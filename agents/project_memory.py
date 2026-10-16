"""
Remembers finished projects so similar requests can reuse them.

Every project that passed testing is stored with an embedding of its
requirement (the same all-MiniLM-L6-v2 model the RAG search uses).
For a new requirement:

* REUSE  - almost the same request (very high similarity AND no new
           important words): the old project is copied, no model call.
* ADAPT  - clearly related request: the old project is given to the
           model as a base and the model writes ONLY the files that
           must change. Far fewer output tokens than a full project.
* NONE   - anything else: normal full generation.

Thresholds can be changed in .env / Streamlit secrets:
    PROJECT_REUSE_SIMILARITY=0.90
    PROJECT_ADAPT_SIMILARITY=0.80
Set PROJECT_MEMORY=off to switch the whole feature off.
"""

import json
import os
import re
import threading
from pathlib import Path

import numpy as np


BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_FILE = BASE_DIR / ".cache" / "project_memory.json"

REUSE = "reuse"
ADAPT = "adapt"

# A base project larger than this is not sent to the model.
MAX_BASE_CHARS = 60_000
MAX_FILE_CHARS = 20_000

TEXT_SUFFIXES = {
    ".php", ".sql", ".css", ".js", ".html", ".htm", ".json", ".md",
    ".txt", ".xml", ".env", ".example", ".htaccess", ".ini", ".yml",
    ".yaml",
}

# Words that do not change what the project is.
STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with",
    "using", "use", "me", "my", "i", "want", "need", "please", "that",
    "which", "is", "it", "can", "should", "will", "be", "by", "from",
    "create", "build", "make", "generate", "develop", "write", "give",
    "php", "project", "app", "application", "complete", "full", "simple",
    "basic", "small", "website", "web", "system", "where", "who",
    "banao", "bana", "do", "de", "ek", "mujhe", "chahiye", "aur", "ka",
    "ki", "ke", "mein", "me", "se", "wala", "wali", "karo",
}


def _setting(name, default):

    value = os.getenv(name)

    if not value:
        try:
            import streamlit as st
            value = st.secrets.get(name)
        except Exception:
            value = None

    return str(value).strip() if value else default


def keywords(text):
    """Important words of a requirement ("todo", "mysql", "login")."""

    words = re.findall(r"[a-z0-9]+", (text or "").lower())

    return {w for w in words if w not in STOPWORDS and len(w) > 1}


class ProjectMemory:

    _lock = threading.Lock()

    def __init__(self, embed, index_file=INDEX_FILE):
        """
        embed: function(list_of_texts) -> list of vectors.
        """
        self.embed = embed
        self.index_file = Path(index_file)

        self.enabled = _setting("PROJECT_MEMORY", "on").lower() not in (
            "off", "false", "0", "no"
        )
        self.reuse_at = float(_setting("PROJECT_REUSE_SIMILARITY", "0.90"))
        self.adapt_at = float(_setting("PROJECT_ADAPT_SIMILARITY", "0.80"))

    # ------------------------------------------------------------

    def _load(self):
        try:
            return json.loads(self.index_file.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save(self, entries):
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        self.index_file.write_text(json.dumps(entries), encoding="utf-8")

    def _vector(self, text):
        vector = np.asarray(list(self.embed([text]))[0], dtype="float32")
        norm = float(np.linalg.norm(vector)) or 1.0
        return vector / norm

    # ------------------------------------------------------------

    def remember(self, requirement, project_dir, model=None):
        """Store a finished, tested project."""

        if not self.enabled:
            return

        try:
            vector = self._vector(requirement)
        except Exception as e:
            print(f"Project memory: could not embed requirement: {e}")
            return

        with self._lock:

            entries = [
                e for e in self._load()
                if e.get("project_dir") != str(project_dir)
            ]

            entries.append({
                "requirement": requirement,
                "project_dir": str(project_dir),
                "model": model,
                "vector": [round(float(x), 5) for x in vector],
            })

            # Keep the file small: newest 300 projects.
            self._save(entries[-300:])

    def find(self, requirement):
        """
        Returns (mode, entry, score). mode is REUSE, ADAPT or None.
        """

        if not self.enabled:
            return None, None, 0.0

        with self._lock:
            entries = [
                e for e in self._load()
                if Path(e.get("project_dir", "")).is_dir()
            ]

        if not entries:
            return None, None, 0.0

        try:
            query = self._vector(requirement)
        except Exception as e:
            print(f"Project memory: could not embed requirement: {e}")
            return None, None, 0.0

        best, best_score = None, -1.0

        for entry in entries:
            score = float(np.dot(query, np.asarray(entry["vector"], dtype="float32")))
            if score > best_score:
                best, best_score = entry, score

        print(f"Project memory: best match {best_score:.3f} -> {best['project_dir']}")

        new_words = keywords(requirement) - keywords(best["requirement"])

        # Same request in other words, nothing new asked for.
        if best_score >= self.reuse_at and not new_words:
            return REUSE, best, best_score

        if best_score >= self.adapt_at and base_size(best["project_dir"]) <= MAX_BASE_CHARS:
            return ADAPT, best, best_score

        return None, best, best_score


# ----------------------------------------------------------------
# Reading a base project for the ADAPT prompt
# ----------------------------------------------------------------

def _text_files(project_dir):

    root = Path(project_dir)

    for path in sorted(root.rglob("*")):

        if not path.is_file():
            continue

        name = path.name.lower()

        if path.suffix.lower() in TEXT_SUFFIXES or name in (".htaccess", ".env.example"):
            yield path


def base_size(project_dir):
    return sum(
        min(p.stat().st_size, MAX_FILE_CHARS) for p in _text_files(project_dir)
    )


def base_project_text(project_dir):
    """The base project as FILE blocks, for the ADAPT prompt."""

    root = Path(project_dir)
    blocks = []

    for path in _text_files(root):

        relative = path.relative_to(root).as_posix()
        content = path.read_text(encoding="utf-8", errors="replace")[:MAX_FILE_CHARS]
        language = path.suffix.lstrip(".") or "text"

        blocks.append(f"FILE: {relative}\n```{language}\n{content}\n```")

    return "\n\n".join(blocks)