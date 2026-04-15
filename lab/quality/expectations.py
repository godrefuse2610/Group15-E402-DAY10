"""
Expectation suite đơn giản (không bắt buộc Great Expectations).

Sinh viên có thể thay bằng GE / pydantic / custom — miễn là có halt có kiểm soát.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class ExpectationResult:
    name: str
    passed: bool
    severity: str  # "warn" | "halt"
    detail: str


def run_expectations(cleaned_rows: List[Dict[str, Any]]) -> Tuple[List[ExpectationResult], bool]:
    """
    Trả về (results, should_halt).

    should_halt = True nếu có bất kỳ expectation severity halt nào fail.
    """
    results: List[ExpectationResult] = []

    # E1: có ít nhất 1 dòng sau clean
    ok = len(cleaned_rows) >= 1
    results.append(
        ExpectationResult(
            "min_one_row",
            ok,
            "halt",
            f"cleaned_rows={len(cleaned_rows)}",
        )
    )

    # E2: không doc_id rỗng
    bad_doc = [r for r in cleaned_rows if not (r.get("doc_id") or "").strip()]
    ok2 = len(bad_doc) == 0
    results.append(
        ExpectationResult(
            "no_empty_doc_id",
            ok2,
            "halt",
            f"empty_doc_id_count={len(bad_doc)}",
        )
    )

    # E3: policy refund không được chứa cửa sổ sai 14 ngày (sau khi đã fix)
    bad_refund = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "policy_refund_v4"
        and "14 ngày làm việc" in (r.get("chunk_text") or "")
    ]
    ok3 = len(bad_refund) == 0
    results.append(
        ExpectationResult(
            "refund_no_stale_14d_window",
            ok3,
            "halt",
            f"violations={len(bad_refund)}",
        )
    )

    # E4: chunk_text đủ dài
    short = [r for r in cleaned_rows if len((r.get("chunk_text") or "")) < 8]
    ok4 = len(short) == 0
    results.append(
        ExpectationResult(
            "chunk_min_length_8",
            ok4,
            "warn",
            f"short_chunks={len(short)}",
        )
    )

    # E5: effective_date đúng định dạng ISO sau clean (phát hiện parser lỏng)
    iso_bad = [
        r
        for r in cleaned_rows
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", (r.get("effective_date") or "").strip())
    ]
    ok5 = len(iso_bad) == 0
    results.append(
        ExpectationResult(
            "effective_date_iso_yyyy_mm_dd",
            ok5,
            "halt",
            f"non_iso_rows={len(iso_bad)}",
        )
    )

    # E6: không còn marker phép năm cũ 10 ngày trên doc HR (conflict version sau clean)
    bad_hr_annual = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "hr_leave_policy"
        and "10 ngày phép năm" in (r.get("chunk_text") or "")
    ]
    ok6 = len(bad_hr_annual) == 0
    results.append(
        ExpectationResult(
            "hr_leave_no_stale_10d_annual",
            ok6,
            "halt",
            f"violations={len(bad_hr_annual)}",
        )
    )

    # E7 (mới — Sprint 2): Không có ký tự vô hình (BOM, zero-width) trong chunk_text đã clean.
    # severity=halt: nếu R7 bỏ sót, expectation này bắt lại trước khi embed → vector store không bị nhiễm.
    # metric_impact: inject dòng BOM-prefix + --skip-validate → E7 FAIL;
    #               sau khi rule R7 chạy → E7 PASS; delta rõ ràng qua log expectation.
    _INVISIBLE_PATTERN = re.compile(r"[\ufeff\u200b\u200c\u200d\u00ad]")
    bad_invisible = [
        r
        for r in cleaned_rows
        if _INVISIBLE_PATTERN.search(r.get("chunk_text") or "")
    ]
    ok7 = len(bad_invisible) == 0
    results.append(
        ExpectationResult(
            "no_invisible_chars_in_chunk_text",
            ok7,
            "halt",
            f"chunks_with_invisible_chars={len(bad_invisible)}",
        )
    )

    # E8 (mới — Sprint 2): Độ đa dạng doc_id tối thiểu — ít nhất 3 doc_id khác nhau trong cleaned.
    # severity=warn: cảnh báo sớm khi pipeline vô tình loại bỏ quá nhiều nguồn dữ liệu.
    # metric_impact: inject xoá toàn bộ hr_leave_policy → distinct_doc_ids=3 (warn);
    #               pipeline chuẩn → distinct_doc_ids=4 (pass).
    distinct_docs = len({(r.get("doc_id") or "") for r in cleaned_rows if r.get("doc_id")})
    ok8 = distinct_docs >= 3
    results.append(
        ExpectationResult(
            "min_doc_id_diversity",
            ok8,
            "warn",
            f"distinct_doc_ids={distinct_docs} (min=3)",
        )
    )

    halt = any(not r.passed and r.severity == "halt" for r in results)
    return results, halt
