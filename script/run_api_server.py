#!/usr/bin/env python3
"""HTTP API tối giản cho demo hỏi đáp RAG tại local."""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core.config import Settings, load_settings
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question

HOST = "127.0.0.1"
PORT = 8000


def _index_path(settings: Settings, collection_name: str) -> Path:
    paths = {
        settings.baseline_collection_name: settings.paths.embeddings_json,
        settings.corrupted_collection_name: settings.paths.corrupted_embeddings_json,
        settings.repaired_collection_name: settings.paths.repaired_embeddings_json,
    }
    if collection_name not in paths:
        raise ValueError(f"Collection không hợp lệ: {collection_name}")
    return paths[collection_name]


class RAGRuntime:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.cache: dict[str, tuple[LocalEmbeddingIndex, object]] = {}

    def get(self, collection_name: str) -> tuple[LocalEmbeddingIndex, object]:
        if collection_name not in self.cache:
            index = LocalEmbeddingIndex.load(self.settings, _index_path(self.settings, collection_name))
            # Cache index + agent: mỗi collection chỉ khởi tạo một lần.
            self.cache[collection_name] = (index, build_agent(self.settings, index))
        return self.cache[collection_name]


settings = load_settings(ROOT)
runtime = RAGRuntime(settings)


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "http://localhost:5173")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send(204, {})

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send(200, {"status": "ok", "message": "RAG API đang chạy"})
            return
        self._send(404, {"detail": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/query":
            self._send(404, {"detail": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length))
            question = str(request.get("question", "")).strip()
            collection_name = str(request.get("collection_name", "")).strip()
            if not question:
                raise ValueError("Câu hỏi không được để trống")
            index, agent = runtime.get(collection_name)
            retrieved = index.search(question, top_k=settings.top_k)
            # Chỉ gọi Gemini khi người dùng bấm Gửi. Nếu mạng/model chậm, trả lời
            # deterministic từ metadata sau 20 giây để buổi demo không bị treo.
            llm_pool = ThreadPoolExecutor(max_workers=1)
            llm_future = llm_pool.submit(run_agent_question, agent, question)
            try:
                answer = llm_future.result(timeout=20)
                answer_mode = f"{settings.llm_provider.upper()} + RAG"
            except TimeoutError:
                llm_future.cancel()
                answer = answer_question(question, settings, index).answer
                answer_mode = "RAG local fallback (model/network timeout)"
            except Exception:
                answer = answer_question(question, settings, index).answer
                answer_mode = "RAG local fallback (LLM unavailable)"
            finally:
                llm_pool.shutdown(wait=False, cancel_futures=True)
            self._send(200, {
                "answer": answer,
                "retrieved_docs": [item.paper_id for item in retrieved],
                "retrieved_titles": [item.title for item in retrieved],
                "collection_used": collection_name,
                "model": settings.model_name,
                "answer_mode": answer_mode,
            })
        except Exception as exc:
            self._send(500, {"detail": str(exc)})

    def log_message(self, format: str, *args: object) -> None:
        print(f"[RAG API] {format % args}")


if __name__ == "__main__":
    print(f"RAG API đang chạy tại http://{HOST}:{PORT}")
    print("Gemini chỉ được gọi khi frontend gửi câu hỏi.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
