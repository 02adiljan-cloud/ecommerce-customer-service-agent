"""售后政策 RAG 检索工具。"""

from __future__ import annotations

import json
from typing import Any

from hello_agents.tools import Tool, ToolParameter

from app.rag import PolicyRetriever


class PolicyRAGTool(Tool):
    """检索售后政策片段，生成由上层 Agent 负责。"""

    def __init__(self, retriever: PolicyRetriever | None = None) -> None:
        super().__init__(
            name="search_policy",
            description=(
                "检索服装电商售后政策和商品知识。用户询问退换货、质量问题、"
                "售后运费、退款到账、尺码、洗护或促销规则时必须使用。"
            ),
        )
        self.retriever = retriever or PolicyRetriever()

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="完整的用户政策问题，例如：质量问题退货运费谁承担",
                required=True,
            ),
            ToolParameter(
                name="top_k",
                type="integer",
                description="返回候选片段数量，默认 3，范围 1 到 5",
                required=False,
                default=3,
            ),
        ]

    @staticmethod
    def _result(
        success: bool,
        message: str,
        data: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> str:
        return json.dumps(
            {
                "success": success,
                "data": data,
                "error_code": error_code,
                "message": message,
            },
            ensure_ascii=False,
            indent=2,
        )

    def run(self, parameters: dict[str, Any]) -> str:
        query = str(parameters.get("query", "")).strip()
        if not query:
            return self._result(False, "请提供需要检索的政策问题。", error_code="MISSING_QUERY")

        try:
            top_k = max(1, min(int(parameters.get("top_k", 3)), 5))
        except (TypeError, ValueError):
            return self._result(False, "top_k 必须是 1 到 5 的整数。", error_code="INVALID_TOP_K")

        try:
            results = self.retriever.search(query, top_k=top_k)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return self._result(
                False,
                f"售后知识库暂时无法读取：{exc}",
                error_code="KNOWLEDGE_BASE_ERROR",
            )

        if not results:
            return self._result(
                False,
                "没有检索到足够相关的政策，请补充问题或转人工客服。",
                data={"query": query, **self.retriever.stats(), "results": []},
                error_code="NO_RELEVANT_POLICY",
            )

        result_items = [result.to_dict() for result in results]
        return self._result(
            True,
            "政策检索成功，请仅依据候选片段回答并标注来源。",
            data={
                "query": query,
                **self.retriever.stats(),
                "retrieved_count": len(result_items),
                "results": result_items,
                "citations": sorted({item["source"] for item in result_items}),
            },
        )
