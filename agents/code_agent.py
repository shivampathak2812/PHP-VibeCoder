import json
import hashlib
from pathlib import Path

from rag.context_builder import PHPContextBuilder
from agents.project_writer import ProjectWriter
from agents.gemini_model_manager import GeminiModelManager
from agents.php_rules import PHP_QUALITY_RULES


BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / ".cache" / "generations"


class PHPCodeAgent:

    # Upper bound on the generated answer size.
    MAX_OUTPUT_TOKENS = 32768

    def __init__(self, top_k=3, api_key=None):
        self.context_builder = PHPContextBuilder(top_k=top_k)
        self.project_writer = ProjectWriter()
        self.model_manager = GeminiModelManager(api_key=api_key)

    def _cache_key(self, requirement, attachment_path=None):
        """Same requirement + same attachment -> same key."""

        digest = hashlib.sha256()

        # New rules -> new key, so answers made under old rules
        # are not served from the cache.
        digest.update(PHP_QUALITY_RULES.encode("utf-8"))

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

    def generate_code(
        self,
        requirement,
        project_name="php-project",
        attachment_path=None,
        attachment_type=None,
        on_progress=None
    ):
        """
        on_progress: optional callback(text_so_far). When given, the
        answer is streamed and the callback is called as it grows, so
        the UI can show the project while it is being written.
        """

        # ---------------------------------------------------------
        # Get relevant PHP documentation from RAG
        # ---------------------------------------------------------

        context = self.context_builder.build_context(
            requirement
        )

        # ---------------------------------------------------------
        # Attachment information
        # ---------------------------------------------------------

        attachment_instruction = ""

        if attachment_path:

            attachment_name = Path(
                attachment_path
            ).name

            if attachment_type == "photo":

                attachment_instruction = f"""
USER PROVIDED IMAGE:

The user has provided an image named:
{attachment_name}

The image is part of the project requirement.

Analyze the image carefully and use it as a design/reference
for the generated PHP project.

If the image represents:

- a website UI
- a dashboard
- a form
- a webpage
- an application screen
- a layout
- a component

then reproduce the relevant structure, layout, components,
styling requirements, fields, buttons, navigation, and
visual behavior in the generated PHP project.

Do not ignore the image.
"""

            else:

                attachment_instruction = f"""
USER PROVIDED FILE:

The user has provided a file named:
{attachment_name}

Use the uploaded file as additional project input.

Analyze its relevant contents and incorporate them into
the generated PHP project where appropriate.

Do not ignore the uploaded file.
"""

        # ---------------------------------------------------------
        # Create prompt for Gemini (kept short to save tokens)
        # ---------------------------------------------------------

        prompt = f"""
You are an expert PHP 8.x developer. Generate a complete, working
PHP project for the user's requirement.

USER REQUIREMENT:
{requirement}

{attachment_instruction}

PHP DOCUMENTATION (from RAG, use as primary PHP reference):
{context}

RULES:
- Modern PHP 8.x, no deprecated mysql_* functions.
- MySQL via PDO unless the user asks for something else.
- Complete code only: no placeholders, TODOs or "..." stubs.
- Only what the requirement needs; no unrelated features.
- Include every file needed (PHP, SQL, CSS, JS, config).
- Do not claim the code was tested.

{PHP_QUALITY_RULES}

OUTPUT FORMAT (follow exactly, keep prose short):

PROJECT OVERVIEW
2-4 sentences on what the project does and its architecture.

PROJECT STRUCTURE
The folder and file tree.

FILES
For every file, one FILE line followed by one code block:

FILE: index.php
```php
<complete code>
```

FILE: css/style.css
```css
<complete code>
```

Never put two files in one code block.

SETUP
Short numbered steps to install, configure the database and run.
"""

        print("\nGenerating project...")

        if attachment_path:
            print(
                f"Attachment included: {attachment_path}"
            )

        # ---------------------------------------------------------
        # Reuse a cached answer for an identical request
        # ---------------------------------------------------------

        cache_key = self._cache_key(
            requirement,
            attachment_path
        )

        cached = self._read_cache(cache_key)

        if cached:

            print("\nUsing cached Gemini response.")

            response = cached["response"]
            selected_model = f"{cached.get('model')} (cached)"

        elif on_progress:

            pieces = []

            try:

                for text in self.model_manager.generate_stream(
                    prompt,
                    attachment_path=attachment_path,
                    attachment_type=attachment_type,
                    max_output_tokens=self.MAX_OUTPUT_TOKENS
                ):

                    pieces.append(text)

                    try:
                        on_progress("".join(pieces))
                    except Exception as e:
                        # A UI problem must not stop the generation.
                        print(f"Progress callback failed: {e}")

            except Exception as e:
                raise RuntimeError(
                    f"Gemini generation failed: {e}"
                )

            response = "".join(pieces)
            selected_model = self.model_manager.last_model

        else:

            result = self.model_manager.generate(
                prompt,
                attachment_path=attachment_path,
                attachment_type=attachment_type,
                max_output_tokens=self.MAX_OUTPUT_TOKENS
            )

            if not result.get("success"):
                raise RuntimeError(
                    f"Gemini generation failed: "
                    f"{result.get('error')}"
                )

            response = result["response"]
            selected_model = result["model"]

        print(
            f"\nMODEL USED: {selected_model}"
        )

        # ---------------------------------------------------------
        # Write generated project
        # ---------------------------------------------------------

        result = self.project_writer.write_project(
            project_name,
            response
        )

        if not cached:
            self._write_cache(
                cache_key,
                response,
                selected_model
            )

        return {
            "project_dir": result["project_dir"],
            "files_created": result["files_created"],
            "file_count": result["file_count"],
            "gemini_response": response,
            "model": selected_model
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