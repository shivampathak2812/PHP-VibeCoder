import os
import time
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


class GeminiModelManager:

    PRIMARY_MODEL = "gemini-3.6-flash"
    FALLBACK_MODEL = "gemini-3.5-flash"

    MAX_RETRIES_PER_MODEL = 2
    RETRY_DELAY_SECONDS = 5

    def __init__(self):

        api_key = _get_gemini_api_key()

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found in .env or Streamlit secrets"
            )

        self.client = genai.Client(
            api_key=api_key
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

    def generate(
        self,
        prompt,
        attachment_path=None,
        attachment_type=None
    ):

        models = [
            self.PRIMARY_MODEL,
            self.FALLBACK_MODEL,
        ]

        last_error = None

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

        for model in models:

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
                    # RATE LIMIT
                    # ----------------------------------------

                    if "429" in error_text:

                        print(
                            f"Quota/rate limit detected for {model}."
                        )

                        break

                    # ----------------------------------------
                    # TEMPORARY SERVER UNAVAILABLE
                    # ----------------------------------------

                    if "503" in error_text:

                        if attempt < self.MAX_RETRIES_PER_MODEL:

                            print(
                                f"Model temporarily unavailable. "
                                f"Retrying in "
                                f"{self.RETRY_DELAY_SECONDS} seconds..."
                            )

                            time.sleep(
                                self.RETRY_DELAY_SECONDS
                            )

                            continue

                        print(
                            f"{model} unavailable after "
                            f"{self.MAX_RETRIES_PER_MODEL} attempts."
                        )

                        break

                    # ----------------------------------------
                    # OTHER TEMPORARY ERRORS
                    # ----------------------------------------

                    if any(
                        code in error_text
                        for code in [
                            "500",
                            "502",
                            "504",
                            "UNAVAILABLE",
                            "INTERNAL"
                        ]
                    ):

                        if attempt < self.MAX_RETRIES_PER_MODEL:

                            print(
                                f"Temporary Gemini error. "
                                f"Retrying in "
                                f"{self.RETRY_DELAY_SECONDS} seconds..."
                            )

                            time.sleep(
                                self.RETRY_DELAY_SECONDS
                            )

                            continue

                    # ----------------------------------------
                    # UNKNOWN / NON-RETRYABLE ERROR
                    # ----------------------------------------

                    break

        return {
            "success": False,
            "model": None,
            "response": None,
            "error": str(last_error),
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