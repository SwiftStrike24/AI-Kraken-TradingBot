import os
import json
import time
from typing import Any, Dict, Optional

import google.generativeai as genai

from bot.logger import get_logger

logger = get_logger(__name__)

DEFAULT_MODEL = os.getenv("GEMINI_REFLECTION_MODEL", "gemini-2.5-pro")
DEFAULT_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.3"))
DEFAULT_TOP_P = float(os.getenv("GEMINI_TOP_P", "0.9"))
DEFAULT_MAX_OUTPUT_TOKENS = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "6000"))
RELAX_SAFETY = os.getenv("GEMINI_RELAX_SAFETY", "false").lower() in ("1", "true", "yes")


class GeminiClient:
    """Thin wrapper for Google Gemini API for long-context reflection tasks."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required for reflection tasks")
        genai.configure(api_key=api_key)

        self.model_name = model or DEFAULT_MODEL
        # Optional safety settings (relaxed): BLOCK_ONLY_HIGH reduces false positives
        safety_settings = None
        if RELAX_SAFETY:
            try:
                safety_settings = [
                    genai.types.SafetySetting(category=cat, threshold="BLOCK_ONLY_HIGH")
                    for cat in (
                        "HARM_CATEGORY_HARASSMENT",
                        "HARM_CATEGORY_HATE_SPEECH",
                        "HARM_CATEGORY_SEXUAL_CONTENT",
                        "HARM_CATEGORY_DANGEROUS_CONTENT",
                    )
                ]
            except Exception:
                safety_settings = None

        # Try to set response_mime_type for strict JSON if supported by the SDK
        try:
            self.generation_config = genai.types.GenerationConfig(
                temperature=DEFAULT_TEMPERATURE,
                top_p=DEFAULT_TOP_P,
                max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
                response_mime_type="application/json",
            )
        except TypeError:
            self.generation_config = genai.types.GenerationConfig(
                temperature=DEFAULT_TEMPERATURE,
                top_p=DEFAULT_TOP_P,
                max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
            )

        self._model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            safety_settings=safety_settings,
        )
        logger.info(f"Gemini client initialized for model={self.model_name}")

    def _extract_text(self, response) -> str:
        """Robustly extract text from response.candidates/parts if response.text is unavailable."""
        try:
            if hasattr(response, "text") and response.text:
                return response.text
        except Exception:
            pass
        try:
            if getattr(response, "candidates", None):
                parts = []
                for cand in response.candidates:
                    fr = getattr(cand, "finish_reason", None)
                    if fr is not None:
                        logger.info(f"Gemini candidate finish_reason={fr}")
                    content = getattr(cand, "content", None)
                    if content and getattr(content, "parts", None):
                        for p in content.parts:
                            # parts may be objects with 'text' or dict-like
                            val = getattr(p, "text", None)
                            if not val and isinstance(p, dict):
                                val = p.get("text")
                            if val:
                                parts.append(val)
                return "\n".join(parts).strip()
        except Exception as e:
            logger.warning(f"Failed to extract text from Gemini candidates: {e}")
        return ""

    def generate_json(self, system: str, prompt: str) -> Dict[str, Any]:
        """Generate a JSON object from Gemini by asking it to return strict JSON only.
        If the first response is not valid JSON, run a compact re-ask to convert it to JSON.
        Returns an empty dict if parsing ultimately fails.
        """
        start = time.time()
        try:
            parts = [system.strip(), "\n\n", "STRICT INSTRUCTION: Return a single JSON object only.", "\n\n", prompt.strip()]
            response = self._model.generate_content(parts)
            text = self._extract_text(response)
            if not text:
                # Log finish reasons if available
                try:
                    if getattr(response, "candidates", None):
                        for cand in response.candidates:
                            logger.warning(f"Empty content; candidate finish_reason={getattr(cand, 'finish_reason', None)} safety_ratings={getattr(cand, 'safety_ratings', None)}")
                except Exception:
                    pass
            elapsed = time.time() - start
            logger.info(f"Gemini call completed in {elapsed:.2f}s, response chars={len(text)}")
            try:
                if text:
                    return json.loads(text)
                else:
                    raise json.JSONDecodeError("empty", "", 0)
            except json.JSONDecodeError:
                logger.warning("Gemini response was not valid JSON; attempting JSON reformat pass")
                # Re-ask: convert to JSON strictly
                fix_prompt = (
                    "You produced non-JSON text or empty output. Convert the following content into a single valid JSON object that\n"
                    "matches the described schema. Do not include any commentary. If empty, create a best-effort JSON per schema from prior reasoning.\n\nCONTENT:\n" + (text or ""))
                fix_response = self._model.generate_content(["Return only JSON.", fix_prompt])
                fix_text = self._extract_text(fix_response)
                try:
                    return json.loads(fix_text)
                except Exception:
                    logger.warning("Gemini JSON reformat pass failed; returning raw_text wrapper")
                    return {"raw_text": text}
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return {"error": str(e)}
