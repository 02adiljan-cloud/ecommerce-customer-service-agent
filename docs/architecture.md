# 系统架构

## V0.1 运行链路

```text
用户输入
  -> HelloAgents SimpleAgent
  -> DeepSeek 判断是否需要工具
  -> ToolRegistry
  -> get_order
  -> data/orders.json
  -> 结构化工具结果
  -> DeepSeek 生成客服回复
```

`--offline` 模式绕过模型，仅用于验证订单号提取和订单工具，不计入真实 Agent 演示结果。

## 设计原则

1. Agent 负责理解问题、选择工具和组织回复。
2. 工具负责确定性的业务查询，不让模型编造订单数据。
3. 工具统一返回 `success`、`data`、`error_code` 和 `message`。
4. 模型、数据源、工具和提示词分离，便于独立替换和测试。
5. 涉及退款、取消订单等写操作时，后续增加确认、权限、幂等和审计机制。

## 迭代路线

- V0.2：商品、物流和售后政策 RAG。
- V0.3：连续工具调用、Reflection、人工转接。
- V0.4：Streamlit、评测报告、演示截图。
