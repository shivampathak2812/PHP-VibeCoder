import os
import re
import time
import hashlib
import mimetypes
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from google import genai
from google.genai import types

from agents.fallback_providers import FallbackProviders


load_dotenv()


# ----------------------------------------------------------------
# TASK TYPES: decide which provider is tried first
# ----------------------------------------------------------------

# Project generation, refactor, debug: long, high-quality output.
# Gemini first, then Groq, then NVIDIA.
TASK_HEAVY = "heavy"

# Explain, chat, Q&A: short answers. Groq / NVIDIA first, so the small
# Gemini daily quota is kept for heavy tasks. Gemini is the backup.
TASK_LIGHT = "light"

# One-word answers (intent routing): like LIGHT, but the smallest
# fallback model of each provider is tried first.
TASK_CLASSIFY = "classify"

LIGHT_TASKS = (TASK_LIGHT, TASK_CLASSIFY)


class _GeminiFailed(Exception):
    """Every Gemini model failed before sending any text."""


def _seconds_until_quota_reset():
    """
    Gemini free-tier daily quotas reset at midnight US Pacific time.
    Used when a "PerDay" 429 does not say how long to wait.
    """

    try:
        from zoneinfo import ZoneInfo
        pacific = ZoneInfo("America/Los_Angeles")
    except Exception:
        # Windows without the tzdata package: use PST.
        pacific = timezone(timedelta(hours=-8))

    now = datetime.now(pacific)

    next_midnight = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # A few minutes extra so we don't hit the reset edge.
    return (next_midnight - now).total_seconds() + 300


def _get_gemini_api_key():
    """
    Look for GEMINI_API_KEY in:
    1. Local .env / real environment variable (local dev)
    2. Streamlit Cloud secrets (st.secrets), if running under Streamlit
    """
    key = os.getenv("GEMINI_API_KEY")

    if key:
        return key

    try:
        import streamlit as st
        key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        key = None

    return key


def _read_env(name):
    """Environment / .env first, then Streamlit secrets."""

    value = os.getenv(name)

    if not value:
        try:
            import streamlit as st
            value = st.secrets.get(name)
        except Exception:
            value = None

    return str(value).strip() if value else None


def _get_model_list(default_models):
    """
    Optional override: GEMINI_MODELS="model-a,model-b,model-c"
    in .env or Streamlit secrets.
    """
    value = os.getenv("GEMINI_MODELS")

    if not value:
        try:
            import streamlit as st
            value = st.secrets.get("GEMINI_MODELS")
        except Exception:
            value = None

    if not value:
        return list(default_models)

    models = [
        model.strip()
        for model in str(value).split(",")
        if model.strip()
    ]

    return models or list(default_models)


class GeminiModelManager:

    # gemini-3.8-flash is tried first because it is the model that
    # currently works on this key; the others are fallbacks.
    PRIMARY_MODEL = "gemini-3.8-flash"
    FALLBACK_MODEL = "gemini-3.6-flash"

    # Every model has its own free-tier quota, so each extra
    # model in the chain adds more requests per day.
    EXTRA_FALLBACK_MODEL = "gemini-3.5-flash"

    MAX_RETRIES_PER_MODEL = 3

    # Exponential backoff for 503 / 5xx: 5s, 10s, 20s ...
    RETRY_DELAY_SECONDS = 5
    MAX_RETRY_DELAY_SECONDS = 30

    # Longest we wait on a 429 before moving to the next model.
    MAX_RATE_LIMIT_WAIT_SECONDS = 60

    # How long a model is skipped after its per-minute quota is used up.
    # (Daily quota: skipped until Pacific midnight, see
    # _seconds_until_quota_reset.)
    PER_MINUTE_COOLDOWN_SECONDS = 60

    # Shared across instances: {(key_id, model): skip_until_timestamp}
    _model_cooldowns = {}

    # Shared across instances: models that returned 404 for a key.
    _unavailable_models = set()

    # Shared across instances: models that rejected thinking_config.
    _no_thinking_models = set()

    # Shared across instances: {key_id: model that last succeeded}.
    _last_good_model = {}

    # Never wait longer than this before trying a model again.
    MAX_DAILY_COOLDOWN_SECONDS = 24 * 60 * 60

    def _ordered_models(self):
        """The model that worked last time goes first."""

        good = self._last_good_model.get(self._key_id)

        if good in self.models:
            return [good] + [m for m in self.models if m != good]

        return list(self.models)

    def _retry_delay(self, attempt):

        return min(
            self.RETRY_DELAY_SECONDS * (2 ** (attempt - 1)),
            self.MAX_RETRY_DELAY_SECONDS
        )

    def __init__(self, api_key=None):

        api_key = api_key or _get_gemini_api_key()

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found in .env or Streamlit secrets."
            )

        self.client = genai.Client(
            api_key=api_key
        )

        # Never store the raw key in shared state.
        self._key_id = hashlib.sha256(
            api_key.encode("utf-8")
        ).hexdigest()[:16]

        # Groq / NVIDIA models: first choice for light tasks, backup
        # for heavy ones. Empty unless their keys are configured.
        self.fallback = FallbackProviders()
        self.last_model = None

        self.models = _get_model_list(
            [
                self.PRIMARY_MODEL,
                self.FALLBACK_MODEL,
                self.EXTRA_FALLBACK_MODEL,
            ]
        )

    def _build_contents(
        self,
        prompt,
        attachment_path=None,
        attachment_type=None
    ):

        # No attachment
        if not attachment_path:
            return prompt

        if not os.path.isfile(attachment_path):
            raise FileNotFoundError(
                f"Attachment not found: {attachment_path}"
            )

        # ---------------------------------------------------------
        # IMAGE ATTACHMENT
        # ---------------------------------------------------------

        if attachment_type == "photo":

            mime_type, _ = mimetypes.guess_type(
                attachment_path
            )

            if not mime_type or not mime_type.startswith("image/"):
                mime_type = "image/jpeg"

            with open(
                attachment_path,
                "rb"
            ) as image_file:

                image_bytes = image_file.read()

            image_part = types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type
            )

            return [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text=prompt
                        ),
                        image_part
                    ]
                )
            ]

        # ---------------------------------------------------------
        # TEXT / DOCUMENT ATTACHMENT
        # ---------------------------------------------------------

        try:

            with open(
                attachment_path,
                "r",
                encoding="utf-8",
                errors="replace"
            ) as file:

                file_content = file.read()

            attachment_name = os.path.basename(
                attachment_path
            )

            attachment_prompt = f"""
{prompt}

USER UPLOADED FILE:
{attachment_name}

UPLOADED FILE CONTENT:
{file_content}

Use the uploaded file as additional input for the project.
"""

            return attachment_prompt

        except UnicodeDecodeError:

            return prompt

    @staticmethod
    def _parse_retry_delay(error_text):
        """Read the wait time Google sends with a 429, if any."""

        patterns = [
            r"retryDelay['\"]?\s*:\s*['\"]?(\d+(?:\.\d+)?)s",
            r"retry in (\d+(?:\.\d+)?)\s*s",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                error_text,
                re.IGNORECASE
            )

            if match:
                return float(match.group(1))

        return None

    def _make_config(self, model, max_output_tokens):
        """
        Request settings for one model.

        thinking_level: Gemini 3.x thinks before answering, and that
        hidden thinking adds a lot of waiting time. "low" keeps it
        short. Set GEMINI_THINKING_LEVEL=off to use Google's default.
        """

        options = {}

        if max_output_tokens:
            options["max_output_tokens"] = max_output_tokens

        level = (_read_env("GEMINI_THINKING_LEVEL") or "low").lower()

        if (
            level not in ("off", "none", "default", "")
            and model not in self._no_thinking_models
        ):
            options["thinking_config"] = types.ThinkingConfig(
                thinking_level=level.upper()
            )

        if not options:
            return None

        return types.GenerateContentConfig(**options)

    def _thinking_rejected(self, model, error_text):
        """
        True if the model refused thinking_config (e.g. an older 2.x
        model). It is then never sent to that model again.
        """

        if (
            model not in self._no_thinking_models
            and ("400" in error_text or "INVALID_ARGUMENT" in error_text)
            and "thinking" in error_text.lower()
        ):
            print(f"{model} does not accept thinking_level; retrying without it.")
            self._no_thinking_models.add(model)
            return True

        return False

    def _can_skip(self, model):
        """
        True if something else can answer right now (a Gemini model not
        tried yet in this request, or Groq / NVIDIA). Then a busy model is skipped at once
        instead of waiting for it.
        """

        if self.fallback.available:
            return True

        tried = getattr(self, "_tried_models", set())

        return any(
            other != model
            and other not in tried
            and (self._key_id, other) not in self._unavailable_models
            and not self._is_cooling_down(other)
            for other in self.models
        )

    def _is_cooling_down(self, model):

        until = self._model_cooldowns.get(
            (self._key_id, model),
            0
        )

        return time.time() < until

    def _set_cooldown(self, model, seconds):

        self._model_cooldowns[(self._key_id, model)] = (
            time.time() + seconds
        )

    def _generate_gemini(
        self,
        prompt,
        attachment_path=None,
        attachment_type=None,
        max_output_tokens=None
    ):
        """Gemini models only (no Groq / NVIDIA)."""

        try:

            contents = self._build_contents(
                prompt=prompt,
                attachment_path=attachment_path,
                attachment_type=attachment_type
            )

        except Exception as e:

            return {
                "success": False,
                "model": None,
                "response": None,
                "error": str(e),
            }

        # Remember the most useful error to show the user:
        # a quota or overload error matters more than a 404
        # from a fallback model.
        rate_limit_error = None
        overload_error = None
        last_error = None

        self._tried_models = set()

        for model in self._ordered_models():

            if (self._key_id, model) in self._unavailable_models:
                continue

            if self._is_cooling_down(model):
                print(
                    f"\nSkipping {model}: quota recently exhausted."
                )
                continue

            self._tried_models.add(model)

            print(
                f"\nTrying Gemini model: {model}"
            )

            for attempt in range(
                1,
                self.MAX_RETRIES_PER_MODEL + 1
            ):

                try:

                    response = self.client.models.generate_content(
                        model=model,
                        contents=contents,
                        config=self._make_config(
                            model,
                            max_output_tokens
                        ),
                    )

                    print(
                        f"SUCCESS: {model}"
                    )

                    self._last_good_model[self._key_id] = model

                    return {
                        "success": True,
                        "model": model,
                        "response": response.text,
                    }

                except Exception as e:

                    last_error = e

                    error_text = str(e)

                    print(
                        f"FAILED: {model} "
                        f"(attempt {attempt}/"
                        f"{self.MAX_RETRIES_PER_MODEL})"
                    )

                    print(
                        f"Reason: {error_text}"
                    )

                    if self._thinking_rejected(model, error_text):
                        continue

                    # ----------------------------------------
                    # RATE LIMIT / QUOTA
                    # ----------------------------------------

                    if (
                        "429" in error_text
                        or "RESOURCE_EXHAUSTED" in error_text
                    ):

                        rate_limit_error = e

                        if "PerDay" in error_text:

                            print(
                                f"Daily quota used up for {model}."
                            )

                            # Daily quotas reset at Pacific midnight.
                            # Google's retryDelay here is often only
                            # ~30s, so never skip for less than that.
                            reset_in = self._parse_retry_delay(
                                error_text
                            )

                            self._set_cooldown(
                                model,
                                min(
                                    max(
                                        reset_in or 0,
                                        _seconds_until_quota_reset()
                                    ),
                                    self.MAX_DAILY_COOLDOWN_SECONDS
                                )
                            )

                            break

                        delay = self._parse_retry_delay(
                            error_text
                        )

                        if (
                            delay is not None
                            and delay <= self.MAX_RATE_LIMIT_WAIT_SECONDS
                            and attempt < self.MAX_RETRIES_PER_MODEL
                            and not self._can_skip(model)
                        ):

                            print(
                                f"Per-minute limit hit for {model}. "
                                f"Waiting {delay:.0f} seconds..."
                            )

                            time.sleep(delay + 1)

                            continue

                        self._set_cooldown(
                            model,
                            delay or self.PER_MINUTE_COOLDOWN_SECONDS
                        )

                        break

                    # ----------------------------------------
                    # MODEL NOT AVAILABLE FOR THIS KEY
                    # ----------------------------------------

                    if (
                        "404" in error_text
                        or "NOT_FOUND" in error_text
                    ):

                        print(
                            f"{model} is not available for this key."
                        )

                        self._unavailable_models.add(
                            (self._key_id, model)
                        )

                        break

                    # ----------------------------------------
                    # TEMPORARY SERVER ERRORS
                    # ----------------------------------------

                    if any(
                        code in error_text
                        for code in [
                            "500",
                            "502",
                            "503",
                            "504",
                            "UNAVAILABLE",
                            "INTERNAL"
                        ]
                    ):

                        overload_error = e

                        # If another model can answer, move on at once
                        # instead of sitting through backoff waits.
                        max_attempts = (
                            1
                            if self._can_skip(model)
                            else self.MAX_RETRIES_PER_MODEL
                        )

                        if attempt < max_attempts:

                            delay = self._retry_delay(attempt)

                            print(
                                f"Temporary Gemini error. "
                                f"Retrying in "
                                f"{delay} seconds..."
                            )

                            time.sleep(delay)

                            continue

                        print(
                            f"{model} unavailable after "
                            f"{self.MAX_RETRIES_PER_MODEL} attempts."
                        )

                        break

                    # ----------------------------------------
                    # UNKNOWN / NON-RETRYABLE ERROR
                    # ----------------------------------------

                    break

        error = rate_limit_error or overload_error or last_error

        if error is None:
            error = (
                "429 RESOURCE_EXHAUSTED: all Gemini models are cooling "
                "down after hitting their quota. Please try again later."
            )

        return {
            "success": False,
            "model": None,
            "response": None,
            "error": str(error),
        }


    def _stream_gemini(
        self,
        prompt,
        attachment_path=None,
        attachment_type=None,
        max_output_tokens=None
    ):
        """
        Yields text from the Gemini models only. Raises _GeminiFailed
        if no Gemini model could start an answer.
        """

        contents = self._build_contents(
            prompt=prompt,
            attachment_path=attachment_path,
            attachment_type=attachment_type
        )

        rate_limit_error = None
        overload_error = None
        last_error = None

        for model in self._ordered_models():

            if (self._key_id, model) in self._unavailable_models:
                continue

            if self._is_cooling_down(model):
                print(f"\nSkipping {model}: quota recently exhausted.")
                continue

            print(f"\nStreaming from Gemini model: {model}")

            # Second pass only if the model rejected thinking_config.
            for _pass in (1, 2):

                started = False

                try:

                    for chunk in self.client.models.generate_content_stream(
                        model=model,
                        contents=contents,
                        config=self._make_config(
                            model,
                            max_output_tokens
                        ),
                    ):

                        text = getattr(chunk, "text", None)

                        if not text:
                            continue

                        if not started:
                            started = True
                            self.last_model = model
                            self._last_good_model[self._key_id] = model

                        yield text

                    if started:
                        return

                    last_error = RuntimeError(
                        f"{model} returned an empty answer."
                    )

                    break

                except Exception as e:

                    if started:
                        raise

                    error_text = str(e)
                    last_error = e

                    print(f"FAILED: {model}")
                    print(f"Reason: {error_text}")

                    if self._thinking_rejected(model, error_text):
                        continue

                    if (
                        "429" in error_text
                        or "RESOURCE_EXHAUSTED" in error_text
                    ):

                        rate_limit_error = e

                        reset_in = self._parse_retry_delay(error_text)

                        if "PerDay" in error_text:
                            cooldown = min(
                                max(
                                    reset_in or 0,
                                    _seconds_until_quota_reset()
                                ),
                                self.MAX_DAILY_COOLDOWN_SECONDS
                            )
                        else:
                            cooldown = (
                                reset_in
                                or self.PER_MINUTE_COOLDOWN_SECONDS
                            )

                        self._set_cooldown(model, cooldown)

                    elif (
                        "404" in error_text
                        or "NOT_FOUND" in error_text
                    ):

                        self._unavailable_models.add(
                            (self._key_id, model)
                        )

                    elif any(
                        code in error_text
                        for code in [
                            "500", "502", "503", "504",
                            "UNAVAILABLE", "INTERNAL"
                        ]
                    ):

                        overload_error = e

                    break

        error = rate_limit_error or overload_error or last_error

        if error is None:
            error = (
                "429 RESOURCE_EXHAUSTED: all Gemini models are cooling "
                "down after hitting their quota. Please try again later."
            )

        raise _GeminiFailed(str(error))

    # ------------------------------------------------------------
    # PUBLIC API: routes each task to the right provider first
    # ------------------------------------------------------------

    def _fallback_first(self, task, attachment_type):
        """
        Light tasks go to Groq / NVIDIA first. Images are the exception:
        only Gemini can read them, so those always start on Gemini.
        """

        return (
            task in LIGHT_TASKS
            and attachment_type != "photo"
            and self.fallback.available
        )

    def generate(
        self,
        prompt,
        attachment_path=None,
        attachment_type=None,
        max_output_tokens=None,
        task=TASK_HEAVY
    ):
        """
        task=TASK_HEAVY (default): Gemini -> Groq -> NVIDIA
        task=TASK_LIGHT / TASK_CLASSIFY: Groq -> NVIDIA -> Gemini

        Returns {"success", "model", "response", "error"}.
        """

        small_first = task == TASK_CLASSIFY

        def run_gemini():
            return self._generate_gemini(
                prompt,
                attachment_path=attachment_path,
                attachment_type=attachment_type,
                max_output_tokens=max_output_tokens
            )

        def run_fallback():
            return self.fallback.generate(
                prompt,
                attachment_path=attachment_path,
                attachment_type=attachment_type,
                max_output_tokens=max_output_tokens,
                small_first=small_first
            )

        if self._fallback_first(task, attachment_type):
            steps = [("fallback", run_fallback), ("gemini", run_gemini)]
        else:
            steps = [("gemini", run_gemini)]

            if self.fallback.available:
                steps.append(("fallback", run_fallback))

        errors = []

        for name, step in steps:

            print(f"\n[{task}] trying {name} models...")

            result = step()

            if result.get("success"):
                self.last_model = result.get("model")
                return result

            print(f"[{task}] {name} failed: {result.get('error')}")

            errors.append(result.get("error"))

        return {
            "success": False,
            "model": None,
            "response": None,
            "error": " | ".join(e for e in errors if e),
        }

    def generate_stream(
        self,
        prompt,
        attachment_path=None,
        attachment_type=None,
        max_output_tokens=None,
        task=TASK_HEAVY
    ):
        """
        Like generate(), but yields the answer piece by piece.

        self.last_model holds the model name once the first piece
        arrives. If a provider fails before sending anything, the next
        one is tried. If it fails after it has started, the error is
        raised.
        """

        self.last_model = None

        small_first = task == TASK_CLASSIFY

        def run_gemini():
            return self._stream_gemini(
                prompt,
                attachment_path=attachment_path,
                attachment_type=attachment_type,
                max_output_tokens=max_output_tokens
            )

        def run_fallback():
            return self.fallback.generate_stream(
                prompt,
                attachment_path=attachment_path,
                attachment_type=attachment_type,
                max_output_tokens=max_output_tokens,
                small_first=small_first
            )

        if self._fallback_first(task, attachment_type):
            steps = [("fallback", run_fallback), ("gemini", run_gemini)]
        else:
            steps = [("gemini", run_gemini)]

            if self.fallback.available:
                steps.append(("fallback", run_fallback))

        errors = []

        for name, step in steps:

            print(f"\n[{task}] streaming from {name} models...")

            started = False

            try:

                for text in step():

                    if not started:
                        started = True

                        if name == "fallback":
                            self.last_model = self.fallback.last_model

                    yield text

                if started:
                    return

                errors.append(f"{name}: empty answer")

            except Exception as e:

                if started:
                    raise

                print(f"[{task}] {name} failed: {e}")

                errors.append(str(e))

        raise RuntimeError(
            "Generation failed: " + " | ".join(errors)
        )


if __name__ == "__main__":

    print("=" * 60)
    print("PHP VibeCoder - Gemini Model Manager")
    print("=" * 60)

    manager = GeminiModelManager()

    result = manager.generate(
        "Say hello in one sentence."
    )

    print("\nFinal Result:")
    print(
        f"Success: {result['success']}"
    )
    print(
        f"Model: {result['model']}"
    )

    if result["success"]:

        print(
            f"Response: {result['response']}"
        )

    else:

        print(
            f"Error: {result['error']}"
        )