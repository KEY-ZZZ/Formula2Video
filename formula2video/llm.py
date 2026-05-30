"""统一 LLM 接口层。

支持 Anthropic 和 OpenAI 两家, 运行时按配置切换。
所有 Agent 通过 `complete_json()` 获取结构化输出, 内部做 JSON 解析与重试。

设计:
- 无 API key 时进入 mock 模式, 返回占位数据, 便于离线跑通整条链路。
- complete_json 强制要求模型输出 JSON, 并做容错解析 (剥离 ```json 围栏)。
"""

from __future__ import annotations

import json
import re
from typing import Any

from formula2video.config import config


class LLMError(RuntimeError):
    """LLM 调用失败。"""


def _strip_code_fence(text: str) -> str:
    """剥离 ```json ... ``` 或 ``` ... ``` 围栏, 返回纯 JSON 文本。"""
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    return text


class LLMClient:
    """对两家 provider 的薄封装。"""

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        self.provider = provider or config.llm_provider
        self.model = model or config.llm_model
        self._client: Any = None
        self.mock = False
        self._init_backend()

    def _init_backend(self) -> None:
        if self.provider == "anthropic":
            if not config.anthropic_api_key:
                self.mock = True
                return
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=config.anthropic_api_key)
            except ImportError as exc:  # pragma: no cover
                raise LLMError("未安装 anthropic, 请 pip install anthropic") from exc
        elif self.provider == "openai":
            if not config.openai_api_key:
                self.mock = True
                return
            try:
                import openai

                self._client = openai.OpenAI(api_key=config.openai_api_key)
            except ImportError as exc:  # pragma: no cover
                raise LLMError("未安装 openai, 请 pip install openai") from exc
        else:
            raise LLMError(f"未知 provider: {self.provider}")

    # ------------------------------------------------------------------ #
    def complete(self, system: str, user: str, max_tokens: int = 4096) -> str:
        """返回纯文本补全。mock 模式下报错 (文本补全无通用占位)。"""
        if self.mock:
            raise LLMError(
                "当前为 mock 模式 (无 API key)。complete() 需要真实 LLM; "
                "结构化调用请用 complete_json 并传 mock_fallback。"
            )
        if self.provider == "anthropic":
            resp = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return resp.content[0].text
        # openai
        resp = self._client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content or ""

    def complete_json(
        self,
        system: str,
        user: str,
        *,
        mock_fallback: dict | list | None = None,
        max_tokens: int = 4096,
    ) -> Any:
        """要求模型返回 JSON, 解析为 Python 对象。

        mock 模式下直接返回 mock_fallback (若提供), 否则报错。
        """
        if self.mock:
            if mock_fallback is not None:
                return mock_fallback
            raise LLMError("mock 模式且未提供 mock_fallback")

        raw = self.complete(
            system + "\n\n严格只输出合法 JSON, 不要任何额外说明文字。",
            user,
            max_tokens=max_tokens,
        )
        cleaned = _strip_code_fence(raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise LLMError(f"模型输出不是合法 JSON:\n{raw[:500]}") from exc
