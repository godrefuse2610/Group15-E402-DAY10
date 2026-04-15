"""
Cleaning rules — raw export → cleaned rows + quarantine.

Baseline gồm các failure mode mở rộng (allowlist doc_id, parse ngày, HR stale version).
Sinh viên thêm ≥3 rule mới: mỗi rule phải ghi `metric_impact` (xem README — chống trivial).

Rule mới (Sprint 2 — Group 15):
  R7  strip_invisible_unicode   : Xoá BOM + zero-width chars khỏi chunk_text.
  R8  quarantine_missing_exported_at : Quarantine row thiếu exported_at.
  R9  normalize_doc_id_case     : Lowercase + strip khoảng trắng doc_id trước allowlist check.
"""

from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Khớp export hợp lệ trong lab (mở rộng khi nhóm thêm doc mới — phải đồng bộ contract).
ALLOWED_DOC_IDS = frozenset(
    {
        "policy_refund_v4",
        "sla_p1_2026",
        "it_helpdesk_faq",
        "hr_leave_policy",
        "access_control_sop",
    }
)

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DMY_SLASH = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")

# R7: Các ký tự vô hình cần xoá khỏi văn bản (BOM, zero-width space, soft hyphen, NBSP)
_INVISIBLE_CHARS = re.compile(r"[\ufeff\u200b\u200c\u200d\u00ad\u00a0]+")


def _norm_text(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()


def _strip_invisible_unicode(s: str) -> str:
    """
    R7 — strip_invisible_unicode:
    Loại bỏ BOM (\\ufeff), zero-width space (\\u200b/\\u200c/\\u200d),
    soft-hyphen (\\u00ad) và non-breaking space (\\u00a0) khỏi chuỗi.
    metric_impact: inject dòng BOM-prefix cùng nội dung row 1 →
        trước rule: BOM khác key → bỏ qua dedupe → cleaned +1 (chunk lạ trong index);
        sau rule : BOM bị xoá → trùng key → quarantine +1, cleaned giữ nguyên.
    """
    return _INVISIBLE_CHARS.sub("", s or "")


def _stable_chunk_id(doc_id: str, chunk_text: str, seq: int) -> str:
    h = hashlib.sha256(f"{doc_id}|{chunk_text}|{seq}".encode("utf-8")).hexdigest()[:16]
    return f"{doc_id}_{seq}_{h}"


def _normalize_effective_date(raw: str) -> Tuple[str, str]:
    """
    Trả về (iso_date, error_reason).
    iso_date rỗng nếu không parse được.
    """
    s = (raw or "").strip()
    if not s:
        return "", "empty_effective_date"
    if _ISO_DATE.match(s):
        return s, ""
    m = _DMY_SLASH.match(s)
    if m:
        dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
        return f"{yyyy}-{mm}-{dd}", ""
    return "", "invalid_effective_date_format"


def load_raw_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({k: (v or "").strip() for k, v in r.items()})
    return rows


def clean_rows(
    rows: List[Dict[str, str]],
    *,
    apply_refund_window_fix: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Trả về (cleaned, quarantine).

    Baseline (mở rộng theo narrative Day 10):
    1) Quarantine: doc_id không thuộc allowlist (export lạ / catalog sai).
    2) Chuẩn hoá effective_date sang YYYY-MM-DD; quarantine nếu không parse được.
    3) Quarantine: chunk hr_leave_policy có effective_date < 2026-01-01 (bản HR cũ / conflict version).
    4) Quarantine: chunk_text rỗng hoặc effective_date rỗng sau chuẩn hoá.
    5) Loại trùng nội dung chunk_text (giữ bản đầu).
    6) Fix stale refund: policy_refund_v4 chứa '14 ngày làm việc' → 7 ngày.

    Mới — Sprint 2 (Group 15):
    R7) strip_invisible_unicode  : Xoá BOM + zero-width chars khỏi chunk_text trước mọi bước.
    R8) quarantine_missing_exported_at : Quarantine row thiếu exported_at (lineage không đầy đủ).
    R9) normalize_doc_id_case    : Lowercase + strip khoảng trắng doc_id trước allowlist check
                                   → chấp nhận "Policy_Refund_V4" thay vì quarantine unknown.
    """
    quarantine: List[Dict[str, Any]] = []
    seen_text: set[str] = set()
    cleaned: List[Dict[str, Any]] = []
    seq = 0

    for raw in rows:
        # R7 — strip_invisible_unicode: áp dụng TRƯỚC MỌI kiểm tra để tránh BOM làm lệch key dedup
        chunk_text_cleaned = _strip_invisible_unicode(raw.get("chunk_text", ""))

        # R9 — normalize_doc_id_case: lowercase + strip trước allowlist check
        doc_id = raw.get("doc_id", "").strip().lower()

        text = chunk_text_cleaned
        eff_raw = raw.get("effective_date", "")
        exported_at = raw.get("exported_at", "")

        # R8 — quarantine_missing_exported_at: lineage bắt buộc phải có timestamp nguồn
        if not exported_at.strip():
            quarantine.append({**raw, "doc_id": doc_id, "chunk_text": text,
                                "reason": "missing_exported_at"})
            continue

        if doc_id not in ALLOWED_DOC_IDS:
            quarantine.append({**raw, "doc_id": doc_id, "reason": "unknown_doc_id"})
            continue

        eff_norm, eff_err = _normalize_effective_date(eff_raw)
        if eff_err == "empty_effective_date":
            quarantine.append({**raw, "doc_id": doc_id, "chunk_text": text,
                                "reason": "missing_effective_date"})
            continue
        if eff_err == "invalid_effective_date_format":
            quarantine.append({**raw, "doc_id": doc_id, "chunk_text": text,
                                "reason": eff_err, "effective_date_raw": eff_raw})
            continue

        if doc_id == "hr_leave_policy" and eff_norm < "2026-01-01":
            quarantine.append(
                {
                    **raw,
                    "doc_id": doc_id,
                    "chunk_text": text,
                    "reason": "stale_hr_policy_effective_date",
                    "effective_date_normalized": eff_norm,
                }
            )
            continue

        if not text:
            quarantine.append({**raw, "doc_id": doc_id, "reason": "missing_chunk_text"})
            continue

        # Dedup dựa trên text đã được R7 làm sạch → BOM không còn làm lệch key
        key = _norm_text(text)
        if key in seen_text:
            quarantine.append({**raw, "doc_id": doc_id, "chunk_text": text,
                                "reason": "duplicate_chunk_text"})
            continue
        seen_text.add(key)

        fixed_text = text
        if apply_refund_window_fix and doc_id == "policy_refund_v4":
            if "14 ngày làm việc" in fixed_text:
                fixed_text = fixed_text.replace(
                    "14 ngày làm việc",
                    "7 ngày làm việc",
                )
                fixed_text += " [cleaned: stale_refund_window]"

        seq += 1
        cleaned.append(
            {
                "chunk_id": _stable_chunk_id(doc_id, fixed_text, seq),
                "doc_id": doc_id,
                "chunk_text": fixed_text,
                "effective_date": eff_norm,
                "exported_at": exported_at or "",
            }
        )

    return cleaned, quarantine


def write_cleaned_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at\n", encoding="utf-8")
        return
    fieldnames = ["chunk_id", "doc_id", "chunk_text", "effective_date", "exported_at"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def write_quarantine_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at,reason\n", encoding="utf-8")
        return
    keys: List[str] = []
    seen_k: set[str] = set()
    for r in rows:
        for k in r.keys():
            if k not in seen_k:
                seen_k.add(k)
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore", restval="")
        w.writeheader()
        for r in rows:
            w.writerow(r)
