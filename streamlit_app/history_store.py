"""
Saves each generated project's requirement and chat messages as
JSON on disk (chat_history/<project>.json) so the sidebar can list
past projects and reopen their chat.
"""

import json
import os
import re
from datetime import datetime


PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

HISTORY_DIR = os.path.join(
    PROJECT_ROOT,
    "chat_history"
)


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _history_path(project):
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "-", project)

    return os.path.join(
        HISTORY_DIR,
        f"{safe_name}.json"
    )


def load_history(project):
    """Return the saved record for a project, or None."""

    path = _history_path(project)

    if not os.path.isfile(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_history(record):
    os.makedirs(HISTORY_DIR, exist_ok=True)

    record["updated_at"] = _now()

    with open(
        _history_path(record["project"]),
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(record, f, indent=2, ensure_ascii=False)


def create_history(project, requirement, summary, model=None):
    """
    Start (or restart) the chat for a freshly generated project.
    """

    record = {
        "project": project,
        "requirement": requirement,
        "model": model,
        "created_at": _now(),
        "messages": [
            {
                "role": "user",
                "content": requirement,
                "time": _now(),
            },
            {
                "role": "assistant",
                "content": summary,
                "time": _now(),
            },
        ],
    }

    save_history(record)

    return record


def get_or_create_history(project, project_dir):
    """
    Projects generated before history existed get an empty record
    so they can still be opened as a chat.
    """

    record = load_history(project)

    if record:
        return record

    created = None

    if os.path.isdir(project_dir):
        created = datetime.fromtimestamp(
            os.path.getmtime(project_dir)
        ).isoformat(timespec="seconds")

    return {
        "project": project,
        "requirement": None,
        "model": None,
        "created_at": created or _now(),
        "messages": [],
    }


def append_message(record, role, content):
    record.setdefault("messages", []).append(
        {
            "role": role,
            "content": content,
            "time": _now(),
        }
    )

    save_history(record)

    return record


def list_projects_with_history(generated_projects_dir):
    """
    Every generated project, newest first, with its requirement
    (if a history file exists).
    """

    if not os.path.isdir(generated_projects_dir):
        return []

    items = []

    for name in os.listdir(generated_projects_dir):

        project_dir = os.path.join(generated_projects_dir, name)

        if not os.path.isdir(project_dir) or name.startswith("."):
            continue

        record = load_history(name)

        if record:
            sort_key = record.get("updated_at") or record.get("created_at")
        else:
            sort_key = datetime.fromtimestamp(
                os.path.getmtime(project_dir)
            ).isoformat(timespec="seconds")

        items.append(
            {
                "project": name,
                "requirement": (record or {}).get("requirement"),
                "sort_key": sort_key or "",
            }
        )

    items.sort(key=lambda item: item["sort_key"], reverse=True)

    return items
