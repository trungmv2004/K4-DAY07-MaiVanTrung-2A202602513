# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Mai Văn Trung
**Nhóm:** 6h50
**Ngày:** 20/09/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Giá trị cosine similarity gần 1 nghĩa là hai vector embedding gần như cùng hướng trong không gian nhiều chiều, tức hai đoạn văn bản mang nội dung/ý nghĩa gần giống nhau, bất kể độ dài văn bản khác nhau thế nào.

**Ví dụ có độ tương tự CAO:**
- Câu A: "Người mua có thể yêu cầu trả hàng trong 15 ngày."
- Câu B: "Thời hạn trả hàng là 15 ngày kể từ khi nhận hàng."
- Tại sao tương đồng: hai câu diễn đạt lại (paraphrase) cùng một sự kiện — mốc thời gian 15 ngày để yêu cầu trả hàng — chỉ khác cách hành văn, nên một mô hình embedding ngữ nghĩa tốt sẽ cho điểm cosine rất cao.

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Cách đóng gói hàng hoàn trả an toàn."
- Câu B: "Con mèo đang ngủ trên ghế sofa."
- Tại sao khác: hai câu không liên quan chủ đề (chính sách thương mại điện tử vs. sinh hoạt đời thường), không chia sẻ khái niệm ngữ nghĩa nào nên vector embedding sẽ gần như trực giao hoặc ngược hướng.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine similarity chỉ quan tâm đến *hướng* của vector chứ không phụ thuộc vào độ lớn (magnitude), trong khi độ lớn của embedding có thể bị ảnh hưởng bởi độ dài văn bản; nhờ vậy cosine phản ánh đúng mức độ tương đồng ngữ nghĩa hơn Euclidean distance, vốn nhạy cảm với sự chênh lệch độ lớn giữa hai vector.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:* step = chunk_size − overlap = 500 − 50 = 450. Số chunk = ⌈(10000 − 500) / 450⌉ + 1 = ⌈21.11⌉ + 1 = 22 + 1 = 23.
> *Đáp án:* **23 chunks** — đã kiểm chứng lại bằng cách chạy trực tiếp `FixedSizeChunker(chunk_size=500, overlap=50).chunk(text)` trên chuỗi 10.000 ký tự, kết quả thực tế đúng bằng 23.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Overlap tăng lên 100 → step giảm còn 400 → số chunk tăng lên **25** (đã chạy lại code để kiểm chứng). Overlap lớn hơn giúp giảm rủi ro một thông tin/câu quan trọng bị cắt đúng ngay ranh giới giữa hai chunk (mất ngữ cảnh), đổi lại phải trả giá bằng việc lưu trữ và tính embedding nhiều hơn do dữ liệu bị lặp lại giữa các chunk liền kề.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Dùng `re.split(r"\. |! |\? |\.\n", text)` để tách câu theo đúng 4 kiểu dấu phân cách nêu trong docstring, sau đó `strip()` từng câu và loại câu rỗng. Các câu được nhóm lại theo từng cụm `max_sentences_per_chunk` câu rồi nối lại bằng dấu cách. Trường hợp biên: văn bản rỗng trả về `[]` ngay từ đầu; nếu số câu không chia hết cho `max_sentences_per_chunk`, cụm cuối cùng đơn giản chứa ít câu hơn (dùng slicing nên không lỗi index).

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> `_split` thử tách văn bản theo separator ưu tiên cao nhất (`\n\n` → `\n` → `. ` → `" "` → `""`); các phần nhỏ được gộp dần lại (giống thuật toán "greedy merge") cho tới khi gần chạm `chunk_size` thì chốt thành một chunk. Nếu một phần vẫn dài hơn `chunk_size` sau khi tách, hàm gọi đệ quy `_split` cho phần đó với các separator còn lại. **Base case**: khi `len(current_text) <= chunk_size` thì trả về `[current_text]` ngay (không tách thêm); nếu hết separator mà văn bản vẫn dài, cắt cứng theo `chunk_size` ký tự (fallback an toàn, đảm bảo luôn trả về list không rỗng kể cả khi `separators=[]`).

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> `_make_record` chuẩn hoá mỗi `Document` thành một dict gồm `id`, `content`, `metadata` (tự thêm `doc_id` mặc định bằng `doc.id` nếu chưa có, phục vụ `delete_document` sau này) và `embedding` tính bằng `embedding_fn`. `add_documents` lặp qua từng doc, gọi `_make_record` rồi append vào `self._store` (đường in-memory, dùng khi không có ChromaDB). `search` nhúng câu truy vấn rồi gọi `_search_records`, hàm này tính độ tương tự bằng tích vô hướng (`_dot`) giữa vector truy vấn và từng embedding đã lưu — vì `MockEmbedder` đã chuẩn hoá vector về độ dài 1 nên tích vô hướng ở đây tương đương cosine similarity — sau đó sắp xếp giảm dần theo `score` và cắt lấy `top_k`.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> Lọc metadata **trước**: nếu có `metadata_filter`, duyệt `self._store` giữ lại các record mà mọi cặp key-value trong filter khớp với `record["metadata"]`, rồi mới chạy `_search_records` trên tập đã lọc — cách này đảm bảo `top_k` luôn được tính trên đúng tập ứng viên hợp lệ thay vì lọc sau khi đã có top-k (dễ làm thiếu kết quả). Nếu không truyền filter thì gọi thẳng `search()` để hai hàm luôn nhất quán. `delete_document` lọc bỏ mọi record có `metadata["doc_id"] == doc_id` khỏi `self._store`, so sánh kích thước trước/sau để trả về `True`/`False`.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> `__init__` chỉ lưu tham chiếu tới `store` và `llm_fn`. `answer` gọi `store.search(question, top_k)` để lấy các chunk liên quan, nối nội dung các chunk lại bằng `"\n\n"` thành phần **Ngữ cảnh**, rồi dựng một prompt có cấu trúc rõ ràng: hướng dẫn chỉ trả lời dựa trên ngữ cảnh (tránh mô hình bịa thông tin ngoài corpus), chèn phần Ngữ cảnh, rồi tới Câu hỏi và nhãn "Trả lời:" để mô hình sinh tiếp. Prompt cuối cùng được truyền cho `llm_fn` và trả kết quả nguyên văn.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: H:\AI2026\chatAI\K4-DAY07-MaiVanTrung-2A202602513
collecting ... collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED

============================= 42 passed in 0.04s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | "Người mua có thể yêu cầu trả hàng trong 15 ngày." | "Thời hạn trả hàng là 15 ngày kể từ khi nhận hàng." | cao | -0.1210 | Sai |
| 2 | "Chính sách đổi trả và hoàn tiền của Shopee." | "Quy định trả hàng hoàn tiền trên nền tảng Shopee." | cao | -0.0323 | Sai |
| 3 | "Người mua có thể yêu cầu trả hàng trong 15 ngày." | "Hôm nay trời Hà Nội nắng đẹp." | thấp | 0.1173 | Sai (điểm không âm mạnh như kỳ vọng) |
| 4 | "Cách đóng gói hàng hoàn trả an toàn." | "Con mèo đang ngủ trên ghế sofa." | thấp | 0.1644 | Sai (điểm còn dương, cao hơn cả cặp 1–2 vốn nên tương đồng) |
| 5 | "Shopee hoàn tiền qua Ví ShopeePay trong 24 giờ." | "Người bán cần phản hồi Shopee trong vòng 2 ngày." | trung bình (cùng chủ đề, khác chi tiết) | -0.0292 | Gần đúng |

*(Điểm thực tế tính bằng `compute_similarity(_mock_embed(a), _mock_embed(b))` — `_mock_embed` là `MockEmbedder`, backend embedding mặc định của lab, dùng cho mọi checkpoint bắt buộc.)*

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Bất ngờ nhất là cặp 1 và 2: hai câu gần như diễn đạt lại cùng một ý (paraphrase) nhưng điểm cosine lại âm nhẹ, còn cặp 4 (hai câu hoàn toàn không liên quan) lại có điểm dương cao nhất trong cả 5 cặp. Điều này cho thấy dự đoán của tôi dựa trên trực giác ngữ nghĩa của con người hoàn toàn không khớp với `_mock_embed`, vì đây chỉ là embedding giả lập tạo từ hash MD5 của toàn bộ chuỗi ký tự — nó không "hiểu" nghĩa mà chỉ sinh vector giả ngẫu nhiên (nhưng tất định) từ nội dung thô. Bài học rút ra: chất lượng truy xuất theo ngữ nghĩa phụ thuộc hoàn toàn vào embedder — muốn điểm số phản ánh đúng trực giác con người (như dự đoán ở bảng trên), bắt buộc phải dùng một embedder thật sự học ngữ nghĩa (ví dụ `LocalEmbedder` với mô hình multilingual), chứ mock embedder chỉ phù hợp để kiểm thử hạ tầng code, không dùng để đánh giá chất lượng truy xuất thực tế.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

> **Thiết lập của tôi:** nạp 6 file trong `data/ecommerce/`, chia nhỏ phần nội dung (bỏ front matter) bằng `RecursiveChunker(chunk_size=400)` → 143 chunk, nạp vào `EmbeddingStore`. Câu 2 chạy qua `search_with_filter(metadata_filter={"audience": "seller"})`, các câu còn lại chạy `search()` không lọc, `top_k=3`. Kết quả tái lập được bằng `python bench.py` (`EMBEDDING_PROVIDER=gemini` trong `.env`), output đầy đủ đã lưu tại `ket_qua_benchmark.txt`.
>
> **Cập nhật quan trọng:** ban đầu tôi chạy bằng `_mock_embed` (mặc định, không cần API key) và chỉ đúng **1/5** câu theo cách chấm đúng nội dung. Sau khi bật embedder thật (`GeminiEmbedder`, model `gemini-embedding-001`), kết quả tăng vọt lên **5/5** — với **cùng một corpus, cùng một chiến lược chunking, cùng 5 câu hỏi**, chỉ đổi embedder. Đây là bằng chứng trực tiếp, rõ ràng nhất trong cả bài lab: retrieval quality phụ thuộc vào embedder chứ không phải chunking. Bảng dưới đây là kết quả với Gemini (bảng so sánh mock trước đó lưu trong lịch sử `ket_qua_benchmark.txt` / mục 4).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) |
|---|-------|--------------------------------|-------|-----------|
| 1 | Thời hạn gửi yêu cầu trả hàng/hoàn tiền là bao nhiêu ngày? | `quy-dinh-chung-tra-hang-hoan-tien` — "Đối với các đơn hàng khác: 15 ngày kể từ lúc đơn hàng được cập nhật trạng thái 'Giao hàng thành công'" | 0.8432 | **Có** — đúng chunk vàng, đúng mốc 15 ngày |
| 2 | Người Bán phản hồi trong bao lâu khi chưa nhận được hàng hoàn? (**cần `metadata_filter={"audience":"seller"}`**) | `quan-ly-don-tra-hang-hoan-tien-seller` — đúng mục "C. Hướng dẫn Phản hồi... Hạn phản hồi... Trong vòng 2 ngày" | 0.8724 | **Có** — đúng chunk vàng |
| 3 | Hoàn tiền qua Ví ShopeePay mất bao lâu? | `thoi-gian-nhan-tien-hoan` — đúng tài liệu, top-3 cùng chứa mốc "24 giờ" | 0.8386 | **Có** — đúng tài liệu, đáp án nằm trong top-3 |
| 4 | Đóng gói hàng hoàn trả — có được viết lên hộp nhà sản xuất không? | `cach-dong-goi-hang-hoan-tra` — "Bạn cần sử dụng hộp vận chuyển bên ngoài để đảm bảo sản phẩm và hộp của nhà sản xuất không bị hư hại." | 0.7915 | **Có** — đúng chunk vàng |
| 5 | Shopee phản hồi kết quả xử lý trong bao lâu? | `huong-dan-gui-yeu-cau-tra-hang` — "Yêu cầu của bạn thường được xử lý trong khoảng 3 - 5 ngày làm việc." | 0.8860 | **Có** — đúng chunk vàng, khớp chính xác |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 5 / 5 (với Gemini) — so với 1 / 5 khi dùng `_mock_embed`.

**Nhận xét của tôi:** Với `_mock_embed`, chỉ câu 2 (câu bắt buộc dùng `metadata_filter`) trả lời đúng, vì lọc theo `audience` thu hẹp candidate pool đủ nhỏ để bù đắp cho embedding không mang ngữ nghĩa. Với `GeminiEmbedder`, **cả 5 câu đều đúng ngay cả khi không cần filter** (trừ câu 2 vẫn dùng filter theo đúng thiết kế benchmark của nhóm) — vector ngữ nghĩa thật đã tự nhiên phân biệt được nội dung liên quan mà không cần thu hẹp thủ công. Điều này khẳng định lại đúng bài học cốt lõi của lab: **chọn chiến lược chunking "đẹp" không cứu được một embedder yếu, nhưng một embedder tốt lại làm cho hầu hết chiến lược chunking hợp lý đều hoạt động tốt.** `metadata_filter` vẫn hữu ích (đảm bảo đúng đối tượng buyer/seller về mặt nghiệp vụ, không chỉ về mặt điểm số), nhưng với embedder thật nó không còn là "cứu cánh" duy nhất cho retrieval như khi dùng mock.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> *(Điền sau buổi so sánh nhóm — mỗi thành viên chạy chiến lược chunking/metadata khác nhau trên cùng corpus rồi so sánh kết quả.)*

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 10 / 10 |
| **Tổng phần cá nhân** | **60 / 60** |

*(Mục 5 đạt 5/5 câu sau khi bật `GeminiEmbedder` thật — xem so sánh mock vs. Gemini ở trên. Mục "Điều hay nhất học được từ nhóm" còn để trống, cần điền sau buổi demo so sánh nhóm.)*
