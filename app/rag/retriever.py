"""面向中文售后政策的轻量 BM25 检索器。

该模块负责 RAG 的 Retrieval 阶段：加载知识目录、切分 Markdown、建立
内存索引并返回带来源的候选片段。生成阶段由 DeepSeek 完成。
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KB_DIR = PROJECT_ROOT / "knowledge_base"
DEFAULT_CATALOG = DEFAULT_KB_DIR / "catalog.json"

ASCII_WORD_PATTERN = re.compile(r"[a-z0-9]+")
CHINESE_SEQUENCE_PATTERN = re.compile(r"[\u4e00-\u9fff]+")
MARKDOWN_PREFIX_PATTERN = re.compile(r"^\s{0,3}(?:#+|[-*>])\s*")

QUERY_EXPANSIONS = {
    "退钱": "退款 到账",
    "返钱": "退款 到账",
    "邮费": "运费",
    "快递费": "运费",
    "瑕疵": "质量问题 破洞 开线 污渍",
    "破损": "质量问题 破洞 开线",
    "大小": "尺码",
    "换码": "尺码 换货",
    "折扣": "促销 优惠",
    "清洗": "洗护 洗涤",
}

CATEGORY_HINTS = {
    "退换货": ("退货", "换货", "七天无理由", "吊牌", "二次销售"),
    "质量售后": ("质量", "破洞", "开线", "拉链", "污渍", "瑕疵", "破损"),
    "售后运费": ("运费", "邮费", "快递费", "运费险", "谁承担"),
    "退款": ("退款", "退钱", "返钱", "到账", "工作日"),
    "促销售后": ("促销", "优惠", "满减", "折扣", "赠品"),
    "商品尺码": ("尺码", "大小", "身高", "体重", "肩宽", "胸围", "腰围"),
    "商品洗护": ("洗护", "清洗", "洗涤", "水洗", "干洗", "烘干"),
}


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    source: str
    document_id: str
    title: str
    category: str
    version: str
    effective_date: str
    content: str
    search_text: str


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: str
    source: str
    document_id: str
    title: str
    category: str
    version: str
    effective_date: str
    score: float
    content: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "source": self.source,
            "document_id": self.document_id,
            "title": self.title,
            "category": self.category,
            "version": self.version,
            "effective_date": self.effective_date,
            "score": round(self.score, 4),
            "content": self.content,
        }


class PolicyRetriever:
    """加载知识库并使用中文字符 n-gram BM25 进行检索。"""

    def __init__(
        self,
        knowledge_base_dir: Path | None = None,
        catalog_path: Path | None = None,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.knowledge_base_dir = (knowledge_base_dir or DEFAULT_KB_DIR).resolve()
        self.catalog_path = (catalog_path or DEFAULT_CATALOG).resolve()
        self.k1 = k1
        self.b = b
        self.namespace = "fashion_after_sales"
        self.schema_version = "unknown"
        self.chunks = self._load_chunks()
        self._tokenized_documents = [self._tokenize(chunk.search_text) for chunk in self.chunks]
        self._term_frequencies = [Counter(tokens) for tokens in self._tokenized_documents]
        self._document_lengths = [len(tokens) for tokens in self._tokenized_documents]
        self._average_document_length = (
            sum(self._document_lengths) / len(self._document_lengths)
            if self._document_lengths
            else 0.0
        )
        self._inverse_document_frequency = self._build_inverse_document_frequency()

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        normalized = MARKDOWN_PREFIX_PATTERN.sub("", text.lower())
        tokens = ASCII_WORD_PATTERN.findall(normalized)
        for sequence in CHINESE_SEQUENCE_PATTERN.findall(normalized):
            if len(sequence) == 1:
                tokens.append(sequence)
                continue
            tokens.extend(sequence[index : index + 2] for index in range(len(sequence) - 1))
            if len(sequence) >= 3:
                tokens.extend(sequence[index : index + 3] for index in range(len(sequence) - 2))
        return tokens

    @staticmethod
    def _expand_query(query: str) -> str:
        additions = [expansion for phrase, expansion in QUERY_EXPANSIONS.items() if phrase in query]
        return " ".join([query, *additions])

    @staticmethod
    def _paragraphs(markdown: str) -> list[str]:
        useful_lines: list[str] = []
        for line in markdown.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("# "):
                useful_lines.append("")
                continue
            if stripped.startswith(("- 文档编号：", "- 政策编号：", "- 生效日期：")):
                continue
            useful_lines.append(stripped)

        body = "\n".join(useful_lines).strip()
        return [paragraph.strip() for paragraph in re.split(r"\n\s*\n", body) if paragraph.strip()]

    def _safe_document_path(self, source: str) -> Path:
        candidate = (self.knowledge_base_dir / source).resolve()
        try:
            candidate.relative_to(self.knowledge_base_dir)
        except ValueError as exc:
            raise ValueError(f"知识文件路径越界：{source}") from exc
        return candidate

    def _load_chunks(self) -> list[KnowledgeChunk]:
        with self.catalog_path.open("r", encoding="utf-8") as catalog_file:
            catalog = json.load(catalog_file)

        self.namespace = str(catalog.get("namespace", "fashion_after_sales"))
        self.schema_version = str(catalog.get("schema_version", "unknown"))
        documents = catalog.get("documents")
        if not isinstance(documents, list) or not documents:
            raise ValueError("知识目录 catalog.json 中没有 documents。")

        chunks: list[KnowledgeChunk] = []
        for document in documents:
            source = str(document["source"])
            document_path = self._safe_document_path(source)
            markdown = document_path.read_text(encoding="utf-8")
            paragraphs = self._paragraphs(markdown)
            keywords = " ".join(str(keyword) for keyword in document.get("keywords", []))
            for index, paragraph in enumerate(paragraphs, start=1):
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=f"{document['document_id']}#chunk-{index}",
                        source=source,
                        document_id=str(document["document_id"]),
                        title=str(document["title"]),
                        category=str(document["category"]),
                        version=str(document["version"]),
                        effective_date=str(document["effective_date"]),
                        content=paragraph,
                        search_text=" ".join(
                            [
                                str(document["title"]),
                                str(document["title"]),
                                str(document["category"]),
                                keywords,
                                paragraph,
                            ]
                        ),
                    )
                )
        return chunks

    def _build_inverse_document_frequency(self) -> dict[str, float]:
        document_count = len(self._tokenized_documents)
        document_frequency: Counter[str] = Counter()
        for tokens in self._tokenized_documents:
            document_frequency.update(set(tokens))
        return {
            term: math.log(1 + (document_count - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    def _bm25_score(self, query_tokens: set[str], document_index: int) -> float:
        frequencies = self._term_frequencies[document_index]
        document_length = self._document_lengths[document_index]
        if not frequencies or not self._average_document_length:
            return 0.0

        score = 0.0
        for term in query_tokens:
            frequency = frequencies.get(term, 0)
            if not frequency:
                continue
            denominator = frequency + self.k1 * (
                1 - self.b + self.b * document_length / self._average_document_length
            )
            score += self._inverse_document_frequency.get(term, 0.0) * (
                frequency * (self.k1 + 1) / denominator
            )
        return score

    def search(self, query: str, top_k: int = 3) -> list[RetrievalResult]:
        query = str(query).strip()
        if not query:
            return []

        query_tokens = set(self._tokenize(self._expand_query(query)))
        ranked: list[RetrievalResult] = []
        for index, chunk in enumerate(self.chunks):
            score = self._bm25_score(query_tokens, index)
            matched_hints = sum(
                1
                for hint in CATEGORY_HINTS.get(chunk.category, ())
                if hint in query
            )
            score += matched_hints * 4.0
            if score <= 0:
                continue
            ranked.append(
                RetrievalResult(
                    chunk_id=chunk.chunk_id,
                    source=chunk.source,
                    document_id=chunk.document_id,
                    title=chunk.title,
                    category=chunk.category,
                    version=chunk.version,
                    effective_date=chunk.effective_date,
                    score=score,
                    content=chunk.content,
                )
            )

        ranked.sort(key=lambda item: (-item.score, item.source, item.chunk_id))
        result_limit = max(1, min(int(top_k), 5))
        selected: list[RetrievalResult] = []
        source_counts: Counter[str] = Counter()

        detected_categories = {
            category
            for category, hints in CATEGORY_HINTS.items()
            if any(hint in query for hint in hints)
        }
        best_by_category: dict[str, RetrievalResult] = {}
        for result in ranked:
            if result.category in detected_categories and result.category not in best_by_category:
                best_by_category[result.category] = result
        for result in sorted(best_by_category.values(), key=lambda item: -item.score):
            selected.append(result)
            source_counts[result.source] += 1
            if len(selected) == result_limit:
                return selected

        for result in ranked:
            if any(item.chunk_id == result.chunk_id for item in selected):
                continue
            if source_counts[result.source] >= 2:
                continue
            selected.append(result)
            source_counts[result.source] += 1
            if len(selected) == result_limit:
                break
        return selected

    def stats(self) -> dict[str, Any]:
        return {
            "namespace": self.namespace,
            "schema_version": self.schema_version,
            "document_count": len({chunk.source for chunk in self.chunks}),
            "chunk_count": len(self.chunks),
            "retrieval_method": "bm25_zh_char_ngram",
        }
