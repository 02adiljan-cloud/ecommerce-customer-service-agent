"""售后政策 RAG 检索测试。"""

from __future__ import annotations

import json
import unittest

from app.rag import PolicyRetriever
from app.tools.policy_rag_tool import PolicyRAGTool


class PolicyRetrieverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.retriever = PolicyRetriever()

    def test_knowledge_base_stats(self) -> None:
        stats = self.retriever.stats()
        self.assertEqual(stats["namespace"], "fashion_after_sales")
        self.assertEqual(stats["document_count"], 7)
        self.assertGreaterEqual(stats["chunk_count"], 14)

    def test_return_policy_retrieval(self) -> None:
        results = self.retriever.search("七天无理由退货需要什么条件？")
        self.assertTrue(results)
        self.assertEqual(results[0].source, "return_policy.md")

    def test_quality_shipping_fee_retrieval(self) -> None:
        results = self.retriever.search("衣服开线属于质量问题，退货运费谁承担？")
        sources = {result.source for result in results}
        self.assertIn("quality_issue_policy.md", sources)
        self.assertIn("shipping_fee_policy.md", sources)

    def test_hybrid_order_wording_keeps_quality_policy(self) -> None:
        results = self.retriever.search(
            "订单 ORD-202609-004 的连衣裙收到时侧缝开线，退货运费谁承担？"
        )
        sources = {result.source for result in results}
        self.assertIn("quality_issue_policy.md", sources)
        self.assertIn("shipping_fee_policy.md", sources)

    def test_refund_timeline_retrieval(self) -> None:
        results = self.retriever.search("银行卡退款多久能够到账？")
        self.assertTrue(results)
        self.assertEqual(results[0].source, "refund_timeline.md")

    def test_irrelevant_query_has_no_results(self) -> None:
        results = self.retriever.search("量子纠缠实验装置")
        self.assertEqual(results, [])


class PolicyRAGToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = PolicyRAGTool()

    def test_tool_returns_citations(self) -> None:
        payload = json.loads(self.tool.run({"query": "质量问题退货运费谁承担"}))
        self.assertTrue(payload["success"])
        self.assertIn("shipping_fee_policy.md", payload["data"]["citations"])
        self.assertGreater(payload["data"]["retrieved_count"], 0)

    def test_missing_query(self) -> None:
        payload = json.loads(self.tool.run({}))
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error_code"], "MISSING_QUERY")
