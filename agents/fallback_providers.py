"""
Free OpenAI-compatible LLM providers (Groq, NVIDIA NIM).

GeminiModelManager uses them in two ways:

* light tasks (explain, chat, intent classification): tried FIRST, so
  the small Gemini daily quota is saved for project generation;
* heavy tasks (generate, refactor, debug): tried only when every
  Gemini model has failed.

Both speak the OpenAI "chat/completions" format, so plain HTTP is
enough: no extra Python package is needed.

Keys (put them in .env or Streamlit secrets):

    GROQ_API_KEY=...        https://console.groq.com/keys
    NVIDIA_API_KEY=...      https://build.nvidia.com

Several models per provider (comma separated, biggest first). Free
limits are usually per model, so every extra model adds quota:

    GROQ_MODELS=openai/gpt-oss-120b,openai/gpt-oss-20b
    NVIDIA_MODELS=nvidia/nemotron-3-super-120b-a12b

The old single-model settings GROQ_MODEL / NVIDIA_MODEL still work.

A provider without a key is skipped silently. A model the provider
does not know (HTTP 404) is skipped for the rest of the session, so a
wrong name only costs one request.

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
        "models_env": "GROQ_MODELS",
        "model_env": "GROQ_MODEL",
        "default_models": [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
        ],
        "url": "https://api.groq.com/openai/v1/chat/completions",
    },
    {
        "name": "nvidia",
        "key_env": "NVIDIA_API_KEY",
        "models_env": "NVIDIA_MODELS",
        "model_env": "NVIDIA_MODEL",
        "default_models": [
            "nvidia/nemotron-3-super-120b-a12b",
        ],
        "url": "https://integrate.api.nvidia.com/v1/chat/completions",
    },
]


# Reasoning models count hidden thinking inside max_tokens, so a very
# small limit (e.g. 8) would come back empty.
MIN_OUTPUT_TOKENS = 1024
MAX_OUTPUT_TOKENS = 32768

REQUEST_TIMEOUT_SECONDS = 180
DEFAULT_COOLDOWN_SECONDS = 60
MAX_COOLDOWN_SECONDS = 24 * 60 * 60


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


def _model_list(provider):
    """GROQ_MODELS (list) > GROQ_MODEL (single) > defaults."""

    value = _read_setting(provider["models_env"])

    if value:
        models = [m.strip() for m in value.split(",") if m.strip()]

        if models:
            return models

    single = _read_setting(provider["model_env"])

    if single:
        return [single]

    return list(provider["default_models"])


def _extra_params(model):
    """Optional request parameters that only some models accept."""

    # gpt-oss is a reasoning model; keep its hidden thinking short.
    if "gpt-oss" in model:
        return {"reasoning_effort": "low"}

    # Qwen on Groq otherwise prints its <think>...</think> text inside
    # the answer.
    if "qwen" in model:
        return {"reasoning_format": "hidden"}

    return {}


# Models whose output limit is below MAX_OUTPUT_TOKENS. Asking for more
# makes the provider reject the whole request (HTTP 400).
MODEL_MAX_OUTPUT_TOKENS = {
    "qwen/qwen3.8-27b": 16384,
}


class FallbackProviders:

    # All shared across instances (one Streamlit process):
    # {"provider/model": skip_until_timestamp}
    _cooldowns = {}

    # Models that returned 404 (wrong / retired name).
    _unavailable = set()

    # Models that rejected the optional extra parameters (HTTP 400).
    _no_extra = set()

    def __init__(self):
        self.providers = []
        self.last_model = None

        # One entry per (provider, model), in priority order:
        # all Groq models, then all NVIDIA models.
        for provider in PROVIDERS:

            key = _read_setting(provider["key_env"])

            if not key:
                continue

            for model in _model_list(provider):

                self.providers.append(
                    {
                        "name": provider["name"],
                        "url": provider["url"],
                        "key": key,
                        "model": model,
                        "label": f"{provider['name']}/{model}",
                        "extra": _extra_params(model),
                    }
                )

    @property
    def available(self):
        return bool(self.providers)

    # ------------------------------------------------------------

    def _ordered(self, small_first=False):
        """
        Entries that are worth trying right now.

        small_first: inside each provider, try the smaller models first
        (lists are written biggest first). Used for tiny jobs such as
        intent classification, where a big model is wasted quota.
        """

        entries = list(self.providers)

        if small_first:
            names = []

            for entry in entries:
                if entry["name"] not in names:
                    names.append(entry["name"])

            entries = [
                entry
                for name in names
                for entry in reversed(
                    [e for e in self.providers if e["name"] == name]
                )
            ]

        result = []

        for entry in entries:

            label = entry["label"]

            if label in self._unavailable:
                continue

            if time.time() < self._cooldowns.get(label, 0):
                print(f"Skipping {label}: cooling down.")
                continue

            result.append(entry)

        return result

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

    def _request(self, provider, prompt, max_output_tokens, stream):

        payload = {
            "model": provider["model"],
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": min(
                max(max_output_tokens or 4096, MIN_OUTPUT_TOKENS),
                MODEL_MAX_OUTPUT_TOKENS.get(
                    provider["model"],
                    MAX_OUTPUT_TOKENS
                )
            ),
        }

        if stream:
            payload["stream"] = True

        if provider["label"] not in self._no_extra:
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

    def _call(self, provider, prompt, max_output_tokens):

        with self._request(
            provider,
            prompt,
            max_output_tokens,
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

    def _call_stream(self, provider, prompt, max_output_tokens):
        """Yield text pieces from an OpenAI-style server-sent stream."""

        with self._request(
            provider,
            prompt,
            max_output_tokens,
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

    def _handle_http_error(self, provider, error):
        """
        Decide what an HTTP error means for this model.
        Returns True if the same model should be retried once.
        """

        label = provider["label"]

        body = ""

        try:
            body = error.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass

        print(f"FAILED: {label} HTTP {error.code} {body}")

        # An unsupported optional parameter: retry once without it,
        # and never send it to this model again.
        if (
            error.code == 400
            and provider["extra"]
            and label not in self._no_extra
        ):
            self._no_extra.add(label)
            return True

        # Wrong or retired model name.
        if error.code == 404:
            self._unavailable.add(label)

        # Rate limit: only THIS model cools down; the provider's other
        # models have their own quota and are still tried.
        elif error.code == 429:

            wait = DEFAULT_COOLDOWN_SECONDS

            try:
                wait = float(error.headers.get("Retry-After"))
            except Exception:
                pass

            self._cooldowns[label] = time.time() + min(
                wait,
                MAX_COOLDOWN_SECONDS
            )

        # 413 (prompt larger than this model's per-minute token limit)
        # and other errors: just move on to the next model.

        return False

    # ------------------------------------------------------------

    def generate(
        self,
        prompt,
        attachment_path=None,
        attachment_type=None,
        max_output_tokens=None,
        small_first=False
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

        for provider in self._ordered(small_first):

            label = provider["label"]

            print(f"\nTrying fallback: {label}")

            for attempt in (1, 2):

                try:

                    text = self._call(
                        provider,
                        full_prompt,
                        max_output_tokens
                    )

                    print(f"SUCCESS: {label}")

                    self.last_model = label

                    return {
                        "success": True,
                        "model": label,
                        "response": text,
                    }

                except urllib.error.HTTPError as e:

                    if self._handle_http_error(provider, e):
                        continue

                    errors.append(f"{label}: HTTP {e.code}")

                    break

                except Exception as e:

                    print(f"FAILED: {label} {e}")

                    errors.append(f"{label}: {e}")

                    break

        return {
            "success": False,
            "model": None,
            "response": None,
            "error": (
                "Fallback providers failed: "
                + ("; ".join(errors) or "all models cooling down")
            ),
        }


    # ------------------------------------------------------------
    # STREAMING
    # ------------------------------------------------------------

    def generate_stream(
        self,
        prompt,
        attachment_path=None,
        attachment_type=None,
        max_output_tokens=None,
        small_first=False
    ):
        """
        Yields text pieces as they arrive. After the first piece,
        self.last_model holds the model name. Raises RuntimeError if
        no model could start an answer.
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

        for provider in self._ordered(small_first):

            label = provider["label"]

            print(f"\nStreaming from fallback: {label}")

            started = False

            for attempt in (1, 2):

                try:

                    for text in self._call_stream(
                        provider,
                        full_prompt,
                        max_output_tokens
                    ):

                        if not started:
                            started = True
                            self.last_model = label

                        yield text

                    if started:
                        return

                    errors.append(f"{label}: empty answer")

                    break

                except urllib.error.HTTPError as e:

                    if started:
                        raise

                    if self._handle_http_error(provider, e):
                        continue

                    errors.append(f"{label}: HTTP {e.code}")

                    break

                except Exception as e:

                    if started:
                        raise

                    print(f"FAILED: {label} {e}")

                    errors.append(f"{label}: {e}")

                    break

        raise RuntimeError(
            "Fallback providers failed: "
            + ("; ".join(errors) or "all models cooling down")
        )