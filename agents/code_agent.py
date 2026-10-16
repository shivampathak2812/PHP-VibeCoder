import json
import re
import shutil
import hashlib
from pathlib import Path

from rag.context_builder import PHPContextBuilder
from agents.project_writer import ProjectWriter
from agents.gemini_model_manager import GeminiModelManager
from agents.php_rules import PHP_QUALITY_RULES
from agents.complexity import estimate as estimate_complexity, effective_level
from agents import feature_checker
from agents.project_memory import (
    ProjectMemory, REUSE, ADAPT, base_project_text,
)


BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / ".cache" / "generations"
TEMPLATE_DIR = BASE_DIR / "templates" / "php_base"

# Bump when the prompt changes, so old cached answers are not reused.
PROMPT_VERSION = "3"

# Requests that should NOT get the PDO/MySQL template files.
NO_TEMPLATE_PATTERN = re.compile(
    r"\b(mysqli|sqlite|postgres|postgresql|pgsql|mongo|mongodb|"
    r"oracle|mssql|sql server|laravel|symfony|codeigniter|yii|"
    r"no database|without (a )?database|without db|no db|json file|"
    r"flat file|static (site|page|website))\b",
    re.IGNORECASE,
)


# ----------------------------------------------------------------
# STATIC PROMPT PARTS
# Kept first and identical on every request, so Gemini's implicit
# prompt cache can reuse them (faster start, cheaper input tokens).
# Everything that changes per request goes at the END of the prompt.
# ----------------------------------------------------------------

BASE_INSTRUCTIONS = """
You are an expert PHP 8.x developer. Generate a complete, working
PHP project for the user's requirement given at the end.

RULES:
- Modern PHP 8.x, no deprecated mysql_* functions.
- MySQL via PDO unless the user asks for something else.
- Complete code only: no placeholders, TODOs or "..." stubs.
- Only what the requirement needs; no unrelated features.
- Include every file needed (PHP, SQL, CSS, JS, config).
- Do not claim the code was tested.

COMPLETENESS:
- Implement EVERY feature the requirement lists. For each thing the
  user manages (contacts, deals, tasks, ...) include list, add, edit
  and delete, plus any status/stage change the requirement implies.

STRUCTURE AND SIZE (the output is written to disk, so skip anything
that does not change how the app works):
- One file per page or module (for example contacts.php, deals.php),
  plus shared includes (header, footer, helpers). Do not put a whole
  app in one file, and never write the same file twice.
- No code comments, except one short line where the logic is not
  obvious. No README or documentation pages.
- CSS: one clean, responsive stylesheet that makes the app pleasant to
  use (navigation, tables, forms, buttons, cards); no frameworks unless
  the user asks.
- PROJECT OVERVIEW: at most 3 sentences. SETUP: at most 6 short steps.
"""

TEMPLATE_INSTRUCTIONS = """
PROVIDED FILES (they are added to the project automatically; do NOT
write them, just use them):

- config/database.php  returns ['host','port','name','user','pass',
  'charset','debug'] read from environment variables
  (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS, APP_DEBUG).
- src/Database.php     final class Database (global namespace):
    Database::connection(): PDO   shared PDO, ERRMODE_EXCEPTION,
                                  FETCH_ASSOC, real prepared statements
    Database::debug(): bool       true when APP_DEBUG is on
- .env.example         the variables above.

Load it with require_once and the correct relative path to
src/Database.php (for example
require_once __DIR__ . '/../src/Database.php'; from a file in public/).
Inside a namespace call \\Database::connection().
Never create another database connection class or config file.
The database name comes from DB_NAME; in schema.sql create and USE a
database named after the project (lowercase, underscores), e.g.
CREATE DATABASE IF NOT EXISTS crm_app; USE crm_app;
"""

OUTPUT_FORMAT = """
OUTPUT FORMAT (follow exactly):

PROJECT OVERVIEW
At most 3 sentences.

PROJECT STRUCTURE
The folder and file tree.

FILES
For every file, one FILE line followed by one code block:

FILE: index.php
```php
<complete code>
```

Never put two files in one code block.

SETUP
At most 6 short numbered steps, including how to log in.
"""

ADAPT_INSTRUCTIONS = """
You are an expert PHP 8.x developer. A finished, tested project for a
SIMILAR earlier request is given below as the BASE PROJECT. Change it
so it fully satisfies the NEW REQUIREMENT at the end.

RULES:
- Keep everything from the base project that the new requirement
  still needs; change or add only what is different.
- Output ONLY the files you add or change, each one complete.
  Files you do not output are kept exactly as they are.
- To remove a file that the new requirement does not need, write a
  line: DELETE: path/of/file
- Same code quality and security rules as the base project:
  prepared statements, password_hash, CSRF tokens, escaped output.
- No code comments except one short line where logic is not obvious.
- Implement EVERY feature of the new requirement.

OUTPUT FORMAT (follow exactly):

CHANGES
At most 3 sentences describing what changed.

FILES
FILE: path/of/changed_or_new_file.php
```php
<complete code>
```

DELETE: path/of/removed_file.php   (only if needed)
"""


DB_NAME_PATTERN = re.compile(
    r"\b(?:CREATE\s+DATABASE(?:\s+IF\s+NOT\s+EXISTS)?|USE)\s+`?([A-Za-z0-9_]+)`?",
    re.IGNORECASE,
)


def schema_database_name(project_dir):
    """The database name used in the project's .sql files, if any."""

    for path in sorted(Path(project_dir).rglob("*.sql")):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        match = DB_NAME_PATTERN.search(text)
        if match:
            return match.group(1)

    return None


def _file_mentions_template(project_dir):
    """True if any generated file uses the provided Database class."""

    for path in Path(project_dir).rglob("*.php"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "Database::" in text or "Database.php" in text or "config/database.php" in text:
            return True

    return False


class PHPCodeAgent:

    # Upper bound on the generated answer size. Kept high on purpose:
    # the prompt keeps answers short, and a lower cap would cut big
    # projects off in the middle of a file.
    MAX_OUTPUT_TOKENS = 32768

    def __init__(self, top_k=3, api_key=None):
        self.context_builder = PHPContextBuilder(top_k=top_k)
        self.project_writer = ProjectWriter()
        self.model_manager = GeminiModelManager(api_key=api_key)
        self._memory = None

    # ------------------------------------------------------------
    # Similar-project memory (uses the RAG embedding model)
    # ------------------------------------------------------------

    @property
    def memory(self):

        if self._memory is None:
            model = self.context_builder.retriever.model
            self._memory = ProjectMemory(embed=lambda texts: model.embed(texts))

        return self._memory

    def remember_project(self, requirement, project_dir, model=None):
        """Called by PHPVibeCoder after the project passed testing."""

        try:
            self.memory.remember(requirement, project_dir, model)
        except Exception as e:
            print(f"Could not remember project: {e}")

    # ------------------------------------------------------------
    # Exact-match cache
    # ------------------------------------------------------------

    def _cache_key(self, requirement, attachment_path=None):
        """Same requirement + same attachment -> same key."""

        digest = hashlib.sha256()

        # New rules or prompt -> new key, so answers made under old
        # rules are not served from the cache.
        digest.update(PHP_QUALITY_RULES.encode("utf-8"))
        digest.update(PROMPT_VERSION.encode("utf-8"))

        digest.update(
            " ".join(requirement.lower().split()).encode("utf-8")
        )

        if attachment_path and Path(attachment_path).is_file():
            digest.update(Path(attachment_path).read_bytes())

        return digest.hexdigest()

    def _read_cache(self, cache_key):

        cache_file = CACHE_DIR / f"{cache_key}.json"

        if not cache_file.is_file():
            return None

        try:
            return json.loads(
                cache_file.read_text(encoding="utf-8")
            )
        except Exception:
            return None

    def _write_cache(self, cache_key, response, model):

        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)

            (CACHE_DIR / f"{cache_key}.json").write_text(
                json.dumps(
                    {"response": response, "model": model}
                ),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"Could not write cache: {e}")

    # ------------------------------------------------------------
    # Prompt pieces
    # ------------------------------------------------------------

    @staticmethod
    def use_templates(requirement):
        return not NO_TEMPLATE_PATTERN.search(requirement or "")

    @staticmethod
    def _attachment_instruction(attachment_path, attachment_type):

        if not attachment_path:
            return ""

        name = Path(attachment_path).name

        if attachment_type == "photo":
            return f"""
USER PROVIDED IMAGE ({name}): it is part of the requirement. If it
shows a UI (page, form, dashboard, layout, component), reproduce its
structure, fields, buttons, navigation and styling. Do not ignore it.
"""

        return f"""
USER PROVIDED FILE ({name}): use its relevant contents as project
input. Do not ignore it.
"""

    def build_prompt(self, requirement, attachment_path=None, attachment_type=None):
        """Full-generation prompt: static parts first, request last."""

        templates = self.use_templates(requirement)

        context = self.context_builder.build_context(requirement)

        return (
            BASE_INSTRUCTIONS
            + PHP_QUALITY_RULES
            + (TEMPLATE_INSTRUCTIONS if templates else "")
            + OUTPUT_FORMAT
            # ---- per request from here on ----
            + f"\nPHP DOCUMENTATION (from RAG, reference only):\n{context}\n"
            + self._attachment_instruction(attachment_path, attachment_type)
            + f"\nUSER REQUIREMENT:\n{requirement}\n"
        )

    @staticmethod
    def build_adapt_prompt(requirement, base_requirement, base_dir):
        return (
            ADAPT_INSTRUCTIONS
            + PHP_QUALITY_RULES
            + f"\nEARLIER REQUEST (the base project was built for this):\n{base_requirement}\n"
            + f"\nBASE PROJECT:\n{base_project_text(base_dir)}\n"
            + f"\nNEW REQUIREMENT:\n{requirement}\n"
        )

    # ------------------------------------------------------------
    # Model call (streamed when the UI wants live progress)
    # ------------------------------------------------------------

    def _ask_model(self, prompt, attachment_path, attachment_type,
                   on_progress, thinking_level=None):

        if on_progress:

            pieces = []

            try:

                for text in self.model_manager.generate_stream(
                    prompt,
                    attachment_path=attachment_path,
                    attachment_type=attachment_type,
                    max_output_tokens=self.MAX_OUTPUT_TOKENS,
                    thinking_level=thinking_level
                ):

                    pieces.append(text)

                    try:
                        on_progress("".join(pieces))
                    except Exception as e:
                        # A UI problem must not stop the generation.
                        print(f"Progress callback failed: {e}")

            except Exception as e:
                raise RuntimeError(f"Gemini generation failed: {e}")

            return "".join(pieces), self.model_manager.last_model

        result = self.model_manager.generate(
            prompt,
            attachment_path=attachment_path,
            attachment_type=attachment_type,
            max_output_tokens=self.MAX_OUTPUT_TOKENS,
            thinking_level=thinking_level
        )

        if not result.get("success"):
            raise RuntimeError(
                f"Gemini generation failed: {result.get('error')}"
            )

        return result["response"], result["model"]

    # ------------------------------------------------------------
    # Files
    # ------------------------------------------------------------

    def _project_dir(self, project_name):
        safe = re.sub(r"[^a-zA-Z0-9_-]", "-", project_name)
        return self.project_writer.output_dir / safe

    def _apply_templates(self, project_dir, requirement):
        """
        Copy the provided base files into the project when the
        generated code uses them. A file the model wrote itself is
        kept, because the rest of its code was written for it.
        """

        if not self.use_templates(requirement) or not TEMPLATE_DIR.is_dir():
            return

        if not _file_mentions_template(project_dir):
            return

        # Same database name as schema.sql, so the app connects to the
        # database the SQL script creates.
        db_name = schema_database_name(project_dir)

        for source in TEMPLATE_DIR.rglob("*"):

            if not source.is_file():
                continue

            target = Path(project_dir) / source.relative_to(TEMPLATE_DIR)

            if target.exists():
                continue

            target.parent.mkdir(parents=True, exist_ok=True)

            text = source.read_text(encoding="utf-8")

            if db_name:
                text = text.replace("getenv('DB_NAME') ?: 'app'", f"getenv('DB_NAME') ?: '{db_name}'")
                text = text.replace("DB_NAME=app", f"DB_NAME={db_name}")

            target.write_text(text, encoding="utf-8")

    def _complete_missing(self, requirement, project_name, project_dir,
                          on_progress, thinking):
        """
        Requirement check (cheap, Groq first). If features are missing,
        one more call writes only the files that add them.
        Returns the extra model response ("" if nothing was added).
        """

        if not feature_checker.enabled():
            return ""

        try:
            missing = feature_checker.find_missing(
                self.model_manager, requirement, project_dir
            )
        except Exception as e:
            print(f"Feature check failed: {e}")
            return ""

        if not missing:
            return ""

        prompt = (
            feature_checker.COMPLETE_INSTRUCTIONS
            + PHP_QUALITY_RULES
            + "\nMISSING FEATURES TO ADD:\n"
            + "\n".join(f"- {item}" for item in missing)
            + f"\n\nPROJECT:\n{base_project_text(project_dir)}\n"
            + f"\nREQUIREMENT:\n{requirement}\n"
        )

        try:

            response, model = self._ask_model(
                prompt, None, None, on_progress, thinking
            )

            if self.project_writer.extract_files(response):
                self.project_writer.write_project(project_name, response)
                self._apply_templates(project_dir, requirement)
                print(f"Added missing features with {model}: {missing}")
                return "\n\n" + response

        except Exception as e:
            print(f"Adding missing features failed: {e}")

        return ""

    @staticmethod
    def _apply_deletes(project_dir, response):

        root = Path(project_dir).resolve()

        for match in re.finditer(r"^DELETE:\s*(\S+)", response, re.MULTILINE):

            target = (root / match.group(1)).resolve()

            # Only files inside the project.
            if root in target.parents and target.is_file():
                target.unlink()

    @staticmethod
    def _all_files(project_dir):
        root = Path(project_dir)
        return sorted(
            p.relative_to(root).as_posix()
            for p in root.rglob("*") if p.is_file()
        )

    # ------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------

    def generate_code(
        self,
        requirement,
        project_name="php-project",
        attachment_path=None,
        attachment_type=None,
        on_progress=None
    ):
        """
        Order of attempts, cheapest first:
        1. exact cache            same request seen before   (no model call)
        2. REUSE similar project  same request, other words  (no model call)
        3. ADAPT similar project  related request            (only changed files)
        4. full generation

        on_progress: optional callback(text_so_far). When given, the
        answer is streamed and the callback is called as it grows.
        """

        project_dir = self._project_dir(project_name)

        # Adaptive thinking: easy projects think less (faster), hard
        # ones (payments, roles, booking conflicts...) think more.
        thinking, details = estimate_complexity(requirement)
        print(f"Adaptive thinking: {details}")

        # A fixed GEMINI_THINKING_LEVEL in .env wins; show what is used.
        self.thinking_level = effective_level(thinking)

        # ---------------- 1. exact cache ----------------
        cache_key = self._cache_key(requirement, attachment_path)
        cached = self._read_cache(cache_key)

        if cached:

            print("\nUsing cached response.")

            self.project_writer.write_project(project_name, cached["response"])
            self._apply_templates(project_dir, requirement)

            return self._result(
                project_dir, cached["response"], cached.get("model"), "cache"
            )

        # ---------------- 2/3. similar project ----------------
        mode, entry = None, None

        if not attachment_path:

            try:
                mode, entry, score = self.memory.find(requirement)
            except Exception as e:
                print(f"Project memory unavailable: {e}")
                mode = None

        if mode == REUSE:

            print(f"\nReusing similar project: {entry['project_dir']}")

            shutil.copytree(entry["project_dir"], project_dir, dirs_exist_ok=True)

            return self._result(project_dir, "", None, "reuse")

        if mode == ADAPT:

            print(f"\nAdapting similar project: {entry['project_dir']}")

            shutil.copytree(entry["project_dir"], project_dir, dirs_exist_ok=True)

            prompt = self.build_adapt_prompt(
                requirement, entry["requirement"], entry["project_dir"]
            )

            try:

                response, model = self._ask_model(
                    prompt, None, None, on_progress, thinking
                )

                self._apply_deletes(project_dir, response)

                if self.project_writer.extract_files(response):
                    self.project_writer.write_project(project_name, response)

                self._apply_templates(project_dir, requirement)

                extra = self._complete_missing(
                    requirement, project_name, project_dir,
                    on_progress, thinking
                )

                # Only the model name is shown to the user; how the
                # project was made stays internal (see "source").
                return self._result(
                    project_dir, response + extra, model, "adapt"
                )

            except Exception as e:

                # Fall back to a normal full generation.
                print(f"Adapting failed, generating from scratch: {e}")
                shutil.rmtree(project_dir, ignore_errors=True)

        # ---------------- 4. full generation ----------------
        prompt = self.build_prompt(requirement, attachment_path, attachment_type)

        print("\nGenerating project...")

        response, model = self._ask_model(
            prompt, attachment_path, attachment_type, on_progress, thinking
        )

        print(f"\nMODEL USED: {model}")

        self.project_writer.write_project(project_name, response)
        self._apply_templates(project_dir, requirement)

        # Later FILE blocks replace earlier ones, so the cached answer
        # rebuilds the completed project.
        response += self._complete_missing(
            requirement, project_name, project_dir, on_progress, thinking
        )

        self._write_cache(cache_key, response, model)

        return self._result(project_dir, response, model, "generated")

    def _result(self, project_dir, response, model, source):

        files = self._all_files(project_dir)

        return {
            "project_dir": str(project_dir),
            "files_created": files,
            "file_count": len(files),
            "gemini_response": response,
            "model": model,
            # "cache", "reuse", "adapt" or "generated"
            "source": source,
            # thinking level that was used ("low" / "medium" / "high")
            "thinking": (
                getattr(self, "thinking_level", None)
                if source in ("adapt", "generated") else None
            ),
        }


if __name__ == "__main__":

    print("=" * 70)
    print("PHP VibeCoder - Code Agent")
    print("=" * 70)
    print("Code Agent is ready.")
    print(
        "Use PHPCodeAgent.generate_code() "
        "with a dynamic requirement."
    )