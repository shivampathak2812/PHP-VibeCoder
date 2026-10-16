"""
Requirement check: after a project is written, a small, fast model
(Groq first) compares the requirement with the code and lists the
features that are missing. Only if something is missing does the code
agent make one more call that adds just those parts.

php -l only proves the code has no syntax errors; this step catches
"the deal stage cannot be changed" or "there is no tasks page".

FEATURE_CHECK=off in .env / Streamlit secrets switches it off.
"""

import json
import os
import re
from pathlib import Path

from agents.gemini_model_manager import TASK_LIGHT


# Keep the check cheap: code is trimmed before it is sent.
MAX_FILE_CHARS = 6_000
MAX_TOTAL_CHARS = 40_000
MAX_MISSING = 6

CODE_SUFFIXES = {".php", ".sql", ".js", ".html", ".htm"}


def enabled():

    value = os.getenv("FEATURE_CHECK")

    if not value:
        try:
            import streamlit as st
            value = st.secrets.get("FEATURE_CHECK")
        except Exception:
            value = None

    return str(value or "on").strip().lower() not in ("off", "false", "0", "no")


def _project_code(project_dir):
    """Project code as FILE blocks, trimmed to keep the request small."""

    root = Path(project_dir)
    blocks = []
    total = 0

    for path in sorted(root.rglob("*")):

        if not path.is_file() or path.suffix.lower() not in CODE_SUFFIXES:
            continue

        relative = path.relative_to(root).as_posix()

        # The provided template files are known to be complete.
        if relative in ("src/Database.php", "config/database.php"):
            continue

        text = path.read_text(encoding="utf-8", errors="replace")[:MAX_FILE_CHARS]

        if total + len(text) > MAX_TOTAL_CHARS:
            blocks.append(f"FILE: {relative}\n(not shown, project too large)")
            continue

        total += len(text)
        blocks.append(f"FILE: {relative}\n{text}")

    return "\n\n".join(blocks)


def _parse(response):

    match = re.search(r"\{.*\}", response or "", re.DOTALL)

    if not match:
        return []

    try:
        data = json.loads(match.group(0))
    except ValueError:
        return []

    missing = data.get("missing") or []

    return [
        str(item).strip() for item in missing
        if str(item).strip()
    ][:MAX_MISSING]


def find_missing(model_manager, requirement, project_dir):
    """
    List of features from the requirement that the code does not
    implement (empty list = complete, or the check could not run).
    """

    prompt = f"""
You review a generated PHP project against the user's requirement.

REQUIREMENT:
{requirement}

PROJECT CODE:
{_project_code(project_dir)}

List only features that the REQUIREMENT explicitly asks for and that
are missing or clearly broken in the code (for example: a page that
does not exist, an action with no form or handler, a field that is
never saved). Ignore style, wording, small improvements and anything
the requirement did not ask for.

Reply with JSON only:
{{"missing": ["short description of each missing feature"]}}
Use {{"missing": []}} if everything asked for is there.
"""

    result = model_manager.generate(
        prompt,
        max_output_tokens=1024,
        task=TASK_LIGHT
    )

    if not result.get("success"):
        print(f"Feature check skipped: {result.get('error')}")
        return []

    missing = _parse(result.get("response"))

    print(f"Feature check ({result.get('model')}): missing = {missing}")

    return missing


COMPLETE_INSTRUCTIONS = """
You are an expert PHP 8.x developer. The project below was generated
for the requirement, but a review found that some requested features
are MISSING. Add exactly those features, in the same style and
structure as the existing code.

RULES:
- Output ONLY the files you add or change, each one complete.
  Files you do not output are kept exactly as they are.
- Keep the existing database tables and columns working; if you need
  new columns or tables, output the full updated schema.sql.
- Same security rules: prepared statements (each named placeholder
  used once), password_hash, CSRF tokens, escaped output.
- No code comments except one short line where logic is not obvious.

OUTPUT FORMAT (follow exactly):

CHANGES
At most 3 sentences.

FILES
FILE: path/of/file.php
```php
<complete code>
```
"""