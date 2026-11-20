"""人群交付路由：交付文件的导出、下载、核对与签收流转。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.schemas import ActionPayload, ActionResult
from app.services.crowd_delivery import (
    confirm_delivery,
    export_delivery,
    get_delivery,
    get_delivery_file,
    list_deliveries,
    verify_delivery,
    void_delivery,
)
from app.store import query_filters

router = APIRouter(prefix="/api/crowd-delivery", tags=["crowd_delivery"])


@router.get("")
def index(request: Request, page: int = 1, size: int = 20) -> dict[str, Any]:
    rows = list_deliveries()
    filters = query_filters(request)
    if filters:
        rows = [r for r in rows if all(str(r.get(k)) == str(v) for k, v in filters.items())]
    total = len(rows)
    start = (page - 1) * size
    return {"items": rows[start : start + size], "total": total, "page": page, "size": size}


@router.post("/export/{condition_id}")
def export(condition_id: str) -> ActionResult:
    """从已计算的圈选成员导出交付文件；同版本重复导出复用原记录。"""
    try:
        row = export_delivery(condition_id)
        return ActionResult(ok=True, message="Exported", entry=row)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{delivery_id}")
def detail(delivery_id: str) -> dict[str, Any]:
    row = get_delivery(delivery_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    return row


@router.get("/{delivery_id}/download")
def download(delivery_id: str) -> JSONResponse:
    """下载交付文件：内容来自不可变快照，重试与刷新不会改变名单。"""
    file_data = get_delivery_file(delivery_id)
    if file_data is None:
        raise HTTPException(status_code=404, detail="Not found")
    return JSONResponse(
        content=file_data,
        headers={"Content-Disposition": f'attachment; filename="crowd_delivery_{delivery_id}.json"'},
    )


@router.get("/{delivery_id}/verify")
def verify(delivery_id: str) -> dict[str, Any]:
    """核对交付文件：圈选范围、名单数量与校验和。"""
    result = verify_delivery(delivery_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Not found")
    return result


@router.post("/{delivery_id}/actions")
def run_action(delivery_id: str, payload: ActionPayload) -> ActionResult:
    try:
        if payload.action == "确认签收":
            row = confirm_delivery(delivery_id)
        elif payload.action == "作废":
            row = void_delivery(delivery_id)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported action: {payload.action}")
        return ActionResult(ok=True, message=payload.action, entry=row)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
