"""OpenAI-Compatible 大模型适配层

只做四件事：
1. 统一 chat / vision / JSON / Function-Calling 四种调用方式；
2. 失败重试 + 超时控制，避免演示时被一次性网络抖动打断；
3. 记录 token 用量与耗时，供成本测算与技术报告使用；
4. 对不支持 response_format 的供应商做容错 JSON 解析。
"""
from __future__ import annotations

import base64
import json
import re
import threading
import time
from typing import Any

import requests

from . import config

# 全局限流：免费额度下并发调用极易触发 429，这里做串行化 + 最小间隔
_RATE_LOCK = threading.Lock()
_LAST_CALL = [0.0]
_MIN_INTERVAL = float(__import__("os").getenv("LLM_MIN_INTERVAL", "1.0"))


class LLMError(RuntimeError):
    pass


def _extract_json(text: str) -> dict:
    """从模型输出里抠出第一个完整 JSON 对象，兼容 ```json 包裹与前后废话。"""
    if not text:
        raise LLMError("模型返回为空")
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LLMError(f"模型未返回 JSON：{text[:200]}")
    return json.loads(text[start : end + 1])


class LLMClient:
    def __init__(self) -> None:
        self.base = config.LLM_BASE_URL
        self.key = config.LLM_API_KEY
        self.session = requests.Session()
        self.usage = {
            "calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_ms": 0,
        }
        self.trace: list[dict[str, Any]] = []

    # ------------------------------------------------------------------ 基础
    @property
    def configured(self) -> bool:
        return bool(self.key and self.base)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }

    def _post(self, payload: dict) -> dict:
        last_err = ""
        for attempt in range(config.LLM_MAX_RETRIES):
            try:
                with _RATE_LOCK:  # 串行 + 最小间隔，避免免费额度被打爆
                    wait = _MIN_INTERVAL - (time.time() - _LAST_CALL[0])
                    if wait > 0:
                        time.sleep(wait)
                    t0 = time.time()
                    resp = self.session.post(
                        f"{self.base}/chat/completions",
                        headers=self._headers(),
                        json=payload,
                        timeout=config.LLM_TIMEOUT,
                    )
                    _LAST_CALL[0] = time.time()
                elapsed = int((time.time() - t0) * 1000)
                if resp.status_code == 429:
                    last_err = f"HTTP 429: {resp.text[:200]}"
                    time.sleep(5.0 * (attempt + 1))
                    continue
                if resp.status_code in (500, 502, 503, 504):
                    last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    time.sleep(2.0 * (attempt + 1))
                    continue
                if resp.status_code != 200:
                    raise LLMError(f"HTTP {resp.status_code}: {resp.text[:400]}")
                data = resp.json()
                u = data.get("usage") or {}
                self.usage["calls"] += 1
                self.usage["prompt_tokens"] += int(u.get("prompt_tokens", 0) or 0)
                self.usage["completion_tokens"] += int(u.get("completion_tokens", 0) or 0)
                self.usage["total_ms"] += elapsed
                return data
            except requests.RequestException as exc:  # 网络层抖动
                last_err = f"{type(exc).__name__}: {exc}"
                time.sleep(1.2 * (attempt + 1))
        raise LLMError(f"大模型调用失败（已重试 {config.LLM_MAX_RETRIES} 次）：{last_err}")

    # -------------------------------------------------------------- 对话接口
    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        tools: list[dict] | None = None,
        tool_choice: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1200,
        json_mode: bool = False,
    ) -> dict:
        payload: dict[str, Any] = {
            "model": model or config.LLM_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice or "auto"
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            data = self._post(payload)
        except LLMError:
            if not json_mode:
                raise
            # 部分供应商不支持 response_format，降级重试
            payload.pop("response_format", None)
            data = self._post(payload)
        return data["choices"][0]["message"]

    def text(self, messages: list[dict], **kw) -> str:
        return (self.chat(messages, **kw).get("content") or "").strip()

    def json(self, messages: list[dict], **kw) -> dict:
        msg = self.chat(messages, json_mode=True, **kw)
        content = msg.get("content") or ""
        try:
            return _extract_json(content)
        except (LLMError, json.JSONDecodeError):
            # 再给一次机会：要求模型只输出 JSON
            fix = messages + [
                {"role": "assistant", "content": content},
                {"role": "user", "content": "上面的输出不是合法 JSON。请只输出一个合法 JSON 对象，不要任何解释、不要 Markdown 代码块。"},
            ]
            return _extract_json(self.text(fix, **kw))

    def vision(self, image_bytes: bytes, prompt: str, mime: str = "image/jpeg", **kw) -> str:
        b64 = base64.b64encode(image_bytes).decode()
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            }
        ]
        return self.text(messages, model=config.LLM_VISION_MODEL, **kw)

    def vision_json(self, image_bytes: bytes, prompt: str, mime: str = "image/jpeg", **kw) -> dict:
        b64 = base64.b64encode(image_bytes).decode()
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            }
        ]
        msg = self.chat(messages, model=config.LLM_VISION_MODEL, json_mode=True, **kw)
        return _extract_json(msg.get("content") or "")

    # ---------------------------------------------------------------- 成本估算
    def cost_report(self) -> dict:
        cost = (
            self.usage["prompt_tokens"] / 1e6 * config.PRICE_IN
            + self.usage["completion_tokens"] / 1e6 * config.PRICE_OUT
        )
        return {**self.usage, "cost_cny": round(cost, 6)}


llm = LLMClient()
