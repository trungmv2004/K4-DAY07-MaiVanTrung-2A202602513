# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** 6h50
**Thành viên:** Mai Văn Trung, Ngô Văn Giáp, Vũ Minh Trí, Trịnh Quốc Hoàng
**Ngày:** 20/09/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách đổi trả và hoàn tiền trên sàn thương mại điện tử Shopee (chủ đề bắt buộc của lớp K4-L3B).

**Tại sao nhóm chọn chủ đề này?**
> Đây là chủ đề bắt buộc theo `K4_VARIANT.md` cho lớp L3B. Nhóm chọn tập trung vào một sàn duy nhất (Shopee) thay vì trộn nhiều sàn, vì Shopee có Trung tâm trợ giúp công khai, cấu trúc rõ ràng, và tách biệt rõ nội dung dành cho Người Mua (`help.shopee.vn/portal/4`) với nội dung dành cho Người Bán (`help.shopee.vn/portal/1`) — điều kiện cần để cột `audience` có ý nghĩa lọc thật sự thay vì chỉ gắn nhãn cho có.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | `chinh-sach-tra-hang-hoan-tien.md` | help.shopee.vn/portal/4/article/77251 | 2026-09-20 / hiệu lực 2026-03-11 | 19.618 | audience: both · category: returns-policy |
| 2 | `quy-dinh-chung-tra-hang-hoan-tien.md` | help.shopee.vn/portal/4/article/188931 | 2026-09-20 / not-stated | 6.331 | audience: buyer · category: returns-policy |
| 3 | `thoi-gian-nhan-tien-hoan.md` | help.shopee.vn/portal/4/article/189473 | 2026-09-20 / not-stated | 3.900 | audience: buyer · category: refund-timeline |
| 4 | `quan-ly-don-tra-hang-hoan-tien-seller.md` | help.shopee.vn/portal/1/article/102521 | 2026-09-20 / not-stated | 3.863 | audience: seller · category: seller-operations |
| 5 | `cach-dong-goi-hang-hoan-tra.md` | help.shopee.vn/portal/4/article/79508 | 2026-09-20 / not-stated | 3.620 | audience: buyer · category: returns-process |
| 6 | `huong-dan-gui-yeu-cau-tra-hang.md` | help.shopee.vn/portal/4/article/79233 | 2026-09-20 / not-stated | 2.520 | audience: buyer · category: returns-process |

*(Số ký tự tính trên phần nội dung sau front matter; đối chiếu đầy đủ tại `data/ecommerce/sources.csv`, đã qua `scripts/check_data_collection.py` — mọi dòng OK.)*

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ — toàn bộ 6 tài liệu lấy từ Trung tâm trợ giúp công khai của Shopee, không cần đăng nhập, đã kiểm `robots.txt` cho phép.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata — `document_version` ghi `not-stated` cho các trang không nêu rõ, không bịa số hiệu.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `audience` | string (`buyer`/`seller`/`both`) | `seller` | Cho phép `search_with_filter({"audience": "seller"})` loại bỏ hẳn tài liệu dành cho người mua khi câu hỏi chỉ liên quan quy trình nội bộ của người bán — đây là trường bắt buộc theo `K4_VARIANT.md`. |
| `category` | string | `refund-timeline` | Gom nhóm tài liệu theo loại nội dung (chính sách gốc / hướng dẫn thao tác / mốc thời gian), hữu ích khi câu hỏi thuộc riêng một nhóm chủ đề. |
| `doc_id` | string | `thoi-gian-nhan-tien-hoan` | Định danh tài liệu gốc, dùng để `delete_document` và để đối chiếu "chunk nào thuộc file nào" khi đã bị chia nhỏ thành nhiều `Document`. |
| `document_version` | string (ngày hoặc `not-stated`) | `2026-03-11` | Cho biết tài liệu còn hiệu lực hay đã cũ, quan trọng với chính sách hay thay đổi như đổi trả/hoàn tiền. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` (chunk_size=400, đã bỏ front matter) trên 3 tài liệu đại diện — một tài liệu dài/gộp cả hai audience, một tài liệu ngắn seller, một tài liệu ngắn buyer:

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| `chinh-sach-tra-hang-hoan-tien.md` (19.618 ký tự) | FixedSizeChunker | 50 | 392.4 | Không — cắt cứng theo ký tự, có thể chia đôi ngay giữa câu/mục. |
| `chinh-sach-tra-hang-hoan-tien.md` | SentenceChunker | 43 | 450.6 | Trọn câu, nhưng nhiều câu luật rất dài (một điều khoản = một câu) nên chunk vẫn to và có thể gộp nhiều ý khác nhau. |
| `chinh-sach-tra-hang-hoan-tien.md` | RecursiveChunker | 80 | 243.3 | Tốt nhất về ranh giới — ưu tiên cắt theo đoạn/mục trước, nhưng vì văn bản có rất nhiều đoạn ngắn nên số chunk tăng và độ dài trung bình giảm so với 2 chiến lược kia. |
| `quan-ly-don-tra-hang-hoan-tien-seller.md` (3.863 ký tự) | FixedSizeChunker | 10 | 386.3 | Không |
| `quan-ly-don-tra-hang-hoan-tien-seller.md` | SentenceChunker | 5 | 767.8 | Trọn câu nhưng chunk quá to (một mục A/B/C dồn thành 1-2 câu rất dài trong bản thô) |
| `quan-ly-don-tra-hang-hoan-tien-seller.md` | RecursiveChunker | 11 | 349.4 | Tốt — bám theo từng mục A/B/C của hướng dẫn |
| `cach-dong-goi-hang-hoan-tra.md` (3.620 ký tự) | FixedSizeChunker | 10 | 362.0 | Không |
| `cach-dong-goi-hang-hoan-tra.md` | SentenceChunker | 7 | 505.1 | Trung bình |
| `cach-dong-goi-hang-hoan-tra.md` | RecursiveChunker | 11 | 327.3 | Tốt — bám theo từng bước hướng dẫn |

**Nhận xét chung:** `RecursiveChunker` luôn cho *nhiều chunk hơn nhưng ngắn hơn* hai chiến lược kia trên cả 3 tài liệu — vì nó ưu tiên dừng ở ranh giới đoạn/mục (`\n\n`, `\n`) thay vì cố lấp đầy `chunk_size`, nên các đoạn ngắn cuối mỗi mục không được gộp sang mục kế tiếp. Đây là đánh đổi: **mạch lạc ngữ nghĩa hơn nhưng phân mảnh hơn**.

### Chiến lược của từng thành viên

> Mỗi thành viên điền một khối dưới đây (copy thêm nếu nhóm có nhiều hơn 3 người).

> **Cập nhật (sau khi từng thành viên tự chạy `bench.py` với embedder thật):** ban đầu cả nhóm chạy trên `_mock_embed` để tiết kiệm thời gian setup (số liệu mock giữ lại bên dưới như một phát hiện phụ). Sau đó mỗi người tự bật embedder thật trên máy mình và gửi lại `ket_qua_benchmark.txt` thật: **Trung và Giáp dùng `GeminiEmbedder` (gemini-embedding-001)**, còn **Trí dùng `LocalEmbedder` (sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)** thay vì Gemini. Điều này có nghĩa so sánh Trung ↔ Giáp là công bằng (cùng embedder), nhưng so sánh với Trí bị **lẫn hai biến số** (vừa khác chunking vừa khác embedder) — nhóm ghi nhận đây là một hạn chế cần khắc phục ở vòng chạy tiếp theo (thống nhất một embedder chung trước khi so chunking). Ngoài ra, corpus Giáp chạy có **8 file** thay vì 6 file hiện tại của nhóm (dữ liệu cũ chưa đồng bộ) — cần Giáp `git pull` lại `data/ecommerce/` trước khi nộp bài, dù kết quả benchmark theo nội dung không đổi đáng kể.

**Thành viên 1 — Mai Văn Trung**
- **Loại chiến lược:** RecursiveChunker (`chunk_size=400`)
- **Mô tả & lý do chọn cho chủ đề này:** Corpus là văn bản chính sách có cấu trúc theo mục/điều khoản (`1.`, `2.1.`, `A.`, `B.`...), nên ưu tiên tách theo ranh giới đoạn (`\n\n`, `\n`) trước khi hạ xuống cấp câu/từ sẽ giữ được trọn vẹn từng điều khoản thay vì cắt cứng giữa chừng như FixedSize. Xem chi tiết chạy thật trong `bench.py` / `ket_qua_benchmark.txt`.
- **Code snippet (nếu custom):** không dùng custom, dùng thẳng `RecursiveChunker` có sẵn trong `src/chunking.py`.
- **Kết quả (Gemini, tự chạy `bench.py`):** 143 chunk trên 6 tài liệu; điểm nội dung thật **5/5** (naive theo doc_id cũng 5/5).

**Thành viên 2 — Ngô Văn Giáp** *(vai R3 gợi ý)*
- **Loại chiến lược:** `FixedSizeChunker(chunk_size=400, overlap=50)`
- **Mô tả & lý do chọn cho chủ đề này:** Chiến lược cơ sở, cắt cứng theo số ký tự với overlap để giảm rủi ro mất thông tin ở ranh giới chunk; dùng làm đối trọng so sánh với hai chiến lược "thông minh" hơn (Recursive, Heading).
- **Code snippet (nếu custom):** không custom, dùng `FixedSizeChunker` có sẵn.
- **Kết quả (Gemini, `ket_qua_benchmark-giap.txt` — Giáp tự chạy):** 119 chunk trên **8 tài liệu** (corpus của Giáp có 2 file cũ chưa đồng bộ với 6 file chính thức — cần `git pull`); điểm nội dung thật **3/5** (câu 4: đúng chủ đề nhưng chunk cắt mất đúng đoạn nêu "hộp của nhà sản xuất"; câu 5: sai hẳn tài liệu — top-1 trả về `quy-dinh-chung-tra-hang-hoan-tien` thay vì `huong-dan-gui-yeu-cau-tra-hang`). Điểm doc_id ngây thơ hiển thị 0/5 trong file gốc do lỗi định dạng — `doc_id` trong bản chạy của Giáp bị dính thêm hậu tố chunk (`quy-dinh-chung-tra-hang-hoan-tien#3` thay vì `quy-dinh-chung-tra-hang-hoan-tien`), Giáp cần sửa lại `load_corpus`/`_make_record` để `doc_id` chỉ giữ tên file gốc.

**Thành viên 3 — Vũ Minh Trí** *(vai bắt buộc theo K4_VARIANT.md: chunk theo heading/mục)*
- **Loại chiến lược:** `HeadingChunker` tự viết — tách văn bản tại các dòng heading dạng số/chữ cái (`1.`, `1.1.`, `A.`, `B.`...), gắn lại tiêu đề vào từng mảnh con nếu section quá dài phải cắt tiếp bằng `RecursiveChunker`.
- **Mô tả & lý do chọn cho chủ đề này:** Văn bản chính sách Shopee được biên soạn theo điều khoản/mục rõ ràng, mỗi mục là một đơn vị ngữ nghĩa Shopee đã chia sẵn — chunk theo heading tận dụng đúng cấu trúc đó thay vì đoán lại bằng ký tự/câu.
- **Code snippet (nếu custom):**
```python
HEADING_RE = re.compile(r"^\s{0,3}(?:\d{1,2}(?:\.\d{1,2})*\.?\s+\S|[A-EĐ]\.\s+\S)")

class HeadingChunker:
    def __init__(self, chunk_size=400):
        self.chunk_size = chunk_size
        self._fallback = RecursiveChunker(chunk_size=chunk_size)

    def chunk(self, text):
        lines = text.split("\n")
        sections, heading, buf = [], "", []
        for line in lines:
            if HEADING_RE.match(line.strip()) and line.strip():
                if buf:
                    sections.append((heading, "\n".join(buf).strip()))
                heading, buf = line.strip(), []
            else:
                buf.append(line)
        if buf:
            sections.append((heading, "\n".join(buf).strip()))
        chunks = []
        for h, body in sections:
            full = f"{h}\n{body}".strip() if h else body
            if not full:
                continue
            if len(full) <= self.chunk_size:
                chunks.append(full)
            else:
                for piece in self._fallback.chunk(body):
                    chunks.append(f"{h}\n{piece}".strip() if h else piece)
        return chunks
```
- **Kết quả (`ket_qua_benchmark-tri.txt` — Trí tự chạy):** 138 chunk trên 6 tài liệu — **dùng `LocalEmbedder` (sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2), không phải Gemini** như Trung/Giáp; điểm nội dung thật **3/5** (câu 4: đúng file nhưng KHÔNG đúng đoạn chứa "hộp của nhà sản xuất"; câu 5: sai hẳn tài liệu — top-1 trả về `chinh-sach-tra-hang-hoan-tien` thay vì `huong-dan-gui-yeu-cau-tra-hang`), điểm doc_id ngây thơ 4/5. *(Vì dùng embedder khác, kết quả này không so sánh trực tiếp 1:1 được với Trung/Giáp — xem ghi chú đầu mục 2.)*

**Thành viên 4 — Trịnh Quốc Hoàng** *(Report & Demo Lead — theo gợi ý nhóm 4 người của lab doc)*
- **Vai trò:** Không cần chạy thêm một chiến lược chunking khác biệt; chịu trách nhiệm gom kết quả cả nhóm vào `REPORT_NHOM.md`, chuẩn bị và dẫn phần thuyết trình (mục 4, CP7).

### So Sánh Giữa Các Thành Viên

> Cột điểm dùng thang **1đ/câu × 5 câu = /5**, quy đổi tương đối sang **/10** (nhân 2), tính theo cách chấm đúng nội dung (chuỗi đáp án có thật trong top-3), không dùng cách chấm ngây thơ theo doc_id. **Trung và Giáp dùng cùng embedder (Gemini) nên so sánh công bằng; Trí dùng `LocalEmbedder` khác nên kết quả của Trí chỉ mang tính tham khảo, không dùng để kết luận "chiến lược nào thắng" một cách chặt chẽ.**

| Thành viên | Chiến lược (Strategy) | Embedder | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------|----------------------|-----------|----------|
| Mai Văn Trung | RecursiveChunker (400) | Gemini | **10/10** (5/5 câu đúng nội dung) | Giữ trọn mục/điều khoản, ranh giới chunk luôn khớp ý nghĩa | Nhiều chunk hơn (143), tốn thêm dung lượng lưu trữ/embedding so với FixedSize |
| Ngô Văn Giáp | FixedSizeChunker (400, overlap 50) | Gemini | 6/10 (3/5 câu đúng nội dung) | Đơn giản, ít chunk nhất (119), vẫn giữ đúng 3/5 câu dễ | Cắt cứng theo ký tự nên câu 4 bị đứt đúng đoạn chứa đáp án, câu 5 lạc hẳn sang tài liệu khác |
| Vũ Minh Trí | HeadingChunker (theo mục, 400) | LocalEmbedder (khác embedder) | 6/10 (3/5 câu đúng nội dung) | Giữ nguyên văn cả tiêu đề + nội dung mục, dễ đọc nhất trong 3 chiến lược | Cũng trượt câu 4 và câu 5 y như FixedSizeChunker, dù dùng embedder khác — nghi vấn 2 câu này khó với mọi chiến lược, không riêng gì FixedSize |
| Trịnh Quốc Hoàng | *(Report & Demo Lead — không chạy chiến lược riêng)* | — | — | — | — |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> Trong phép so sánh công bằng (cùng embedder Gemini): **RecursiveChunker (5/5) rõ ràng thắng FixedSizeChunker (3/5)** — cắt theo ranh giới đoạn/mục giữ được trọn câu chứa đáp án ở câu 4 và câu 5, còn cắt cứng theo ký tự làm đứt/loãng đúng những câu đó. Kết quả của Trí (HeadingChunker, 3/5) trùng khớp thất bại ở đúng 2 câu 4-5 giống FixedSize dù dùng embedder khác — điều này gợi ý rằng **câu 4 và câu 5 khó với mọi chiến lược trừ RecursiveChunker cụ thể của Trung**, nhưng nhóm chưa thể kết luận chắc chắn `HeadingChunker` tệ hơn `RecursiveChunker` vì hai kết quả này không cùng embedder — cần Trí chạy lại với Gemini để có phép so sánh sạch. Bài học quan trọng hơn cả thứ hạng: **giữ embedder cố định là điều kiện tiên quyết** để so sánh chunking cho có ý nghĩa; nhóm đã học được điều này *sau khi* phát hiện Trí dùng nhầm embedder, nên ghi lại đây làm lưu ý cho vòng benchmark tiếp theo.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Người mua có bao nhiêu ngày để gửi yêu cầu trả hàng/hoàn tiền kể từ khi đơn hàng giao thành công? | 15 ngày kể từ lúc đơn hàng được cập nhật giao hàng thành công; riêng thực phẩm tươi sống và đông lạnh là 24 giờ. | `quy-dinh-chung-tra-hang-hoan-tien.md` (mục 1.2) và `chinh-sach-tra-hang-hoan-tien.md` (mục 3.2) |
| 2 | Khi hệ thống ghi nhận đã trả hàng thành công nhưng Shop chưa nhận được hàng, Người Bán phải phản hồi Shopee trong bao lâu? | Trong vòng 2 ngày, kể từ ngày hệ thống cập nhật trả hàng thành công. | `quan-ly-don-tra-hang-hoan-tien-seller.md` (mục C) — **cần `metadata_filter={"audience": "seller"}`**, vì `chinh-sach-tra-hang-hoan-tien.md` cũng có mốc "02 ngày" nhưng cho tình huống khác (Người Bán khiếu nại quyết định hoàn tiền của Shopee), dễ bị lẫn nếu không lọc theo seller. |
| 3 | Nếu người mua nhận hoàn tiền qua Ví ShopeePay, sau khi Shopee chấp nhận hoàn tiền thì mất bao lâu để nhận được tiền? | 24 giờ, với điều kiện Ví ShopeePay vẫn hoạt động bình thường. | `thoi-gian-nhan-tien-hoan.md` (Bảng 1) |
| 4 | Khi đóng gói hàng hoàn trả, người mua có được dán/viết thông tin trả hàng lên hộp của nhà sản xuất không? | Không — không được dán/viết lên hộp của nhà sản xuất; cần dùng hộp vận chuyển bên ngoài để bảo vệ sản phẩm và hộp gốc. | `cach-dong-goi-hang-hoan-tra.md` |
| 5 | Sau khi người mua gửi yêu cầu Trả hàng/Hoàn tiền, Shopee phản hồi kết quả xử lý trong khoảng thời gian nào? | Khoảng 3–5 ngày làm việc. | `huong-dan-gui-yeu-cau-tra-hang.md` (mục 2 — Thời gian xử lý) |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

> Số liệu dưới đây là **kết quả thật** mỗi thành viên tự chạy và gửi lại (`ket_qua_benchmark.txt`, `ket_qua_benchmark-giap.txt`, `ket_qua_benchmark-tri.txt`): RecursiveChunker/Gemini — Trung; FixedSizeChunker/Gemini — Giáp; HeadingChunker/**LocalEmbedder** — Trí. Cột "Có chunk liên quan" kiểm ở **hai mức**: (a) top-3 có đúng file gold không, và (b) ngữ cảnh top-3 có thực sự **chứa chuỗi đáp án** không (cách chấm đúng theo `docs/SCORING.md`, tránh thổi phồng). *(Số liệu mock-embedder ban đầu — 0–1/5 cho cả 3 chiến lược — giữ trong lịch sử như phát hiện phụ về tầm quan trọng của embedder.)*

| # | Câu hỏi | Trung (Recursive/Gemini) | Giáp (FixedSize/Gemini) | Trí (Heading/Local) | Ghi chú |
|---|---------|:---:|:---:|:---:|---------|
| 1 | Thời hạn gửi yêu cầu (15 ngày) | CÓ | CÓ | CÓ | Cả 3 đều đúng — câu dễ nhất trong bộ 5 câu, không phân biệt được chiến lược/embedder. |
| 2 | Người Bán phản hồi trong 2 ngày (**cần `metadata_filter`**) | CÓ | CÓ | CÓ | Cả 3 đều đúng khi có filter `audience=seller` — xác nhận thiết kế filter của nhóm hoạt động tốt bất kể chiến lược/embedder. |
| 3 | Hoàn tiền Ví ShopeePay 24 giờ | CÓ | CÓ | CÓ | Cả 3 đều đúng. |
| 4 | Không viết lên hộp nhà sản xuất | CÓ | KHÔNG (đúng file, sai đoạn) | KHÔNG (đúng file, sai đoạn) | Chỉ `RecursiveChunker` của Trung giữ trọn câu chứa "hộp của nhà sản xuất"; cả FixedSize lẫn Heading (dù khác embedder) đều làm mất đúng câu này. |
| 5 | Shopee phản hồi 3-5 ngày | CÓ | KHÔNG (sai hẳn tài liệu) | KHÔNG (sai hẳn tài liệu) | Cả Giáp và Trí đều trả về nhầm tài liệu khác (`quy-dinh-chung-tra-hang-hoan-tien` / `chinh-sach-tra-hang-hoan-tien`) thay vì đúng `huong-dan-gui-yeu-cau-tra-hang`, dù khác nhau cả chunking lẫn embedder — dấu hiệu câu này khó chung, không phải lỗi riêng của một chiến lược. |

**Kết quả gộp theo chiến lược (cách chấm đúng theo nội dung):** RecursiveChunker+Gemini **5/5**, FixedSizeChunker+Gemini **3/5**, HeadingChunker+LocalEmbedder **3/5**. So với lúc dùng `_mock_embed` (0–1/5 cho cả 3), bật embedder thật nâng điểm rõ rệt cho mọi chiến lược, nhưng chỉ riêng `RecursiveChunker` của Trung đạt tuyệt đối — 2 câu khó nhất (4, 5) "đánh bại" cả 2 chiến lược còn lại bất kể chunking khác nhau (FixedSize) hay embedder khác nhau (Heading + Local).

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> Có — câu 2 là bằng chứng rõ nhất: cả 3 lần chạy thật (3 chiến lược, 2 embedder khác nhau) đều dùng `metadata_filter={"audience":"seller"}` và đều trả lời đúng. Với `_mock_embed` trước đó, câu 2 từng là câu **duy nhất** đúng trong cả 5 câu nhờ filter bù đắp cho embedding yếu; với embedder thật, filter vẫn giữ vai trò đảm bảo đúng đối tượng nghiệp vụ (không lẫn nội dung buyer/seller) dù bản thân retrieval ngữ nghĩa đã đủ mạnh để có thể đúng ngay cả khi thử bỏ filter (Trung đã kiểm tra riêng với `search()` không lọc trên Gemini và vẫn ra đúng kết quả — xem `REPORT_CANHAN.md` mục 5).

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Phân tích lỗi (failure case) — Mai Văn Trung:**
> **Câu hỏi hỏng:** Câu 5 — "Sau khi người mua gửi yêu cầu Trả hàng/Hoàn tiền, Shopee phản hồi kết quả xử lý trong khoảng thời gian nào?" — thất bại ở **cả `FixedSizeChunker`+Gemini (Giáp) lẫn `HeadingChunker`+LocalEmbedder (Trí)**, dù hai lần chạy này khác nhau cả về chunking lẫn embedder. **Vì sao:** cả hai đều trả về top-1 là một tài liệu khác (`quy-dinh-chung-tra-hang-hoan-tien` với Giáp, `chinh-sach-tra-hang-hoan-tien` với Trí) thay vì đúng tài liệu gold `huong-dan-gui-yeu-cau-tra-hang` — sai hẳn tài liệu chứ không chỉ sai đoạn. Nguyên nhân có thể không nằm ở một chiến lược cụ thể mà ở việc **3 tài liệu trong corpus đều có câu gần giống nhau về "3-5 ngày làm việc"** (`huong-dan-gui-yeu-cau-tra-hang`, `quy-dinh-chung-tra-hang-hoan-tien`, và gián tiếp trong `chinh-sach-tra-hang-hoan-tien`), nên với hầu hết chiến lược/embedder, các chunk này có vector rất gần nhau và dễ đảo thứ hạng. Chỉ `RecursiveChunker`+Gemini (Trung) trả lời đúng câu này. **Đề xuất sửa:** thêm một trường metadata phân biệt rõ hơn (ví dụ đánh dấu tài liệu nào là "hướng dẫn thao tác" so với "chính sách gốc") để có thể lọc thêm khi câu hỏi thiên về quy trình cụ thể; hoặc thử tăng `top_k` lên 5 để kiểm tra xem tài liệu đúng có nằm ngay dưới top-3 hay không, từ đó cân nhắc điều chỉnh ngưỡng.

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
1. **Embedder quan trọng hơn chunking, nhưng cả hai đều cần đúng.** Chuyển từ `_mock_embed` sang embedder thật (Gemini hoặc Local) nâng điểm từ 0–1/5 lên 3–5/5 tuỳ chiến lược — mức tăng lớn hơn nhiều so với khác biệt giữa các chiến lược chunking.
2. **Trong phép so sánh công bằng (cùng embedder Gemini), chunking vẫn tạo khác biệt rõ:** `RecursiveChunker` (5/5) thắng `FixedSizeChunker` (3/5) của cùng một embedder — cắt cứng theo ký tự làm mất đúng câu chứa đáp án ở 2/5 câu hỏi.
3. **Bài học ngoài kế hoạch:** một thành viên (Trí) vô tình chạy bằng embedder khác (`LocalEmbedder` thay vì Gemini) mà không ai phát hiện ra cho đến khi đọc kỹ file `ket_qua_benchmark.txt` — dòng "Embedding Backend" trong output. Đây là lời nhắc quan trọng: **luôn kiểm tra dòng backend trong output benchmark trước khi so sánh số liệu giữa các thành viên**, nếu không dễ so sánh nhầm hai kết quả không cùng điều kiện.
4. Cách chấm hai mức (doc_id vs. nội dung thật) vẫn quan trọng dù dùng embedder nào: với `FixedSizeChunker`+Gemini, cách chấm ngây thơ (sau khi sửa lỗi hiển thị doc_id của Giáp) sẽ là 3/5, trùng với cách chấm đúng — nhưng ở bản gốc Giáp gửi, lỗi định dạng `doc_id` khiến cách chấm ngây thơ báo sai thành 0/5, minh chứng thêm cho việc không nên tin số liệu tự động mà không đọc kỹ log.

**Bài học rút ra khi so sánh trong nhóm:**
> Thứ tự làm việc đúng là: **bật embedder thật trước, rồi mới so sánh chiến lược chunking — và phải đảm bảo cùng một embedder cho tất cả các lần so sánh.** Nhóm ban đầu so sánh trên `_mock_embed` và kết luận nhầm "chunking không tạo khác biệt"; sau khi đổi sang embedder thật thì phát hiện tiếp một vấn đề khác — không phải ai cũng dùng cùng một embedder thật, khiến kết quả của Trí (Heading) không thể so sánh sòng phẳng với Trung/Giáp. Bài học kép: (1) mock che mất khác biệt thật giữa các chiến lược, (2) ngay cả khi dùng embedder thật, phải thống nhất **cùng một** embedder mới so sánh được, nếu không sẽ lẫn hai biến số.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Thống nhất **một dòng lệnh `.env` chung** cho cả nhóm (ví dụ chốt `EMBEDDING_PROVIDER=gemini` cho mọi máy) trước khi ai bắt đầu chạy `bench.py`, thay vì để mỗi người tự chọn backend — đây là nguyên nhân trực tiếp khiến kết quả của Trí không so sánh được công bằng với Trung/Giáp lần này. Đồng bộ `data/ecommerce/` qua `git pull` trước khi benchmark (Giáp chạy nhầm bản 8 file cũ). Cũng nên bật embedder thật **ngay từ đầu buổi** thay vì để tới cuối, và dùng cơ chế cache theo hash nội dung (đã thêm vào `bench.py`) để tránh tốn quota Gemini free-tier khi chạy lại nhiều lần. Cuối cùng vẫn nên làm sạch kỹ phần rác giao diện ("Xin chào, Shopee có thể giúp gì cho bạn?"...) còn sót trong `.md` trước khi chunk.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10  |
| Thiết kế chiến lược (Strategy Design) | 13 / 15 *(3 chiến lược khác nhau và có số liệu thật từ cả 3 thành viên, nhưng Trí dùng embedder khác Trung/Giáp nên phép so sánh 3 chiều chưa hoàn toàn công bằng)* |
| Chất lượng truy xuất (Retrieval Quality) | 9 / 10 *(bảng kết quả thật 3 chiến lược × 5 câu, phân tích 2 mức chấm điểm, phát hiện và xử lý minh bạch vấn đề lệch embedder + lỗi hiển thị doc_id, 1 failure case cụ thể)* |
| Thuyết trình (Demo) | — *(chưa demo — Trịnh Quốc Hoàng phụ trách)* |
| **Tổng phần nhóm** | **32 / 40 (chờ buổi demo)** |
