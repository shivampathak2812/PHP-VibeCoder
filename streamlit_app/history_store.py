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


# ============================================================
# EXPLANATIONS (questions answered without building a project)
# Saved as chat_history/explanations/<id>.json
# ============================================================

EXPLAIN_DIR = os.path.join(
    HISTORY_DIR,
    "explanations"
)


def _explanation_path(explanation_id):
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "-", explanation_id)

    return os.path.join(
        EXPLAIN_DIR,
        f"{safe_id}.json"
    )


def save_explanation(question, answer, model=None):
    """Save one explanation and return its id."""

    os.makedirs(EXPLAIN_DIR, exist_ok=True)

    words = re.findall(r"[a-z0-9]+", question.lower())[:4]

    explanation_id = (
        datetime.now().strftime("%Y%m%d-%H%M%S")
        + "-"
        + ("-".join(words) or "explanation")
    )

    record = {
        "id": explanation_id,
        "question": question,
        "answer": answer,
        "model": model,
        "created_at": _now(),
    }

    with open(
        _explanation_path(explanation_id),
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    return explanation_id


def load_explanation(explanation_id):

    path = _explanation_path(explanation_id)

    if not os.path.isfile(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def append_explanation_message(explanation_id, role, content, model=None):
    """
    Add a follow-up message to an explanation's chat.
    Follow-ups are kept in record["messages"]; the first question and
    answer stay in "question" / "answer".
    """

    record = load_explanation(explanation_id)

    if not record:
        return None

    message = {
        "role": role,
        "content": content,
        "time": _now(),
    }

    if model:
        message["model"] = model

    record.setdefault("messages", []).append(message)

    record["updated_at"] = _now()

    with open(
        _explanation_path(explanation_id),
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    return record


def list_explanations():
    """All saved explanations, newest first."""

    if not os.path.isdir(EXPLAIN_DIR):
        return []

    items = []

    for filename in os.listdir(EXPLAIN_DIR):

        if not filename.endswith(".json"):
            continue

        record = load_explanation(filename[:-5])

        if record:
            items.append(record)

    items.sort(
        key=lambda r: r.get("created_at") or "",
        reverse=True
    )

    return items