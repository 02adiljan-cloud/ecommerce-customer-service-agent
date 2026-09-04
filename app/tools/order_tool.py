"""订单查询工具。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from hello_agents.tools import Tool, ToolParameter


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ORDER_DATA = PROJECT_ROOT / "data" / "orders.json"
ORDER_ID_PATTERN = re.compile(r"^ORD-\d{6}-\d{3}$")


class OrderQueryTool(Tool):
    """根据订单号查询本地模拟订单数据。"""

    def __init__(self, data_path: Path | None = None) -> None:
        super().__init__(
            name="get_order",
            description=(
                "根据完整订单号查询服装订单。用户询问订单状态、购买商品、"
                "尺码、金额或物流单号时使用。参数 order_id 必须类似 ORD-202609-001。"
            ),
        )
        self.data_path = data_path or DEFAULT_ORDER_DATA

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="order_id",
                type="string",
                description="完整订单号，例如 ORD-202609-001",
                required=True,
            )
        ]

    def _load_orders(self) -> list[dict[str, Any]]:
        with self.data_path.open("r", encoding="utf-8") as data_file:
            data = json.load(data_file)
        if not isinstance(data, list):
            raise ValueError("订单数据格式错误：顶层必须是数组。")
        return data

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
        raw_order_id = parameters.get("order_id")
        if raw_order_id is None:
            return self._result(False, "请提供订单号。", error_code="MISSING_ORDER_ID")

        order_id = str(raw_order_id).strip().upper()
        if not ORDER_ID_PATTERN.fullmatch(order_id):
            return self._result(
                False,
                "订单号格式不正确，请使用 ORD-YYYYMM-NNN 格式。",
                error_code="INVALID_ORDER_ID",
            )

        try:
            orders = self._load_orders()
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return self._result(
                False,
                f"订单数据暂时无法读取：{exc}",
                error_code="DATA_SOURCE_ERROR",
            )

        for order in orders:
            if order.get("order_id", "").upper() == order_id:
                return self._result(True, "订单查询成功。", data=order)

        return self._result(
            False,
            f"未找到订单 {order_id}，请核对订单号。",
            error_code="ORDER_NOT_FOUND",
        )
