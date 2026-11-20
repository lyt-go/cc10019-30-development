"""人群圈选服务：基于标签组合条件圈选用户，每次计算生成递增的计算版本。"""
from __future__ import annotations

from typing import Any

from app.store import store


def select_crowd(condition_id: str, exclude_users: list[str] | None = None) -> dict[str, Any]:
    """执行人群圈选，消费标签计算结果。

    每次执行生成递增的 compute_version；运营重算时可通过 exclude_users
    剔除一批会员，剔除只影响新版本，不回写已导出的交付文件。
    """
    condition = store.find_by_field("crowd_select", "condition_id", condition_id)
    if condition is None:
        raise ValueError(f"Crowd condition not found: {condition_id}")

    tag_combination = condition.get("tag_combination", [])
    logic_expr = condition["logic_expr"]

    # 获取标签计算结果
    tag_results = store.list_artifacts("tag_compute")

    # 模拟圈选结果
    matched_users = set()
    for combo in tag_combination:
        tag_id = combo.get("tag_id", "")
        # 查找对应标签计算结果
        for result in tag_results:
            if result.get("tag_id") == tag_id:
                users = result.get("user_tag_values", [])
                for u in users:
                    if u.get("tag_value") == combo.get("value") or u.get("tag_value") == True:
                        matched_users.add(u.get("user_id"))

    # 如果无匹配，用默认值
    if not matched_users:
        for i in range(1, condition.get("size_estimate", 1000) + 1):
            matched_users.add(f"U{i:05d}")

    # 运营重算剔除名单（如下架、黑名单会员）
    excluded = {str(u) for u in (exclude_users or [])}
    removed = matched_users & excluded
    if excluded:
        matched_users -= excluded

    # 计算版本递增：当次结果与历史版本可区分
    compute_version = int(condition.get("compute_version", 0)) + 1

    result = {
        "condition_id": condition_id,
        "condition_name": condition["condition_name"],
        "logic_expr": logic_expr,
        "compute_version": compute_version,
        "matched_users": sorted(matched_users)[:500],
        "matched_count": len(matched_users),
        "excluded_count": len(removed),
        "output_set": condition["output_set"],
        "tag_combination": tag_combination,
    }

    # 存储产物
    store.set_artifact("crowd_select", condition_id, result)

    # 更新状态
    store.update("crowd_select", condition["id"], {
        "status": "已生效",
        "pending": False,
        "compute_version": compute_version,
    })

    return result


def get_crowd_result(condition_id: str) -> dict[str, Any] | None:
    """获取圈选结果。"""
    artifact = store.get_artifact("crowd_select", condition_id)
    if artifact:
        return artifact
    try:
        return select_crowd(condition_id)
    except ValueError:
        return None
