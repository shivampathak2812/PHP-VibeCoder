"""
Server-side limit on project generations.

The counts live in server memory, shared by every browser tab and
every user of this Streamlit process, so refreshing the page or
opening a new tab does not reset them. They reset only when the app
restarts.

Two limits:

* per user  - GENERATIONS_PER_WINDOW projects per WINDOW_SECONDS,
              users told apart by IP address (hashed, never stored raw);
* whole app - GLOBAL_GENERATIONS_PER_HOUR across all users, so the
              shared Gemini quota cannot be emptied by many users or
              by someone changing IP.

A slot is taken BEFORE generation starts (so ten tabs clicking at
once cannot all slip through) and given back if the generation fails.
"""

import hashlib
import os
import threading
import time
from collections import deque


def _int_setting(name, default):

    value = os.getenv(name)

    if not value:
        try:
            import streamlit as st
            value = st.secrets.get(name)
        except Exception:
            value = None

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


GENERATIONS_PER_WINDOW = _int_setting("GENERATIONS_PER_WINDOW", 5)
WINDOW_SECONDS = _int_setting("GENERATION_WINDOW_MINUTES", 10) * 60

GLOBAL_GENERATIONS_PER_HOUR = _int_setting(
    "GLOBAL_GENERATIONS_PER_HOUR", 40
)
GLOBAL_WINDOW_SECONDS = 60 * 60


def user_id_from_context(context):
    """
    A stable, anonymous id for the person using the app.

    Streamlit Cloud sits behind a proxy, so the real address is in the
    X-Forwarded-For header; st.context.ip_address is the fallback.
    Locally both are empty and every tab counts as one user, "local".
    """

    ip = None

    try:
        forwarded = context.headers.get("X-Forwarded-For")
        if isinstance(forwarded, str) and forwarded:
            ip = forwarded.split(",")[0].strip()
    except Exception:
        pass

    if not ip:
        try:
            ip = context.ip_address
        except Exception:
            ip = None

    # Anything that is not a real address string counts as local.
    if not isinstance(ip, str) or not ip.strip():
        return "local"

    return hashlib.sha256(ip.encode("utf-8")).hexdigest()[:16]


class GenerationLimiter:

    def __init__(
        self,
        per_user=GENERATIONS_PER_WINDOW,
        window_seconds=WINDOW_SECONDS,
        global_limit=GLOBAL_GENERATIONS_PER_HOUR,
        global_window_seconds=GLOBAL_WINDOW_SECONDS,
        clock=time.time
    ):
        self.per_user = per_user
        self.window_seconds = window_seconds
        self.global_limit = global_limit
        self.global_window_seconds = global_window_seconds
        self.clock = clock

        self._lock = threading.Lock()
        self._users = {}          # user_id -> deque of timestamps
        self._all = deque()       # timestamps of every generation

    # ------------------------------------------------------------

    def _prune(self, now):

        while self._all and now - self._all[0] >= self.global_window_seconds:
            self._all.popleft()

        for user_id in list(self._users):

            times = self._users[user_id]

            while times and now - times[0] >= self.window_seconds:
                times.popleft()

            if not times:
                del self._users[user_id]

    def left(self, user_id):
        """Generations this user can still start right now."""

        with self._lock:

            now = self.clock()
            self._prune(now)

            user_left = self.per_user - len(self._users.get(user_id, ()))
            global_left = self.global_limit - len(self._all)

            return max(0, min(user_left, global_left))

    def try_acquire(self, user_id):
        """
        Take one slot. Returns (ok, reason, wait_seconds, token).
        reason is "user" or "global" when ok is False.
        Keep the token: pass it to release() if the generation fails.
        """

        with self._lock:

            now = self.clock()
            self._prune(now)

            times = self._users.get(user_id, deque())

            if len(times) >= self.per_user:
                wait = self.window_seconds - (now - times[0])
                return False, "user", int(wait) + 1, None

            if len(self._all) >= self.global_limit:
                wait = self.global_window_seconds - (now - self._all[0])
                return False, "global", int(wait) + 1, None

            times.append(now)
            self._users[user_id] = times
            self._all.append(now)

            return True, None, 0, now

    def release(self, user_id, token):
        """Give a slot back (the generation failed)."""

        if token is None:
            return

        with self._lock:

            times = self._users.get(user_id)

            if times and token in times:
                times.remove(token)

            if token in self._all:
                self._all.remove(token)