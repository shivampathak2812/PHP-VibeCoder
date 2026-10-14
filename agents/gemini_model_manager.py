import os
import re
import time
import hashlib
import mimetypes

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()


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

    PRIMARY_MODEL = "gemini-3.6-flash"
    FALLBACK_MODEL = "gemini-3.5-flash"

    # Every model has its own free-tier quota, so each extra
    # model in the chain adds more requests per day.
    EXTRA_FALLBACK_MODEL = "gemini-3.8-flash"

    MAX_RETRIES_PER_MODEL = 3

    # Exponential backoff for 503 / 5xx: 5s, 10s, 20s ...
    RETRY_DELAY_SECONDS = 5
    MAX_RETRY_DELAY_SECONDS = 30

    # Longest we wait on a 429 before moving to the next model.
    MAX_RATE_LIMIT_WAIT_SECONDS = 60

    # How long a model is skipped after its quota is used up.
    PER_MINUTE_COOLDOWN_SECONDS = 60
    PER_DAY_COOLDOWN_SECONDS = 60 * 60

    # Shared across instances: {(key_id, model): skip_until_timestamp}
    _model_cooldowns = {}

    # Shared across instances: models that returned 404 for a key.
    _unavailable_models = set()

    def _retry_delay(self, attempt):

        return min(
            self.RETRY_DELAY_SECONDS * (2 ** (attempt - 1)),
            self.MAX_RETRY_DELAY_SECONDS
        )

    def __init__(self, api_key=None):

        api_key = api_key or _get_gemini_api_key()

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found in .env or Streamlit secrets. "
                "Add one, or enter your own Gemini API key in the sidebar."
            )

        self.client = genai.Client(
            api_key=api_key
        )

        # Never store the raw key in shared state.
        self._key_id = hashlib.sha256(
            api_key.encode("utf-8")
        ).hexdigest()[:16]

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

    def generate(
        self,
        prompt,
        attachment_path=None,
        attachment_type=None,
        max_output_tokens=None
    ):

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

        config = None

        if max_output_tokens:
            config = types.GenerateContentConfig(
                max_output_tokens=max_output_tokens
            )

        # Remember the most useful error to show the user:
        # a quota or overload error matters more than a 404
        # from a fallback model.
        rate_limit_error = None
        overload_error = None
        last_error = None

        for model in self.models:

            if (self._key_id, model) in self._unavailable_models:
                continue

            if self._is_cooling_down(model):
                print(
                    f"\nSkipping {model}: quota recently exhausted."
                )
                continue

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
                        config=config,
                    )

                    print(
                        f"SUCCESS: {model}"
                    )

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

                            self._set_cooldown(
                                model,
                                self.PER_DAY_COOLDOWN_SECONDS
                            )

                            break

                        delay = self._parse_retry_delay(
                            error_text
                        )

                        if (
                            delay is not None
                            and delay <= self.MAX_RATE_LIMIT_WAIT_SECONDS
                            and attempt < self.MAX_RETRIES_PER_MODEL
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

                        if attempt < self.MAX_RETRIES_PER_MODEL:

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