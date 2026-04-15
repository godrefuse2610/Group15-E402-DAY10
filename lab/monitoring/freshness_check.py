"""
Kiểm tra freshness từ manifest pipeline (SLA đơn giản theo giờ).

Sinh viên mở rộng: đọc watermark DB, so sánh với clock batch, v.v.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts" / "data_contract.yaml"


def parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        # Cho phép "2026-04-10T08:00:00" không có timezone
        if ts.endswith("Z"):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _load_freshness_policy() -> tuple[str, float]:
    measured_at = "publish"
    sla_hours = 24.0
    if not CONTRACT_PATH.is_file():
        return measured_at, sla_hours
    try:
        data = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return measured_at, sla_hours
    freshness = data.get("freshness") or {}
    measured_at = str(freshness.get("measured_at") or measured_at).strip().lower()
    try:
        sla_hours = float(freshness.get("sla_hours", sla_hours))
    except (TypeError, ValueError):
        pass
    return measured_at, sla_hours


def check_manifest_freshness(
    manifest_path: Path,
    *,
    sla_hours: float | None = None,
    measured_at: str | None = None,
    now: datetime | None = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Trả về ("PASS" | "WARN" | "FAIL", detail dict).

    Đọc timestamp theo freshness policy trong contract.
    """
    now = now or datetime.now(timezone.utc)
    if not manifest_path.is_file():
        return "FAIL", {"reason": "manifest_missing", "path": str(manifest_path)}

    data: Dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract_measured_at, contract_sla_hours = _load_freshness_policy()
    measured_at = (measured_at or contract_measured_at or "publish").strip().lower()
    sla_hours = contract_sla_hours if sla_hours is None else float(sla_hours)

    timestamp_candidates = {
        "publish": data.get("run_timestamp"),
        "cleaned": data.get("run_timestamp"),
        "ingest": data.get("latest_exported_at"),
    }
    ts_raw = timestamp_candidates.get(measured_at) or data.get("run_timestamp") or data.get("latest_exported_at")
    dt = parse_iso(str(ts_raw)) if ts_raw else None
    if dt is None:
        return "WARN", {"reason": "no_timestamp_in_manifest", "measured_at": measured_at, "manifest": data}

    age_hours = (now - dt).total_seconds() / 3600.0
    detail = {
        "measured_at": measured_at,
        "checked_timestamp": ts_raw,
        "age_hours": round(age_hours, 3),
        "sla_hours": sla_hours,
    }
    if age_hours <= sla_hours:
        return "PASS", detail
    return "FAIL", {**detail, "reason": "freshness_sla_exceeded"}
