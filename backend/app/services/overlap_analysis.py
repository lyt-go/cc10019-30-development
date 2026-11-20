"""交集分析服务：计算两个人群的交集、并集或差集。

任务指定交付编号时，成员集合来自不可变的人群交付文件，
重算圈选、文件重传或下载重试都不会改变可核对的人数。
"""
from __future__ import annotations

from typing import Any

from app.store import store
from app.services.crowd_select import get_crowd_result
from app.services.crowd_delivery import get_delivery_file


def analyze_overlap(task_id: str) -> dict[str, Any]:
    """执行交集分析：优先按交付编号读取交付文件，否则回退到圈选实时结果。"""
    task = store.find_by_field("overlap_analysis", "task_id", task_id)
    if task is None:
        raise ValueError(f"Overlap task not found: {task_id}")

    intersect_mode = task["intersect_mode"]
    analysis_dims = task.get("analysis_dims", [])
    delivery_a_id = str(task.get("delivery_a") or "")
    delivery_b_id = str(task.get("delivery_b") or "")

    source = "crowd_result"
    version_a: int | None = None
    version_b: int | None = None

    if delivery_a_id and delivery_b_id:
        # 交付文件路径：成员集合来自不可变的交付快照
        file_a = get_delivery_file(delivery_a_id)
        file_b = get_delivery_file(delivery_b_id)
        if file_a is None or file_b is None:
            raise ValueError(f"Delivery file not found: {delivery_a_id}/{delivery_b_id}")
        users_a = set(file_a["member_ids"])
        users_b = set(file_b["member_ids"])
        crowd_a_id = str(file_a["condition_id"])
        crowd_b_id = str(file_b["condition_id"])
        version_a = int(file_a["compute_version"])
        version_b = int(file_b["compute_version"])
        source = "delivery_file"
    else:
        crowd_a_id = task["crowd_a"]
        crowd_b_id = task["crowd_b"]

        # 获取两个人群的圈选结果
        crowd_a = get_crowd_result(crowd_a_id)
        crowd_b = get_crowd_result(crowd_b_id)

        if crowd_a is None or crowd_b is None:
            raise ValueError("Crowd result not found")

        users_a = set(crowd_a.get("matched_users", []))
        users_b = set(crowd_b.get("matched_users", []))
        version_a = int(crowd_a.get("compute_version", 0)) or None
        version_b = int(crowd_b.get("compute_version", 0)) or None

    # 计算交集模式
    if intersect_mode == "intersect":
        result_users = users_a & users_b
    elif intersect_mode == "union":
        result_users = users_a | users_b
    elif intersect_mode == "diff":
        result_users = users_a - users_b
    elif intersect_mode == "a_only":
        result_users = users_a - users_b
    elif intersect_mode == "b_only":
        result_users = users_b - users_a
    else:
        result_users = users_a & users_b

    # 维度分析
    dim_stats: dict[str, dict[str, int]] = {}
    for dim in analysis_dims:
        dim_stats[dim] = {}
        # 模拟维度分布
        for user in result_users:
            val = f"{dim}_val_{hash(user) % 5}"
            dim_stats[dim][val] = dim_stats[dim].get(val, 0) + 1

    result = {
        "task_id": task_id,
        "crowd_a": crowd_a_id,
        "crowd_b": crowd_b_id,
        "intersect_mode": intersect_mode,
        "source": source,
        "delivery_a": delivery_a_id or None,
        "delivery_b": delivery_b_id or None,
        "compute_version_a": version_a,
        "compute_version_b": version_b,
        "users_a_count": len(users_a),
        "users_b_count": len(users_b),
        "result_count": len(result_users),
        "intersection_rate": len(users_a & users_b) / len(users_a) if users_a else 0.0,
        "dim_stats": dim_stats,
        "result_table": task.get("result_table", ""),
    }

    # 存储产物
    store.set_artifact("overlap_analysis", task_id, result)

    # 更新状态
    store.update("overlap_analysis", task["id"], {
        "status": "已完成",
        "pending": False,
    })

    return result


def get_overlap_result(task_id: str) -> dict[str, Any] | None:
    """获取交集分析结果。"""
    artifact = store.get_artifact("overlap_analysis", task_id)
    if artifact:
        return artifact
    try:
        return analyze_overlap(task_id)
    except ValueError:
        return None
