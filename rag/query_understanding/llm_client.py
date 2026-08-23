"""DashScope OpenAI 兼容 LLM 客户端。"""
from typing import Protocol

from openai import OpenAI


class StructuredLlmClient(Protocol):
    def complete_json(self, system_prompt: str, user_text: str) -> str: ...


class DashScopeLlmClient:
    def __init__(self, api_key: str, base_url: str, model: str, timeout: int):
        if not api_key:
            raise ValueError("未配置 DASHSCOPE_API_KEY")
        # DashScope 提供 OpenAI 兼容端点，便于未来替换其他模型供应商。
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        self.model = model

    def complete_json(self, system_prompt: str, user_text: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("LLM 返回内容为空")
        return content
