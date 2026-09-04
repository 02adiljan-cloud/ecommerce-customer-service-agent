"""电商客服 Agent 命令行入口。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

from app.agent_factory import build_agent
from app.tools.order_tool import OrderQueryTool


ORDER_ID_PATTERN = re.compile(r"ORD-\d{6}-\d{3}", re.IGNORECASE)


def _configure_console_encoding() -> None:
    """让 Windows 终端稳定输出中文及货币符号。"""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def _format_offline_order_result(payload: dict[str, Any]) -> str:
    """将订单工具结果格式化为便于演示的自然语言。"""
    if not payload.get("success"):
        return payload.get("message", "订单查询失败。")

    order = payload["data"]
    return (
        f"订单 {order['order_id']} 查询成功：{order['product_name']}，"
        f"尺码 {order['size']}，金额 ¥{order['amount']}，"
        f"当前状态为“{order['status']}”。"
    )


def run_offline_query(query: str) -> str:
    """无需 API Key 的骨架自检，不代表真实 LLM 决策。"""
    match = ORDER_ID_PATTERN.search(query)
    if not match:
        return "请提供格式为 ORD-YYYYMM-NNN 的订单号，例如 ORD-202609-001。"

    tool = OrderQueryTool()
    raw_result = tool.run({"order_id": match.group(0).upper()})
    return _format_offline_order_result(json.loads(raw_result))


def interactive(offline: bool) -> None:
    """启动命令行多轮交互。"""
    print("电商客服 Agent 已启动，输入 exit 退出。")
    if offline:
        print("当前为离线骨架自检模式：仅验证订单工具，不调用大模型。")
        agent = None
    else:
        agent = build_agent()

    while True:
        user_input = input("\n用户：").strip()
        if user_input.lower() in {"exit", "quit"}:
            print("再见。")
            break
        if not user_input:
            continue

        response = run_offline_query(user_input) if offline else agent.run(user_input)
        print(f"客服：{response}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="电商客服 Agent 命令行程序")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="不调用 DeepSeek，仅验证订单查询骨架",
    )
    parser.add_argument(
        "--query",
        help="执行一条查询后退出，例如：帮我查询订单 ORD-202609-001",
    )
    return parser.parse_args()


def main() -> None:
    _configure_console_encoding()
    args = parse_args()

    try:
        if args.query:
            if args.offline:
                print(run_offline_query(args.query))
            else:
                print(build_agent().run(args.query))
            return

        interactive(args.offline)
    except RuntimeError as exc:
        print(f"配置错误：{exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
