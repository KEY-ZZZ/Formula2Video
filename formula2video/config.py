"""Runtime configuration for Formula2Video.

Values are read from environment variables so the pipeline can switch LLM
providers and output locations without code changes. When no API key is
present the LLM layer transparently falls back to mock mode.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(*names: str, default: str = "") -> str:
    for name in names:
        val = os.environ.get(name)
        if val:
            return val
    return default


@dataclass
class Config:
    """Global configuration object."""

    # LLM provider: "anthropic" or "openai".
    llm_provider: str = field(default_factory=lambda: _env("F2V_LLM_PROVIDER", default="anthropic"))

    anthropic_api_key: str = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))
    anthropic_model: str = field(default_factory=lambda: _env("F2V_ANTHROPIC_MODEL", default="claude"))

    openai_api_key: str = field(default_factory=lambda: _env("OPENAI_API_KEY"))
    openai_model: str = field(default_factory=lambda: _env("F2V_OPENAI_MODEL", default="gpt"))

    # Rendering / output.
    bg_color: str = field(default_factory=lambda: _env("F2V_BG_COLOR", default="#000000"))
    work_dir: Path = field(default_factory=lambda: Path(_env("F2V_WORK_DIR", default="./.f2v_work")))
    output_dir: Path = field(default_factory=lambda: Path(_env("F2V_OUTPUT_DIR", default="./output")))

    @property
    def has_api_key(self) -> bool:
        if self.llm_provider == "openai":
            return bool(self.openai_api_key)
        return bool(self.anthropic_api_key)

    def ensure_dirs(self) -> None:
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


# A module-level singleton used across the codebase. Tests monkeypatch its
# attributes (e.g. work_dir / output_dir) to redirect filesystem output.
config = Config()
