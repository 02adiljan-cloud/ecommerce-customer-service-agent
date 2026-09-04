"""创建接入 DeepSeek 和业务工具的 HelloAgents 实例。"""

from __future__ import annotations

from hello_agents import HelloAgentsLLM, SimpleAgent, ToolRegistry

from app.config import Settings
from app.prompts import SYSTEM_PROMPT
from app.tools.order_tool import OrderQueryTool
from app.tools.policy_rag_tool import PolicyRAGTool


def build_agent() -> SimpleAgent:
    settings = Settings.from_env()
    settings.validate_online()

    llm = HelloAgentsLLM(
        provider="deepseek",
        model=settings.llm_model_id,
        api_key=settings.deepseek_api_key,
        base_url=settings.llm_base_url,
        temperature=0.2,
        max_tokens=800,
        timeout=settings.llm_timeout,
    )

    registry = ToolRegistry()
    registry.register_tool(OrderQueryTool())
    registry.register_tool(PolicyRAGTool())

    return SimpleAgent(
        name="电商客服Agent",
        llm=llm,
        system_prompt=SYSTEM_PROMPT,
        tool_registry=registry,
        enable_tool_calling=True,
    )
