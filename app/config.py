"""应用配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    deepseek_api_key: str
    llm_base_url: str
    llm_model_id: str
    llm_timeout: int

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(PROJECT_ROOT / ".env")
        return cls(
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
            llm_base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com").strip(),
            llm_model_id=os.getenv("LLM_MODEL_ID", "deepseek-v4-flash").strip(),
            llm_timeout=int(os.getenv("LLM_TIMEOUT", "60")),
        )

    def validate_online(self) -> None:
        if not self.deepseek_api_key or self.deepseek_api_key == "replace_with_your_key":
            raise RuntimeError(
                "尚未配置 DEEPSEEK_API_KEY。请把 .env.example 复制为 .env，"
                "填写本机 API Key；也可以先使用 --offline 验证工具骨架。"
            )
