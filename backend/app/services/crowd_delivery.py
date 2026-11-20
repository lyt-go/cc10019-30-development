"""人群交付服务：从已计算的圈选成员导出版本化交付文件。

交付文件是给活动组的可核对名单：写明所用计算版本与实际成员编号，
创建后内容不可变——重算圈选只会产生新版本，不会改写已交付的名单，
因此下载重试、重复导出都不会改变可核对的人数。
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from app.store import store

STATUS_PENDING = "待签收"
STATUS_CONFIRMED = "已签收"
STATUS_VOID = "已作废"


def delivery_checksum(member_ids: list[str]) -> str:
    """交付名单校验和：与 seed 中预置交付使用同一算法，供核对名单内容。"""
    return hashlib.sha256("|".join(sorted(member_ids)).encode("utf-8")).hexdigest()[:16]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _next_delivery_id() -> str:
    seq = 0
    for row in store.rows("crowd_delivery"):
        did = str(row.get("delivery_id", ""))
        if did.startswith("CD-"):
            try:
                seq = max(seq, int(did.split("-", 1)[1]))
            except (IndexError, ValueError):
                continue
    return f"CD-{seq + 1:03d}"


def export_delivery(condition_id: str) -> dict[str, Any]:
    """把当前已计算的圈选成员导出为一份交付文件。

    - 只消费已计算的圈选结果，导出本身不触发重算；
    - 同一圈选、同一计算版本重复导出时复用未作废的交付记录，
      避免文件重传产生两份名单、改变可核对人数。
    """
    condition = store.find_by_field("crowd_select", "condition_id", condition_id)
    if condition is None:
        raise ValueError(f"Crowd condition not found: {condition_id}")
    result = store.get_artifact("crowd_select", condition_id)
    if result is None:
        raise ValueError(f"Crowd result not computed yet: {condition_id}")

    compute_version = int(result.get("compute_version", 1))
    for row in store.find_all_by_field("crowd_delivery", "condition_id", condition_id):
        if int(row.get("compute_version", 0)) == compute_version and row.get("status") != STATUS_VOID:
            return row

    member_ids = sorted(str(u) for u in result.get("matched_users", []))
    row = {
        "status": STATUS_PENDING,
        "pending": True,
        "abnormal": False,
        "delivery_id": _next_delivery_id(),
        "condition_id": condition_id,
        "condition_name": condition.get("condition_name", ""),
        "compute_version": compute_version,
        "member_count": len(member_ids),
        "source_matched_count": int(result.get("matched_count", len(member_ids))),
        "member_ids": member_ids,
        "checksum": delivery_checksum(member_ids),
        "output_set": condition.get("output_set", ""),
        "logic_expr": condition.get("logic_expr", ""),
        "exported_at": _now(),
        "confirmed_at": "",
    }
    return store.insert("crowd_delivery", row)


def get_delivery_file(delivery_id: str) -> dict[str, Any] | None:
    """读取交付文件内容：每次返回同一份快照，下载重试不会改变名单。"""
    row = store.find_by_field("crowd_delivery", "delivery_id", delivery_id)
    if row is None:
        return None
    return {
        "delivery_id": row["delivery_id"],
        "condition_id": row["condition_id"],
        "condition_name": row.get("condition_name", ""),
        "compute_version": row["compute_version"],
        "output_set": row.get("output_set", ""),
        "logic_expr": row.get("logic_expr", ""),
        "member_count": row["member_count"],
        "checksum": row["checksum"],
        "exported_at": row.get("exported_at", ""),
        "member_ids": list(row.get("member_ids", [])),
    }


def list_deliveries() -> list[dict[str, Any]]:
    """交付记录列表，逐条附带与最新计算版本的对比。"""
    return [_enrich(row) for row in store.rows("crowd_delivery")]


def get_delivery(delivery_id: str) -> dict[str, Any] | None:
    """交付详情：附带尚未生效的变动，便于分清当次交付版本。"""
    row = store.find_by_field("crowd_delivery", "delivery_id", delivery_id)
    if row is None:
        return None
    return _enrich(row)


def _enrich(row: dict[str, Any]) -> dict[str, Any]:
    detail = dict(row)
    condition = store.find_by_field("crowd_select", "condition_id", row.get("condition_id"))
    latest_version = int(condition.get("compute_version", 0)) if condition else 0
    detail["latest_compute_version"] = latest_version
    detail["is_latest_version"] = int(row.get("compute_version", 0)) >= latest_version
    pending_change = None
    current = store.get_artifact("crowd_select", str(row.get("condition_id", "")))
    if current and int(current.get("compute_version", 0)) > int(row.get("compute_version", 0)):
        # 与导出时的全量命中数同口径对比，得到尚未生效的名单变动
        baseline = int(row.get("source_matched_count", row.get("member_count", 0)))
        pending_change = {
            "compute_version": current["compute_version"],
            "matched_count": current.get("matched_count", 0),
            "matched_delta": int(current.get("matched_count", 0)) - baseline,
        }
    detail["pending_change"] = pending_change
    return detail


def confirm_delivery(delivery_id: str) -> dict[str, Any]:
    """确认签收：交付记录生效；重复签收幂等。"""
    row = store.find_by_field("crowd_delivery", "delivery_id", delivery_id)
    if row is None:
        raise ValueError(f"Delivery not found: {delivery_id}")
    if row.get("status") == STATUS_VOID:
        raise ValueError(f"Delivery {delivery_id} is void and cannot be confirmed")
    if row.get("status") == STATUS_CONFIRMED:
        return row
    updated = store.update("crowd_delivery", int(row["id"]), {
        "status": STATUS_CONFIRMED,
        "pending": False,
        "confirmed_at": _now(),
    })
    return updated if updated is not None else row


def void_delivery(delivery_id: str) -> dict[str, Any]:
    """作废交付：仅限尚未签收的记录，已签收的交付不能作废。"""
    row = store.find_by_field("crowd_delivery", "delivery_id", delivery_id)
    if row is None:
        raise ValueError(f"Delivery not found: {delivery_id}")
    if row.get("status") == STATUS_CONFIRMED:
        raise ValueError(f"Delivery {delivery_id} is confirmed and cannot be voided")
    if row.get("status") == STATUS_VOID:
        return row
    updated = store.update("crowd_delivery", int(row["id"]), {
        "status": STATUS_VOID,
        "pending": False,
        "abnormal": True,
    })
    return updated if updated is not None else row


def verify_delivery(delivery_id: str) -> dict[str, Any] | None:
    """核对交付文件：圈选范围、名单数量与校验和是否一致。"""
    row = store.find_by_field("crowd_delivery", "delivery_id", delivery_id)
    if row is None:
        return None
    member_ids = [str(u) for u in row.get("member_ids", [])]
    condition = store.find_by_field("crowd_select", "condition_id", row.get("condition_id"))
    return {
        "delivery_id": row["delivery_id"],
        "condition_id": row["condition_id"],
        "output_set": row.get("output_set", ""),
        "logic_expr": row.get("logic_expr", ""),
        "compute_version": row["compute_version"],
        "latest_compute_version": int(condition.get("compute_version", 0)) if condition else 0,
        "member_count": row["member_count"],
        "listed_members": len(member_ids),
        "count_matches": int(row["member_count"]) == len(member_ids),
        "checksum": row["checksum"],
        "checksum_verified": delivery_checksum(member_ids) == row["checksum"],
        "status": row["status"],
    }
