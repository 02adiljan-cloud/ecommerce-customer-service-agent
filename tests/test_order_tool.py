"""订单工具单元测试。"""

from __future__ import annotations

import json
import unittest

from app.tools.order_tool import OrderQueryTool


class OrderQueryToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = OrderQueryTool()

    def test_existing_order(self) -> None:
        result = json.loads(self.tool.run({"order_id": "ORD-202609-001"}))
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["status"], "已发货")
        self.assertEqual(result["data"]["tracking_number"], "SF1234567890")

    def test_missing_order(self) -> None:
        result = json.loads(self.tool.run({}))
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "MISSING_ORDER_ID")

    def test_invalid_order_id(self) -> None:
        result = json.loads(self.tool.run({"order_id": "1001"}))
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "INVALID_ORDER_ID")

    def test_unknown_order(self) -> None:
        result = json.loads(self.tool.run({"order_id": "ORD-202609-999"}))
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "ORDER_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
