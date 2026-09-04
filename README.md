# 电商客服Agent

基于 Datawhale Hello-Agents 教程设计的服装电商客服智能体。当前 V0.2 已完成 DeepSeek 接入、订单查询工具、售后政策 RAG、模拟业务数据和离线评测。

## 当前能力

- 使用 HelloAgents `SimpleAgent` 和 `ToolRegistry`；
- 通过 DeepSeek 判断是否调用订单工具；
- 根据订单号查询结构化订单数据；
- 使用中文 BM25 对 Markdown 售后政策进行 Top-K 检索；
- RAG 结果携带文档编号、版本、生效日期、片段和来源引用；
- 支持订单事实与售后政策的连续工具调用；
- 处理缺少订单号、格式错误、订单不存在和数据源异常；
- 提供无需 API Key 的订单与 RAG 离线自检；
- 为商品、物流、Embedding、Rerank 和人工转接预留模块边界。

## 技术路线

```text
用户 -> SimpleAgent -> DeepSeek -> ToolRegistry -> get_order -> orders.json
                                     |
                                     -> search_policy -> BM25 -> Markdown政策
                                     |
                                     -> 后续：商品 / 物流 / Rerank / 人工工单
```

项目采用 Hello-Agents 教程中介绍的“LLM + 工具 + 观察结果 + 再决策”模式。RAG 将检索与生成分离：本地检索器只返回可信政策片段，DeepSeek 负责组织带引用的客服回复。当前锁定 `hello-agents==0.2.9`，该版本导入评测模块时还需要显式安装 `huggingface_hub`。

## 环境要求

- Python 3.10+
- Git
- DeepSeek API Key（真实 Agent 模式需要）

## Windows 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `.env`，填写自己的 API Key：

```dotenv
DEEPSEEK_API_KEY=你的API_Key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL_ID=deepseek-v4-flash
LLM_TIMEOUT=60
```

不要把 `.env` 提交到 GitHub。

## 先运行离线自检

```powershell
python main.py --offline --query "帮我查询订单 ORD-202609-001"
```

预期结果：

```text
订单 ORD-202609-001 查询成功：宽松纯棉白色衬衫，尺码 L，金额 ¥199，当前状态为“已发货”。
```

离线验证 RAG 检索和来源：

```powershell
python main.py --offline --query "质量问题退货运费谁承担？"
```

## 运行真实 Agent

配置 `.env` 后执行：

```powershell
python main.py --query "帮我查询订单 ORD-202609-001"
```

政策 RAG：

```powershell
python main.py --query "七天无理由退货需要满足什么条件？"
```

订单与政策联合调用：

```powershell
python main.py --query "订单 ORD-202609-004 的连衣裙收到时侧缝开线，退货运费谁承担？"
```

进入多轮命令行模式：

```powershell
python main.py
```

## 运行测试

```powershell
python -m unittest discover -s tests -v
```

## 模拟数据

- `data/products.json`：8 件服装商品；
- `data/orders.json`：8 个不同状态的订单；
- `data/logistics.json`：5 条物流记录；
- `knowledge_base/`：退货、质量问题、运费、尺码、洗护、促销和退款到账知识。
- `knowledge_base/catalog.json`：知识文档 ID、分类、版本、生效日期、状态和关键词。

所有数据均为面试演示用虚构数据。

## 下一阶段

1. 接入商品查询和物流查询工具；
2. 将 BM25 升级为 BGE Embedding + Qdrant，并保留本地回退；
3. 增加混合检索和可选 Rerank；
4. 实现低置信度转人工与 Reflection；
5. 建立任务成功率、工具调用正确率、RAG 检索指标和延迟评测；
6. 添加 Streamlit 演示界面。

## 作者

- GitHub：[@02adiljan-cloud](https://github.com/02adiljan-cloud)
- 项目方向：AI 项目管理 / Agent / RAG

## 参考

- [Datawhale Hello-Agents](https://github.com/datawhalechina/hello-agents)
- [Hello-Agents 第四章：智能体经典范式](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter4/%E7%AC%AC%E5%9B%9B%E7%AB%A0%20%E6%99%BA%E8%83%BD%E4%BD%93%E7%BB%8F%E5%85%B8%E8%8C%83%E5%BC%8F%E6%9E%84%E5%BB%BA.md)
- [Hello-Agents 第八章：记忆与检索](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter8/%E7%AC%AC%E5%85%AB%E7%AB%A0%20%E8%AE%B0%E5%BF%86%E4%B8%8E%E6%A3%80%E7%B4%A2.md)
- [DeepSeek API 文档](https://api-docs.deepseek.com/)
