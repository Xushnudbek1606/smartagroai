from __future__ import annotations

import base64
import json
import logging
import mimetypes
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AIIntegrationError(Exception):
    """Raised when the configured AI provider fails."""

    def __init__(self, code: str, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass
class AIResult:
    predicted_crop: str | None
    disease_name: str | None
    confidence: float | None
    severity: str | None
    symptoms: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    next_steps: str | None = None
    model_version: str | None = None


_PROMPT_TEMPLATE = """You are a plant pathology assistant for farmers in Uzbekistan.
Analyze the attached photo of a plant leaf/crop.

Respond with ONLY a JSON object using exactly this schema:
{{
  "predicted_crop": string | null,
  "disease_name": string | null,
  "confidence": number between 0 and 1 | null,
  "severity": "low" | "medium" | "high" | "unknown",
  "symptoms": string[],
  "recommendations": string[],
  "next_steps": string | null
}}

Rules:
- The user's crop type hint: {crop_hint}
- The user's region: {region}
- The user's interface language is {language}. Write ALL string values in that language.
- If the image does not clearly show a plant disease, return disease_name=null, confidence=null,
  severity="unknown" and explain in next_steps what the user should do (retake photo, better light, or contact an agronomist).
- Never invent chemical dosages. Recommendations must be general integrated-pest-management advice.
- Always recommend confirming serious cases with a human agronomist.
- Output JSON only, no markdown fences, no commentary."""


def _b64(path: Path) -> tuple[str, str]:
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    return base64.standard_b64encode(path.read_bytes()).decode("ascii"), mime


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError as exc:
                raise AIIntegrationError("bad_model_output", "AI model returned invalid JSON") from exc
        raise AIIntegrationError("bad_model_output", "AI model returned invalid output")


def _normalize(data: dict[str, Any], model_version: str) -> AIResult:
    conf = data.get("confidence")
    try:
        conf = float(conf) if conf is not None else None
    except (TypeError, ValueError):
        conf = None
    if conf is not None:
        conf = max(0.0, min(1.0, conf))

    severity = data.get("severity")
    if severity not in ("low", "medium", "high"):
        severity = "unknown"

    def _strlist(v: Any) -> list[str]:
        if isinstance(v, list):
            return [str(x) for x in v][:10]
        if isinstance(v, str) and v.strip():
            return [v.strip()]
        return []

    return AIResult(
        predicted_crop=_opt_str(data.get("predicted_crop")),
        disease_name=_opt_str(data.get("disease_name")),
        confidence=conf,
        severity=severity,
        symptoms=_strlist(data.get("symptoms")),
        recommendations=_strlist(data.get("recommendations")),
        next_steps=_opt_str(data.get("next_steps")),
        model_version=model_version,
    )


def _opt_str(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


class PlantAIService:
    """Pluggable vision-LLM integration.

    Providers:
      - openai:   OpenAI-compatible chat/completions with image input
      - anthropic: Anthropic messages API with image input
      - custom:   any OpenAI-compatible HTTP endpoint (AI_CUSTOM_BASE_URL)

    When no provider is configured, analyze() raises AIIntegrationError(503)
    so the API can clearly tell the user the integration is not set up,
    instead of pretending a diagnosis exists.
    """

    def analyze(
        self,
        image_path: Path,
        *,
        crop_hint: str | None,
        region: str | None,
        language: str,
    ) -> AIResult:
        settings = get_settings()
        if not settings.ai_configured:
            raise AIIntegrationError(
                "ai_not_configured",
                "AI tashxis xizmati hali sozlanmagan. Administrator AI_API_KEY va AI_MODEL_NAME "
                "muhit o'zgaruvchilarini o'rnatishi kerak. /integration holatini tekshiring.",
                status_code=503,
            )

        prompt = _PROMPT_TEMPLATE.format(
            crop_hint=crop_hint or "unknown",
            region=region or "unknown",
            language=language,
        )
        b64img, mime = _b64(image_path)

        provider = settings.AI_PROVIDER.lower()
        if provider in ("openai", "custom"):
            raw = self._call_openai_compatible(settings, prompt, b64img, mime)
        elif provider == "anthropic":
            raw = self._call_anthropic(settings, prompt, b64img, mime)
        else:
            raise AIIntegrationError(
                "ai_unknown_provider", f"Unknown AI provider: {settings.AI_PROVIDER}", 503
            )

        data = _extract_json(raw)
        return _normalize(data, settings.AI_MODEL_NAME or provider)

    # ----- providers -----

    def _call_openai_compatible(self, settings, prompt: str, b64img: str, mime: str) -> str:
        base = (
            settings.AI_CUSTOM_BASE_URL.rstrip("/")
            if settings.AI_PROVIDER == "custom" and settings.AI_CUSTOM_BASE_URL
            else "https://api.openai.com/v1"
        )
        headers = {"Content-Type": "application/json"}
        if settings.AI_API_KEY:
            headers["Authorization"] = f"Bearer {settings.AI_API_KEY}"
        body = {
            "model": settings.AI_MODEL_NAME or "gpt-4o-mini",
            "temperature": 0.1,
            "max_tokens": 1200,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64img}"},
                        },
                    ],
                }
            ],
        }
        try:
            with httpx.Client(timeout=settings.AI_TIMEOUT_SECONDS) as client:
                resp = client.post(f"{base}/chat/completions", headers=headers, json=body)
        except httpx.HTTPError as exc:
            raise AIIntegrationError("ai_unreachable", "AI xizmatiga ulanib bo'lmadi") from exc
        if resp.status_code == 401:
            raise AIIntegrationError("ai_auth_failed", "AI API kaliti noto'g'ri yoki muddati tugagan", 502)
        if resp.status_code != 200:
            logger.warning("AI provider returned %s", resp.status_code)
            raise AIIntegrationError("ai_provider_error", "AI xizmati xatolik qaytardi", 502)
        try:
            return resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            raise AIIntegrationError("bad_model_output", "AI modelidan kutilmagan javob keldi") from exc

    def _call_anthropic(self, settings, prompt: str, b64img: str, mime: str) -> str:
        headers = {
            "x-api-key": settings.AI_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        body = {
            "model": settings.AI_MODEL_NAME or "claude-3-5-sonnet-latest",
            "max_tokens": 1200,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": mime, "data": b64img},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
        try:
            with httpx.Client(timeout=settings.AI_TIMEOUT_SECONDS) as client:
                resp = client.post(
                    "https://api.anthropic.com/v1/messages", headers=headers, json=body
                )
        except httpx.HTTPError as exc:
            raise AIIntegrationError("ai_unreachable", "AI xizmatiga ulanib bo'lmadi") from exc
        if resp.status_code == 401:
            raise AIIntegrationError("ai_auth_failed", "AI API kaliti noto'g'ri", 502)
        if resp.status_code != 200:
            logger.warning("Anthropic returned %s", resp.status_code)
            raise AIIntegrationError("ai_provider_error", "AI xizmati xatolik qaytardi", 502)
        try:
            blocks = resp.json()["content"]
            return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        except (KeyError, ValueError) as exc:
            raise AIIntegrationError("bad_model_output", "AI modelidan kutilmagan javob keldi") from exc


plant_ai_service = PlantAIService()
