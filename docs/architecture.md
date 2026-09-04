# 系统架构

## V0.2 运行链路

```text
用户输入
  -> HelloAgents SimpleAgent
  -> DeepSeek 判断需要哪些工具
  -> ToolRegistry
     -> get_order -> data/orders.json
     -> search_policy -> catalog.json + Markdown -> 中文 BM25 Top-K
  -> 结构化工具结果 / 带来源政策片段
  -> DeepSeek 生成客服回复
```

`--offline` 模式绕过模型，用于确定性验证订单工具和 RAG Retrieval，不计入真实 Agent 决策。

## 设计原则

1. Agent 负责理解问题、选择工具和组织回复。
2. 结构化事实由业务工具查询，非结构化规则由 RAG 检索，不让模型编造数据和政策。
3. RAG 将 Retrieval 与 Generation 分离，检索结果携带文档、版本、生效日期和片段编号。
4. 工具统一返回 `success`、`data`、`error_code` 和 `message`。
5. 模型、检索器、数据源、工具和提示词分离，便于将 BM25 替换为 BGE + Qdrant。
6. 涉及退款、取消订单等写操作时，后续增加确认、权限、幂等和审计机制。

## 迭代路线

- V0.2：已完成售后政策 RAG；下一步增加商品、物流工具。
- V0.3：Embedding、混合检索、Rerank、Reflection、人工转接。
- V0.4：Streamlit、评测报告、演示截图。
