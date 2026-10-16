import re
from pathlib import Path

from agents.gemini_model_manager import GeminiModelManager, TASK_LIGHT
from agents.project_writer import ProjectWriter


# Files up to this many lines are shown whole; longer files only
# around the error line.
FULL_FILE_LINES = 200
WINDOW_LINES = 40

LINE_PATTERN = re.compile(r"on line (\d+)")

PATCH_FILE = re.compile(r"^FILE:\s*(\S+)\s*$")
PATCH_HUNK = re.compile(r"^@@\s*(\d+)\s*-\s*(\d+)\s*@@?\s*$")


def local_fix(code):
    """
    Fixes that need no AI, for mistakes models often make:
    a BOM, leftover ``` fences inside the file, a missing <?php tag.
    Returns the fixed code (unchanged if nothing applied).
    """

    fixed = code.lstrip("\ufeff")

    # Markdown fences that leaked into the file.
    fixed = "\n".join(
        line for line in fixed.splitlines()
        if not re.fullmatch(r"\s*```[\w+-]*\s*", line)
    )

    stripped = fixed.lstrip()

    # PHP code without an opening tag (but not HTML templates).
    if stripped and "<?php" not in fixed and not stripped.startswith("<"):
        fixed = "<?php\n\n" + stripped

    if code.endswith("\n") and not fixed.endswith("\n"):
        fixed += "\n"

    return fixed


def numbered(code, error):
    """
    The code with line numbers. Long files are cut to a window around
    the error line, except for "unexpected end of file" errors whose
    cause can be anywhere.
    """

    lines = code.splitlines()
    total = len(lines)

    match = LINE_PATTERN.search(error or "")
    error_line = int(match.group(1)) if match else None

    if (
        total <= FULL_FILE_LINES
        or error_line is None
        or "end of file" in (error or "").lower()
    ):
        start, end = 1, total
    else:
        start = max(1, error_line - WINDOW_LINES)
        end = min(total, error_line + WINDOW_LINES)

    body = "\n".join(
        f"{n:>5}| {lines[n - 1]}" for n in range(start, end + 1)
    )

    note = (
        f"(lines {start}-{end} of {total} shown)"
        if (start, end) != (1, total)
        else f"({total} lines)"
    )

    return body, note


def parse_patches(response):
    """
    {relative_path: [(start, end, [new lines]), ...]} from:

        FILE: path/file.php
        @@ 40-42 @@
        <new lines that replace lines 40..42>
        END
    """

    patches = {}
    current_file = None
    current_hunk = None

    def close_hunk():
        if current_file is not None and current_hunk is not None:
            patches.setdefault(current_file, []).append(current_hunk)

    for raw in response.splitlines():

        line = raw.rstrip("\n")

        if re.fullmatch(r"\s*```[\w+-]*\s*", line):
            continue

        file_match = PATCH_FILE.match(line.strip())
        hunk_match = PATCH_HUNK.match(line.strip())

        if file_match:
            close_hunk()
            current_file, current_hunk = file_match.group(1), None
            continue

        if hunk_match:
            close_hunk()
            current_hunk = (
                int(hunk_match.group(1)), int(hunk_match.group(2)), []
            )
            continue

        if line.strip() == "END":
            close_hunk()
            current_hunk = None
            continue

        if current_hunk is not None:
            # Drop a copied "  42| " line-number prefix if present.
            current_hunk[2].append(re.sub(r"^\s*\d+\|\s?", "", line))

    close_hunk()

    return patches


def apply_patches(code, hunks):
    """Apply hunks bottom-up. Returns new code, or None if invalid."""

    lines = code.splitlines()
    total = len(lines)

    hunks = sorted(hunks, key=lambda h: h[0], reverse=True)

    previous_start = total + 1

    for start, end, new_lines in hunks:

        if not (1 <= start <= end <= total) or end >= previous_start:
            return None

        lines[start - 1:end] = new_lines
        previous_start = start

    result = "\n".join(lines)

    return result + "\n" if code.endswith("\n") else result


class PHPDebugAgent:

    MAX_OUTPUT_TOKENS = 16384

    def __init__(self, api_key=None):
        self.model_manager = GeminiModelManager(api_key=api_key)

    def read_file(self, file_path):
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"File not found: {file_path}"
            )

        return path.read_text(encoding="utf-8")

    def debug_file(self, file_path, error_message):
        code = self.read_file(file_path)

        prompt = f"""
You are an expert PHP 8.5 debugging agent.

A PHP Testing Agent found a syntax error in a generated PHP project.

FILE:
{file_path}

PHP ERROR:
{error_message}

CURRENT CODE:
```php
{code}

Your task:

Identify the exact cause of the PHP syntax error.
Fix the code.
Preserve the original functionality.
Use valid PHP 8.x syntax.
Do not introduce unrelated changes.
Return the complete corrected PHP file.

IMPORTANT:
Return ONLY the corrected PHP code inside a single

...

code block.

Do not include explanations outside the code block.
"""

        result = self.model_manager.generate(
            prompt,
            max_output_tokens=self.MAX_OUTPUT_TOKENS
        )

        if not result.get("success"):
            raise RuntimeError(
                f"Gemini debugging failed: {result.get('error')}"
            )

        response = result["response"]

        print(f"DEBUG MODEL USED: {result['model']}")

        corrected_code = self.extract_code(response)

        if not corrected_code:
            raise ValueError(
                "Gemini did not return valid PHP code."
            )

        return corrected_code

    def debug_files(self, project_dir, failures):
        """
        Fix several broken files with ONE Gemini request.

        failures: list of {"file": absolute_path, "error": message}
        Returns: {absolute_path: corrected_code}
        """
        project_dir = Path(project_dir).resolve()

        sections = []

        for failure in failures:

            path = Path(failure["file"]).resolve()
            relative = path.relative_to(project_dir).as_posix()

            sections.append(
                f"""FILE: {relative}
PHP ERROR:
{failure["error"]}

CURRENT CODE:
```php
{self.read_file(path)}
```
"""
            )

        prompt = f"""
You are an expert PHP 8.x debugging agent.

PHP syntax validation (php -l) failed for the files below.
Fix every file: keep the original functionality, use valid
PHP 8.x syntax and make no unrelated changes.

{chr(10).join(sections)}

Return EVERY file listed above in this exact format, with the
complete corrected code and nothing else:

FILE: path/of/file.php
```php
<complete corrected code>
```
"""

        # Fixing syntax is a small job: fast Groq models first.
        result = self.model_manager.generate(
            prompt,
            max_output_tokens=self.MAX_OUTPUT_TOKENS,
            task=TASK_LIGHT
        )

        if not result.get("success"):
            raise RuntimeError(
                f"Gemini debugging failed: {result.get('error')}"
            )

        print(f"DEBUG MODEL USED: {result['model']}")

        writer = ProjectWriter()

        fixed = {}

        for file_data in writer.extract_files(result["response"]):

            relative = writer.validate_path(file_data["path"])
            full_path = (project_dir / relative).resolve()

            if not file_data["content"]:
                continue

            fixed[str(full_path)] = file_data["content"]

        return fixed

    def debug_files_patch(self, project_dir, failures):
        """
        Like debug_files(), but the model returns only the lines it
        changes (a patch), not whole files: far fewer output tokens,
        and the rest of each file cannot be broken by the fix.

        Returns ({absolute_path: corrected_code}, [failures not fixed]).
        """

        project_dir = Path(project_dir).resolve()

        sections = []
        originals = {}

        for failure in failures:

            path = Path(failure["file"]).resolve()
            relative = path.relative_to(project_dir).as_posix()
            code = self.read_file(path)

            originals[relative] = (path, code, failure)

            body, note = numbered(code, failure["error"])

            sections.append(
                f"FILE: {relative} {note}\n"
                f"PHP ERROR: {failure['error']}\n"
                f"{body}\n"
            )

        prompt = f"""
You are an expert PHP 8.x debugging agent. php -l found syntax errors
in the files below (shown with line numbers). Fix them with the
smallest possible change; keep the functionality.

{chr(10).join(sections)}

Reply ONLY with patches in this exact format, nothing else:

FILE: path/of/file.php
@@ START-END @@
<new code that replaces lines START to END, without line numbers>
END

Rules:
- START and END are line numbers from the listing above.
- To insert a line, replace the line before it with itself plus the
  new line.
- Several @@ blocks per file are allowed; they must not overlap.
- Do not repeat unchanged lines outside the blocks.
"""

        result = self.model_manager.generate(
            prompt,
            max_output_tokens=4096,
            task=TASK_LIGHT
        )

        if not result.get("success"):
            raise RuntimeError(
                f"Debugging failed: {result.get('error')}"
            )

        print(f"DEBUG (patch) MODEL USED: {result['model']}")

        patches = parse_patches(result["response"])

        fixed = {}
        not_fixed = []

        for relative, (path, code, failure) in originals.items():

            new_code = None

            if relative in patches:
                new_code = apply_patches(code, patches[relative])

            if new_code is None or new_code == code:
                not_fixed.append(failure)
            else:
                fixed[str(path)] = new_code

        return fixed, not_fixed

    def extract_code(self, response):
        lines = response.splitlines()

        inside_code = False
        code_lines = []

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("```"):
                if not inside_code:
                    inside_code = True
                else:
                    break

                continue

            if inside_code:
                code_lines.append(line)

        # If Gemini returned code without a code fence
        if not code_lines:
            return response.strip()

        return "\n".join(code_lines).strip()

    def write_fixed_file(self, file_path, corrected_code):
        path = Path(file_path)

        path.write_text(
            corrected_code,
            encoding="utf-8"
        )

        return str(path)

def main():
    print("=" * 70)
    print("PHP VibeCoder - Debug Agent Test")
    print("=" * 70)

    file_path = str(
        Path(__file__).resolve().parent.parent
        / "generated_projects" / "php-project" / "public" / "index.php"
    )

    error_message = (
        'Parse error: syntax error, unexpected identifier '
        '"DATABASE" in public/index.php on line 73'
    )

    agent = PHPDebugAgent()

    print("\nDebugging:")
    print(file_path)

    print("\nSending error to Gemini...")

    corrected_code = agent.debug_file(
        file_path,
        error_message
    )

    print("\nCorrected code received.")

    agent.write_fixed_file(
        file_path,
        corrected_code
    )

    print("\nFixed file written successfully:")
    print(file_path)

    print("\n" + "=" * 70)
    print("DEBUG AGENT COMPLETED")
    print("=" * 70)

if __name__ == "__main__":
    main()