"""Unified LLM interface layer.

Wraps the Anthropic and OpenAI SDKs behind one tiny interface, switching at
runtime based on :data:`formula2video.config.config`. When no API key is
available (or the SDK is not installed) the client transparently runs in
*mock mode*, so the entire pipeline can run end-to-end offline.

Provider SDK imports are deliberately performed *inside* methods (lazy) and
guarded with try/except, so this module imports cleanly even when neither
``anthropic`` nor ``openai`` is installed.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from formula2video.config import config


class LLMError(RuntimeError):
    """Raised when an LLM call fails or returns unusable output."""


def _strip_json_fences(text: str) -> str:
    """Remove ```json ... ``` (or plain ``` ... ```) fences around a payload."""
    s = text.strip()
    if s.startswith("```"):
        # Drop the opening fence line (``` or ```json).
        first_newline = s.find("\n")
        if first_newline != -1:
            s = s[first_newline + 1:]
        # Drop a trailing fence.
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
    return s.strip()


class LLMClient:
    """Provider-agnostic chat client.

    Parameters
    ----------
    provider:
        ``"anthropic"`` or ``"openai"``. Defaults to ``config.llm_provider``.

    The ``mock`` attribute is ``True`` when no usable API key is configured.
    Tests can also force mock mode by setting ``client.mock = True``.
    """

    def __init__(self, provider: Optional[str] = None) -> None:
        self.provider = provider or config.llm_provider
        # Enter mock mode automatically when no API key is configured.
        self.mock: bool = not config.has_api_key

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def complete(self, system: str, user: str) -> str:
        """Return the model's plain-text completion for a system+user prompt."""
        if self.mock:
            raise LLMError("LLMClient is in mock mode; no completion available.")
        if self.provider == "openai":
            return self._complete_openai(system, user)
        return self._complete_anthropic(system, user)

    def complete_json(
        self,
        system: str,
        user: str,
        *,
        mock_fallback: Any = None,
    ) -> Any:
        """Ask the model for JSON and parse it.

        In mock mode (or on parse failure with a fallback provided) returns
        ``mock_fallback``. Otherwise strips ```json fences and ``json.loads``.
        """
        if self.mock:
            return mock_fallback
        raw = self.complete(system, user)
        cleaned = _strip_json_fences(raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            if mock_fallback is not None:
                return mock_fallback
            raise LLMError(f"Model did not return valid JSON: {exc}\n{raw}") from exc

    # ------------------------------------------------------------------ #
    # Provider backends (lazy imports)
    # ------------------------------------------------------------------ #
    def _complete_anthropic(self, system: str, user: str) -> str:
        try:
            import anthropic  # noqa: WPS433 (lazy import is intentional)
        except ImportError as exc:  # pragma: no cover - depends on env
            raise LLMError("anthropic SDK is not installed.") from exc
        try:
            client = anthropic.Anthropic(api_key=config.anthropic_api_key)
            resp = client.messages.create(
                model=config.anthropic_model,
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return "".join(
                block.text for block in resp.content if getattr(block, "type", "") == "text"
            )
        except Exception as exc:  # pragma: no cover - network path
            raise LLMError(f"Anthropic call failed: {exc}") from exc

    def _complete_openai(self, system: str, user: str) -> str:
        try:
            import openai  # noqa: WPS433
        except ImportError as exc:  # pragma: no cover
            raise LLMError("openai SDK is not installed.") from exc
        try:
            client = openai.OpenAI(api_key=config.openai_api_key)
            resp = client.chat.completions.create(
                model=config.openai_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:  # pragma: no cover
            raise LLMError(f"OpenAI call failed: {exc}") from exc
