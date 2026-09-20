#!/usr/bin/env python3
"""
Benchmark tool for evaluating retrieval quality on ecommerce corpus.
Day 7 — Data Foundations: Embedding & Vector Store
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from dotenv import load_dotenv

from src.models import Document
from src.store import EmbeddingStore
from src.chunking import RecursiveChunker
from src.embeddings import (
    EMBEDDING_PROVIDER_ENV,
    GEMINI_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    GeminiEmbedder,
    LocalEmbedder,
    OpenAIEmbedder,
    _mock_embed,
)

# 5 Benchmark Queries & Gold Answers — đồng bộ với report/REPORT_NHOM.md mục 3.
# gold_doc: doc_id THẬT trong data/ecommerce/ (đối chiếu với sources.csv, KHÔNG bịa hậu tố).
# gold_snippet: chuỗi đặc trưng phải có mặt trong ngữ cảnh top-3 mới tính là "trả lời được" —
#               chỉ khớp đúng gold_doc là chưa đủ (dễ bị thổi phồng, xem cảnh báo trong lab doc mục 7).
BENCHMARK_QUERIES = [
    {
        "id": 1,
        "query": "Người mua có bao nhiêu ngày để gửi yêu cầu trả hàng/hoàn tiền kể từ khi đơn hàng giao thành công?",
        "filter": None,
        "gold_doc": [
            "quy-dinh-chung-tra-hang-hoan-tien",
            "chinh-sach-tra-hang-hoan-tien",
        ],
        "gold_snippet": "15 ngày",
        "gold_answer": "15 ngày kể từ lúc đơn hàng được cập nhật giao hàng thành công; riêng thực phẩm tươi sống và đông lạnh là 24 giờ.",
    },
    {
        "id": 2,
        "query": "Khi hệ thống ghi nhận đã trả hàng thành công nhưng Shop chưa nhận được hàng, Người Bán phải phản hồi Shopee trong bao lâu?",
        "filter": {"audience": "seller"},
        "gold_doc": ["quan-ly-don-tra-hang-hoan-tien-seller"],
        "gold_snippet": "2 ngày",
        "gold_answer": "Trong vòng 2 ngày, kể từ ngày hệ thống cập nhật trả hàng thành công.",
    },
    {
        "id": 3,
        "query": "Nếu người mua nhận hoàn tiền qua Ví ShopeePay, sau khi Shopee chấp nhận hoàn tiền thì mất bao lâu để nhận được tiền?",
        "filter": None,
        "gold_doc": ["thoi-gian-nhan-tien-hoan"],
        "gold_snippet": "24 giờ",
        "gold_answer": "24 giờ, với điều kiện Ví ShopeePay vẫn hoạt động bình thường.",
    },
    {
        "id": 4,
        "query": "Khi đóng gói hàng hoàn trả, người mua có được dán/viết thông tin trả hàng lên hộp của nhà sản xuất không?",
        "filter": None,
        "gold_doc": ["cach-dong-goi-hang-hoan-tra"],
        "gold_snippet": "hộp của nhà sản xuất",
        "gold_answer": "Không — không được dán/viết lên hộp của nhà sản xuất; cần dùng hộp vận chuyển bên ngoài để bảo vệ sản phẩm và hộp gốc.",
    },
    {
        "id": 5,
        "query": "Sau khi người mua gửi yêu cầu Trả hàng/Hoàn tiền, Shopee phản hồi kết quả xử lý trong khoảng thời gian nào?",
        "filter": None,
        "gold_doc": ["huong-dan-gui-yeu-cau-tra-hang"],
        "gold_snippet": "3 - 5 ngày",
        "gold_answer": "Khoảng 3-5 ngày làm việc.",
    },
]


def load_corpus(data_dir: Path) -> list[tuple[dict, str, str]]:
    """Đọc từng file .md, tách frontmatter metadata và nội dung thân bài."""
    documents = []
    for md_file in sorted(data_dir.glob("*.md")):
        raw_text = md_file.read_text(encoding="utf-8")
        parts = raw_text.split("---")
        if len(parts) >= 3:
            fm_raw = parts[1].strip()
            body = "---".join(parts[2:]).strip()
            meta = dict(re.findall(r"^(\w+):\s*(.+)$", fm_raw, re.M))
            meta = {k: v.strip(" \"'") for k, v in meta.items()}
        else:
            meta = {}
            body = raw_text.strip()

        meta.setdefault("doc_id", md_file.stem)
        documents.append((meta, body, md_file.stem))
    return documents


CACHE_PATH = Path(".embedding_cache.json")


class CachedRateLimitedEmbedder:
    """Wraps a real embedding backend with an on-disk content-hash cache and a
    rate limiter with retry/backoff — needed for the Gemini free tier (100
    requests/min): re-running bench.py on unchanged chunks costs zero extra
    calls, and transient 429s are retried instead of crashing the whole run.
    """

    def __init__(self, embedder, model_name: str, min_interval: float = 0.7) -> None:
        self._embedder = embedder
        self._model_name = model_name
        self._backend_name = f"{model_name} (cached, rate-limited)"
        self._min_interval = min_interval
        self._last_call = 0.0
        self._cache: dict[str, list[float]] = {}
        if CACHE_PATH.exists():
            try:
                self._cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            except Exception:
                self._cache = {}

    def _key(self, text: str) -> str:
        digest = hashlib.md5(text.encode("utf-8")).hexdigest()
        return f"{self._model_name}:{digest}"

    def __call__(self, text: str) -> list[float]:
        key = self._key(text)
        if key in self._cache:
            return self._cache[key]

        wait = self._min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)

        for attempt in range(5):
            try:
                vector = self._embedder(text)
                break
            except Exception as error:
                if attempt == 4:
                    raise
                print(f"  [embedder retry {attempt + 1}/4] {error}")
                time.sleep(25.0)
        self._last_call = time.monotonic()

        self._cache[key] = vector
        CACHE_PATH.write_text(json.dumps(self._cache), encoding="utf-8")
        return vector


def get_embedder():
    """Lấy embedding model cấu hình từ file .env"""
    load_dotenv(override=False)
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()
    if provider == "local":
        try:
            return LocalEmbedder(
                model_name=os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL)
            )
        except Exception:
            return _mock_embed
    elif provider == "openai":
        try:
            model_name = os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL)
            return CachedRateLimitedEmbedder(OpenAIEmbedder(model_name=model_name), model_name)
        except Exception:
            return _mock_embed
    elif provider == "gemini":
        try:
            model_name = os.getenv("GEMINI_EMBEDDING_MODEL", GEMINI_EMBEDDING_MODEL)
            return CachedRateLimitedEmbedder(GeminiEmbedder(model_name=model_name), model_name)
        except Exception:
            return _mock_embed
    return _mock_embed


def run_benchmark(chunker=None, data_dir_str: str = "data/ecommerce") -> str:
    data_dir = Path(data_dir_str)
    if not data_dir.exists():
        return f"Error: Data directory '{data_dir}' not found."

    # Chiến lược của tôi: RecursiveChunker (chunk_size=400, khớp số liệu đã dẫn trong
    # report/REPORT_CANHAN.md và REPORT_NHOM.md).
    if chunker is None:
        chunker = RecursiveChunker(chunk_size=400)

    chunker_name = chunker.__class__.__name__
    raw_docs = load_corpus(data_dir)

    all_chunks: list[Document] = []
    for meta, body, file_stem in raw_docs:
        chunks = chunker.chunk(body)
        for i, chunk_text in enumerate(chunks):
            chunk_id = f"{file_stem}#{i}"
            chunk_meta = {**meta, "doc_id": file_stem, "chunk_index": i}
            all_chunks.append(
                Document(id=chunk_id, content=chunk_text, metadata=chunk_meta)
            )

    embedder = get_embedder()
    embedder_name = getattr(embedder, "_backend_name", embedder.__class__.__name__)

    store = EmbeddingStore(collection_name="benchmark_store", embedding_fn=embedder)
    store.add_documents(all_chunks)

    output_lines = []
    output_lines.append("=" * 70)
    output_lines.append(f"BENCHMARK RETRIEVAL REPORT — DAY 7 LAB")
    output_lines.append("=" * 70)
    output_lines.append(f"Chiến lược Chunking  : {chunker_name}")
    output_lines.append(f"Embedding Backend    : {embedder_name}")
    output_lines.append(f"Tổng số tài liệu gốc : {len(raw_docs)} files")
    output_lines.append(f"Tổng số chunks nạp   : {store.get_collection_size()} chunks")
    output_lines.append("-" * 70)

    naive_hits = 0
    real_hits = 0

    for q in BENCHMARK_QUERIES:
        q_id = q["id"]
        query = q["query"]
        q_filter = q["filter"]
        gold_docs = q["gold_doc"]
        gold_snippet = q["gold_snippet"]
        gold_ans = q["gold_answer"]

        output_lines.append(f"\n[QUERY {q_id}] {query}")
        if q_filter:
            output_lines.append(f"  * Metadata filter  : {q_filter}")
        output_lines.append(f"  * Gold Doc ID      : {gold_docs}")
        output_lines.append(f"  * Gold Answer      : {gold_ans}")

        results = store.search_with_filter(query, top_k=3, metadata_filter=q_filter)
        output_lines.append("  * Top-3 Retrieved Chunks:")

        found_doc = False
        for rank, res in enumerate(results, start=1):
            doc_id = res.get("metadata", {}).get("doc_id", "unknown")
            score = res.get("score", 0.0)
            preview = res["content"][:140].replace("\n", " ").strip()
            is_gold = doc_id in gold_docs
            if is_gold:
                found_doc = True
            tag = "[MATCH]" if is_gold else "       "
            output_lines.append(
                f"    {rank}. {tag} score={score:+.4f} | doc={doc_id} | id={res['id']}"
            )
            output_lines.append(f'       preview: "{preview}..."')

        # Chấm hai mức (theo docs/SCORING.md, tránh cách chấm ngây thơ chỉ dựa vào doc_id):
        # (a) top-3 có đúng file gold không; (b) ngữ cảnh top-3 có THỰC SỰ chứa chuỗi đáp án không.
        combined_context = " ".join(r["content"] for r in results)
        found_snippet = gold_snippet in combined_context
        naive_hits += found_doc
        real_hits += found_snippet

        output_lines.append(
            f"  => Đúng file gold trong top-3       : {'CO' if found_doc else 'KHONG'} (cach cham ngay tho)"
        )
        output_lines.append(
            f"  => Ngu canh top-3 chua dap an ('{gold_snippet}') : {'CO' if found_snippet else 'KHONG'} (cach cham dung theo docs/SCORING.md)"
        )

    output_lines.append("\n" + "=" * 70)
    output_lines.append(
        f"TONG KET: {naive_hits}/5 dung doc_id (cach cham ngay tho, de bi thoi phong)"
    )
    output_lines.append(
        f"TONG KET: {real_hits}/5 THUC SU chua dap an trong ngu canh (cach cham dung)"
    )

    report_text = "\n".join(output_lines)
    print(report_text)

    # Lưu kết quả ra file ket_qua_benchmark.txt
    Path("ket_qua_benchmark.txt").write_text(report_text, encoding="utf-8")
    return report_text


if __name__ == "__main__":
    # Chiến lược cá nhân của tôi (Mai Văn Trung): RecursiveChunker + embedder thật (Gemini, xem .env).
    # Các chiến lược khác của nhóm (FixedSizeChunker — Giáp, HeadingChunker — Trí) chạy trên bench.py
    # riêng của từng người, không chạy chung trong file này để tránh ghi đè ket_qua_benchmark.txt.
    run_benchmark(chunker=RecursiveChunker(chunk_size=400))
