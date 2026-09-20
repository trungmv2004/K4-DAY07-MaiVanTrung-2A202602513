from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        results = self.store.search(question, top_k=top_k)
        if not results:
            return "Không tìm thấy thông tin liên quan trong cơ sở tri thức để trả lời câu hỏi này."

        numbered_context = "\n\n".join(
            f"[{i}] (nguồn: {result['metadata'].get('doc_id', result['id'])}) {result['content']}"
            for i, result in enumerate(results, start=1)
        )
        prompt = (
            "Trả lời câu hỏi chỉ dựa trên phần ngữ cảnh được đánh số bên dưới. "
            "Khi dùng thông tin từ đoạn nào, hãy trích dẫn số của đoạn đó (ví dụ [1]). "
            "Nếu ngữ cảnh không chứa câu trả lời, hãy nói rõ là không tìm thấy, không tự bịa thông tin.\n\n"
            f"Ngữ cảnh:\n{numbered_context}\n\nCâu hỏi: {question}\nTrả lời:"
        )
        return self.llm_fn(prompt)
