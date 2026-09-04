"""电商客服 Agent 命令行入口。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

from app.agent_factory import build_agent
from app.tools.order_tool import OrderQueryTool
from app.tools.policy_rag_tool import PolicyRAGTool


ORDER_ID_PATTERN = re.compile(r"ORD-\d{6}-\d{3}", re.IGNORECASE)
POLICY_HINT_PATTERN = re.compile(
    r"退货|换货|退款|质量|破洞|开线|污渍|运费|邮费|尺码|身高|体重|洗护|洗涤|促销|优惠|折扣"
)


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


def _format_offline_policy_result(payload: dict[str, Any]) -> str:
    """将政策检索结果格式化为可核验的离线输出。"""
    if not payload.get("success"):
        return payload.get("message", "政策检索失败。")

    results = payload["data"]["results"]
    lines = ["检索到以下售后政策片段："]
    for result in results:
        lines.append(
            f"- {result['content']}（来源：{result['source']}，"
            f"score={result['score']}）"
        )
    return "\n".join(lines)


def run_offline_query(query: str) -> str:
    """无需 API Key 的工具与检索自检，不代表真实 LLM 决策。"""
    match = ORDER_ID_PATTERN.search(query)
    outputs: list[str] = []
    if match:
        order_tool = OrderQueryTool()
        raw_order_result = order_tool.run({"order_id": match.group(0).upper()})
        outputs.append(_format_offline_order_result(json.loads(raw_order_result)))

    if POLICY_HINT_PATTERN.search(query):
        policy_tool = PolicyRAGTool()
        raw_policy_result = policy_tool.run({"query": query, "top_k": 3})
        outputs.append(_format_offline_policy_result(json.loads(raw_policy_result)))

    if outputs:
        return "\n\n".join(outputs)
    return (
        "离线模式目前支持订单号查询和售后政策检索。"
        "订单号示例：ORD-202609-001。"
    )


def run_online_query(agent: Any, query: str) -> str:
    """运行真实 Agent，为连续工具调用保留足够迭代并拒绝空响应。"""
    response = agent.run(query, max_tool_iterations=5)
    if not response or not response.strip():
        raise RuntimeError("Agent 返回了空响应，请重试本次请求。")
    return response


def interactive(offline: bool) -> None:
    """启动命令行多轮交互。"""
    print("电商客服 Agent 已启动，输入 exit 退出。")
    if offline:
        print("当前为离线自检模式：验证订单工具和政策检索，不调用大模型。")
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

        response = run_offline_query(user_input) if offline else run_online_query(agent, user_input)
        print(f"客服：{response}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="电商客服 Agent 命令行程序")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="不调用 DeepSeek，仅验证订单工具和政策检索",
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
                agent = build_agent()
                print(run_online_query(agent, args.query))
            return

        interactive(args.offline)
    except RuntimeError as exc:
        print(f"配置错误：{exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
