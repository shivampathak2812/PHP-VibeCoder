"""
Free fallback LLM providers, used only when every Gemini model fails
(quota used up, overloaded, ...).

Order: Groq -> NVIDIA NIM.

Both speak the OpenAI "chat/completions" format, so plain HTTP is
enough: no extra Python package is needed.

Keys (put them in .env or Streamlit secrets):

    GROQ_API_KEY=...        https://console.groq.com/keys
    NVIDIA_API_KEY=...      https://build.nvidia.com

Optional model overrides:

    GROQ_MODEL=openai/gpt-oss-120b
    NVIDIA_MODEL=nvidia/nemotron-3-super-120b-a12b

A provider without a key is skipped silently.

Note: free tiers may log prompts or use them for training.
Never put passwords or secrets in a prompt.
"""

import os
import json
import time
import urllib.error
import urllib.request


PROVIDERS = [
    {
        "name": "groq",
        "key_env": "GROQ_API_KEY",
        "model_env": "GROQ_MODEL",
        "default_model": "openai/gpt-oss-120b",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        # gpt-oss is a reasoning model; keep its hidden thinking short.
        "extra": {"reasoning_effort": "low"},
    },
    {
        "name": "nvidia",
        "key_env": "NVIDIA_API_KEY",
        "model_env": "NVIDIA_MODEL",
        "default_model": "nvidia/nemotron-3-super-120b-a12b",
        "url": "https://integrate.api.nvidia.com/v1/chat/completions",
        "extra": {},
    },
]


# Reasoning models count hidden thinking inside max_tokens, so a very
# small limit (e.g. 8) would come back empty.
MIN_OUTPUT_TOKENS = 1024
MAX_OUTPUT_TOKENS = 32768

REQUEST_TIMEOUT_SECONDS = 180
DEFAULT_COOLDOWN_SECONDS = 60


def _read_setting(name):
    """Environment / .env first, then Streamlit secrets."""

    value = os.getenv(name)

    if value:
        return value.strip()

    try:
        import streamlit as st
        value = st.secrets.get(name)
    except Exception:
        value = None

    return str(value).strip() if value else None


class FallbackProviders:

    # Shared across instances: {provider_name: skip_until_timestamp}
    _cooldowns = {}

    def __init__(self):
        self.providers = []
        self.last_model = None

        for provider in PROVIDERS:

            key = _read_setting(provider["key_env"])

            if not key:
                continue

            self.providers.append(
                {
                    **provider,
                    "key": key,
                    "model": (
                        _read_setting(provider["model_env"])
                        or provider["default_model"]
                    ),
                }
            )

    @property
    def available(self):
        return bool(self.providers)

    # ------------------------------------------------------------

    def _build_prompt(
        self,
        prompt,
        attachment_path,
        attachment_type
    ):
        """
        These models are text-only. A text/document attachment is added
        to the prompt; an image makes the fallback unusable.
        """

        if not attachment_path:
            return prompt

        if attachment_type == "photo":
            return None

        try:

            with open(
                attachment_path,
                "r",
                encoding="utf-8",
                errors="replace"
            ) as file:

                content = file.read()

        except Exception:
            return prompt

        return (
            f"{prompt}\n\nATTACHED FILE "
            f"({os.path.basename(attachment_path)}):\n{content}"
        )

    def _request(self, provider, prompt, max_output_tokens, use_extra, stream):

        payload = {
            "model": provider["model"],
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": min(
                max(max_output_tokens or 4096, MIN_OUTPUT_TOKENS),
                MAX_OUTPUT_TOKENS
            ),
        }

        if stream:
            payload["stream"] = True

        if use_extra:
            payload.update(provider["extra"])

        request = urllib.request.Request(
            provider["url"],
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {provider['key']}",
                # Some gateways reject the default Python user agent.
                "User-Agent": "php-vibecoder/1.0",
            },
            method="POST"
        )

        return urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT_SECONDS
        )

    def _call(self, provider, prompt, max_output_tokens, use_extra=True):

        with self._request(
            provider,
            prompt,
            max_output_tokens,
            use_extra,
            stream=False
        ) as response:

            data = json.loads(
                response.read().decode("utf-8")
            )

        message = data["choices"][0]["message"]

        text = (message.get("content") or "").strip()

        if not text:
            raise RuntimeError(
                "Model returned an empty answer."
            )

        return text

    def _call_stream(
        self,
        provider,
        prompt,
        max_output_tokens,
        use_extra=True
    ):
        """Yield text pieces from an OpenAI-style server-sent stream."""

        with self._request(
            provider,
            prompt,
            max_output_tokens,
            use_extra,
            stream=True
        ) as response:

            for raw_line in response:

                line = raw_line.decode("utf-8", "replace").strip()

                if not line.startswith("data:"):
                    continue

                data = line[5:].strip()

                if data == "[DONE]":
                    break

                try:
                    event = json.loads(data)
                except ValueError:
                    continue

                choices = event.get("choices") or []

                if not choices:
                    continue

                delta = choices[0].get("delta") or {}

                # Only the final answer; hidden "reasoning" is ignored.
                text = delta.get("content")

                if text:
                    yield text

    def _remember_rate_limit(self, name, error):

        wait = DEFAULT_COOLDOWN_SECONDS

        try:
            wait = float(error.headers.get("Retry-After"))
        except Exception:
            pass

        self._cooldowns[name] = time.time() + min(
            wait,
            24 * 60 * 60
        )

    # ------------------------------------------------------------

    def generate(
        self,
        prompt,
        attachment_path=None,
        attachment_type=None,
        max_output_tokens=None
    ):
        """
        Same result shape as GeminiModelManager.generate():
        {"success", "model", "response", "error"}.
        """

        if not self.providers:
            return {
                "success": False,
                "model": None,
                "response": None,
                "error": "No fallback provider key configured.",
            }

        full_prompt = self._build_prompt(
            prompt,
            attachment_path,
            attachment_type
        )

        if full_prompt is None:
            return {
                "success": False,
                "model": None,
                "response": None,
                "error": (
                    "Fallback models cannot read images; "
                    "only Gemini can use an image attachment."
                ),
            }

        errors = []

        for provider in self.providers:

            name = provider["name"]

            if time.time() < self._cooldowns.get(name, 0):
                print(f"Skipping {name}: cooling down.")
                errors.append(f"{name}: cooling down")
                continue

            print(
                f"\nTrying fallback: {name} / {provider['model']}"
            )

            use_extra = True

            for attempt in (1, 2):

                try:

                    text = self._call(
                        provider,
                        full_prompt,
                        max_output_tokens,
                        use_extra=use_extra
                    )

                    print(f"SUCCESS: {name}")

                    return {
                        "success": True,
                        "model": f"{name}/{provider['model']}",
                        "response": text,
                    }

                except urllib.error.HTTPError as e:

                    body = ""

                    try:
                        body = e.read().decode("utf-8", "replace")[:300]
                    except Exception:
                        pass

                    print(f"FAILED: {name} HTTP {e.code} {body}")

                    # An unsupported optional parameter: retry once
                    # without it.
                    if (
                        e.code == 400
                        and use_extra
                        and provider["extra"]
                    ):
                        use_extra = False
                        continue

                    if e.code == 429:
                        self._remember_rate_limit(name, e)

                    errors.append(f"{name}: HTTP {e.code}")

                    break

                except Exception as e:

                    print(f"FAILED: {name} {e}")

                    errors.append(f"{name}: {e}")

                    break

        return {
            "success": False,
            "model": None,
            "response": None,
            "error": "Fallback providers failed: " + "; ".join(errors),
        }


    # ------------------------------------------------------------
    # STREAMING
    # ------------------------------------------------------------

    def generate_stream(
        self,
        prompt,
        attachment_path=None,
        attachment_type=None,
        max_output_tokens=None
    ):
        """
        Yields text pieces as they arrive. After the first piece,
        self.last_model holds the model name. Raises RuntimeError if
        no provider could start an answer.
        """

        self.last_model = None

        if not self.providers:
            raise RuntimeError(
                "No fallback provider key configured."
            )

        full_prompt = self._build_prompt(
            prompt,
            attachment_path,
            attachment_type
        )

        if full_prompt is None:
            raise RuntimeError(
                "Fallback models cannot read images; "
                "only Gemini can use an image attachment."
            )

        errors = []

        for provider in self.providers:

            name = provider["name"]

            if time.time() < self._cooldowns.get(name, 0):
                errors.append(f"{name}: cooling down")
                continue

            print(
                f"\nStreaming from fallback: {name} / {provider['model']}"
            )

            started = False
            use_extra = True

            for attempt in (1, 2):

                try:

                    for text in self._call_stream(
                        provider,
                        full_prompt,
                        max_output_tokens,
                        use_extra=use_extra
                    ):

                        if not started:
                            started = True
                            self.last_model = (
                                f"{name}/{provider['model']}"
                            )

                        yield text

                    if started:
                        return

                    errors.append(f"{name}: empty answer")

                    break

                except urllib.error.HTTPError as e:

                    if started:
                        raise

                    print(f"FAILED: {name} HTTP {e.code}")

                    if (
                        e.code == 400
                        and use_extra
                        and provider["extra"]
                    ):
                        use_extra = False
                        continue

                    if e.code == 429:
                        self._remember_rate_limit(name, e)

                    errors.append(f"{name}: HTTP {e.code}")

                    break

                except Exception as e:

                    if started:
                        raise

                    print(f"FAILED: {name} {e}")

                    errors.append(f"{name}: {e}")

                    break

        raise RuntimeError(
            "Fallback providers failed: " + "; ".join(errors)
        )