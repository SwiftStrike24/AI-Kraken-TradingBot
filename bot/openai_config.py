import os

DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-5-2025-08-07")
FALLBACK_OPENAI_MODEL = os.getenv("OPENAI_FALLBACK_MODEL", "gpt-4o")

def get_default_openai_model() -> str:
    return DEFAULT_OPENAI_MODEL

def get_fallback_openai_model() -> str:
    return FALLBACK_OPENAI_MODEL


def build_chat_completion_params(
    model: str,
    messages: list,
    temperature: float | None = None,
    response_format: dict | None = None,
) -> dict:
    """Construct params for client.chat.completions.create() compatible with GPT-5.
    - GPT-5 requires 'max_completion_tokens' instead of 'max_tokens'.
    - GPT-5 may have strict limits on other params like 'temperature'.
    """
    params: dict = {"model": model, "messages": messages}
    if response_format is not None:
        params["response_format"] = response_format
    if temperature is not None:
        # As of Aug 2025, GPT-5 API is restrictive on temperature.
        # We will only pass the temperature parameter for non-GPT-5 models
        # to avoid 'unsupported value' errors.
        if not model.startswith("gpt-5"):
            params["temperature"] = temperature
    return params
