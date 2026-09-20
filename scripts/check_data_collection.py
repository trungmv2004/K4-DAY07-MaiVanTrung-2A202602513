#!/usr/bin/env python3
"""Verify a data/<topic>/ corpus against the checklist in docs/DATA_COLLECTION.md (section 6).

Stdlib-only, mirrors the conservative style of fetch_public_pages.py. This does not
replace human judgement (e.g. "not sensitive data") but automates everything that can
be checked mechanically: file count, required metadata, sources.csv alignment, audience
diversity, and URL reachability.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REQUIRED_MD_FIELDS = ["doc_id", "title", "source_url", "retrieved_at", "document_version", "audience"]
SOURCES_FIELDS = ["doc_id", "file_path", "title", "source_url", "retrieved_at", "document_version", "license_or_permission"]
USER_AGENT = "Day7DataFoundationsCourse/1.0 (+educational-lab)"


def parse_front_matter(text: str) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        line = line.split(" #", 1)[0].rstrip()
        if not line.strip() or ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1]
        fields[key.strip()] = value
    return fields


def check_url(url: str, timeout: float = 15.0) -> tuple[bool, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            return True, f"HTTP {response.status}"
    except HTTPError as error:
        return False, f"HTTP {error.code}"
    except (URLError, TimeoutError, OSError) as error:
        return False, str(error)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/check_data_collection.py data/<topic>", file=sys.stderr)
        return 2
    topic_dir = Path(sys.argv[1])
    if not topic_dir.is_dir():
        print(f"Not a directory: {topic_dir}", file=sys.stderr)
        return 2

    ok = True

    def report(passed: bool, message: str) -> None:
        nonlocal ok
        ok = ok and passed
        print(f"[{'OK' if passed else 'FAIL'}] {message}")

    md_files = sorted(p for p in topic_dir.glob("*.md"))
    sources_path = topic_dir / "sources.csv"

    print("== 1. So luong file & doc_id duy nhat ==")
    report(5 <= len(md_files) <= 10, f"So file .md = {len(md_files)} (yeu cau 5-10)")

    docs: dict[str, dict[str, str]] = {}
    doc_ids_seen: dict[str, Path] = {}
    for path in md_files:
        fm = parse_front_matter(path.read_text(encoding="utf-8"))
        docs[path.name] = fm
        doc_id = fm.get("doc_id", "")
        if not doc_id:
            report(False, f"{path.name}: khong doc duoc doc_id tu front matter")
            continue
        if doc_id in doc_ids_seen:
            report(False, f"doc_id trung lap: '{doc_id}' o ca {doc_ids_seen[doc_id].name} va {path.name}")
        else:
            doc_ids_seen[doc_id] = path
        report(doc_id == path.stem, f"{path.name}: doc_id ('{doc_id}') {'khop' if doc_id == path.stem else 'KHONG khop'} ten file")

    print("\n== 2. Metadata bat buoc & doi chieu sources.csv ==")
    sources_rows: dict[str, dict[str, str]] = {}
    if not sources_path.is_file():
        report(False, f"Khong tim thay {sources_path}")
    else:
        with sources_path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            missing_header = [f for f in SOURCES_FIELDS if f not in (reader.fieldnames or [])]
            report(not missing_header, f"sources.csv header {'day du' if not missing_header else 'THIEU: ' + ', '.join(missing_header)}")
            for row_num, row in enumerate(reader, start=2):
                doc_id = (row.get("doc_id") or "").strip()
                if not doc_id:
                    report(False, f"sources.csv dong {row_num}: doc_id rong")
                    continue
                if doc_id in sources_rows:
                    report(False, f"sources.csv: doc_id trung lap '{doc_id}' (dong {row_num})")
                sources_rows[doc_id] = row
                blank_fields = [f for f in SOURCES_FIELDS if not (row.get(f) or "").strip() and f != "file_path"]
                report(not blank_fields, f"sources.csv '{doc_id}': {'moi truong day du' if not blank_fields else 'thieu ' + ', '.join(blank_fields)}")

    for name, fm in docs.items():
        missing = [f for f in REQUIRED_MD_FIELDS if not fm.get(f, "").strip()]
        report(not missing, f"{name}: front matter {'day du 6 truong bat buoc' if not missing else 'THIEU ' + ', '.join(missing)}")
        doc_id = fm.get("doc_id", "")
        if doc_id and doc_id not in sources_rows:
            report(False, f"{name}: doc_id '{doc_id}' KHONG co trong sources.csv")

    for doc_id in sources_rows:
        if doc_id not in doc_ids_seen:
            report(False, f"sources.csv: doc_id '{doc_id}' khong khop file .md nao trong thu muc")

    report(len(sources_rows) == len(md_files), f"sources.csv co {len(sources_rows)} dong, thu muc co {len(md_files)} file .md (can khop 1-1)")

    print("\n== 3. Da dang audience ==")
    audiences = {fm.get("audience", "").strip() for fm in docs.values() if fm.get("audience", "").strip()}
    print(f"  Cac gia tri audience tim thay: {sorted(audiences)}")
    report(len(audiences) >= 2, f"So gia tri audience khac nhau = {len(audiences)} (yeu cau >= 2)")

    print("\n== 4. URL nguon co truy cap duoc khong (khong tu dong kiem duoc du lieu nhay cam - can nguoi kiem tra) ==")
    checked_urls: set[str] = set()
    for name, fm in docs.items():
        url = fm.get("source_url", "").strip()
        if not url or url in checked_urls:
            continue
        checked_urls.add(url)
        reachable, detail = check_url(url)
        report(reachable, f"{url} -> {detail}")

    print("\n== 5. 5 cau hoi benchmark (khong the tu dong kiem, can doi chieu thu cong voi report/REPORT_NHOM.md) ==")
    nhom_path = Path("report/REPORT_NHOM.md")
    if nhom_path.is_file():
        text = nhom_path.read_text(encoding="utf-8")
        table_match = re.search(r"### Câu hỏi đánh giá.*?\n(.*?)\n---", text, re.S)
        filled_rows = 0
        if table_match:
            for line in table_match.group(1).splitlines():
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) >= 3 and cells[0].isdigit() and cells[1] and cells[2]:
                    filled_rows += 1
        print(f"  [INFO] report/REPORT_NHOM.md: {filled_rows}/5 dong cau hoi da dien (Cau hoi + Gold Answer).")
        print("  [INFO] Muc nay luon can nguoi kiem tra thu cong: xac nhan tung gold answer trich duoc tu corpus,")
        print("         va it nhat 1 cau can metadata_filter={'audience': 'buyer'|'seller'} moi dung.")
    else:
        print(f"  [INFO] Khong tim thay {nhom_path} de doi chieu.")

    print("\n" + ("TAT CA MUC TU DONG KIEM DUOC: OK" if ok else "CO MUC FAIL - xem chi tiet o tren"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
