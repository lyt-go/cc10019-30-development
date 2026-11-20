"""人群交付链路测试：版本化导出、幂等下载、版本争用与交集核对。"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.seed import SEED_ROWS
from app.store import store
from app.services.crowd_select import select_crowd
from app.services.crowd_delivery import (
    confirm_delivery,
    delivery_checksum,
    export_delivery,
    get_delivery,
    get_delivery_file,
    verify_delivery,
    void_delivery,
)
from app.services.overlap_analysis import analyze_overlap


def reset_delivery_state() -> None:
    """重置交付相关状态，避免用例间通过单例 store 互相污染。"""
    store._artifacts.clear()
    store._tables["crowd_delivery"] = [dict(row) for row in SEED_ROWS["crowd_delivery"]]
    store._next_ids["crowd_delivery"] = (
        max(int(row["id"]) for row in SEED_ROWS["crowd_delivery"]) + 1
    )
    seed_by_condition = {row["condition_id"]: row for row in SEED_ROWS["crowd_select"]}
    for row in store.rows("crowd_select"):
        seed_row = seed_by_condition.get(row["condition_id"])
        if seed_row is not None:
            row["compute_version"] = seed_row.get("compute_version", 0)


class TestCrowdDelivery(unittest.TestCase):
    """人群交付文件的导出、下载与签收。"""

    def setUp(self) -> None:
        reset_delivery_state()

    def test_export_snapshots_compute_version_and_members(self) -> None:
        """交付文件写明所用计算版本与实际成员编号。"""
        result = select_crowd("CS-001")
        delivery = export_delivery("CS-001")
        self.assertEqual(delivery["compute_version"], result["compute_version"])
        self.assertEqual(delivery["member_count"], len(result["matched_users"]))
        self.assertEqual(delivery["member_ids"], sorted(result["matched_users"]))
        self.assertEqual(delivery["checksum"], delivery_checksum(delivery["member_ids"]))
        self.assertEqual(delivery["status"], "待签收")
        self.assertTrue(delivery["delivery_id"].startswith("CD-"))

    def test_export_requires_computed_result(self) -> None:
        """只能从已计算的圈选成员数据导出，未计算时拒绝。"""
        with self.assertRaises(ValueError):
            export_delivery("CS-003")
        with self.assertRaises(ValueError):
            export_delivery("CS-NONEXIST")

    def test_export_is_idempotent_per_version(self) -> None:
        """同一圈选同一计算版本重复导出复用原交付，不产生第二份名单。"""
        select_crowd("CS-001")
        first = export_delivery("CS-001")
        second = export_delivery("CS-001")
        self.assertEqual(first["delivery_id"], second["delivery_id"])
        same_version = [
            row
            for row in store.rows("crowd_delivery")
            if row["condition_id"] == "CS-001"
            and row["compute_version"] == first["compute_version"]
            and row["status"] != "已作废"
        ]
        self.assertEqual(len(same_version), 1)

    def test_recompute_keeps_delivered_file_unchanged(self) -> None:
        """版本争用：旧交付未签收时运营重算剔除会员，旧文件与下载内容不变。"""
        select_crowd("CS-001")
        delivery = export_delivery("CS-001")
        did = delivery["delivery_id"]
        original_members = list(delivery["member_ids"])
        removed = original_members[:10]

        # 运营重算并剔除一批会员 → 产生新版本
        rerun = select_crowd("CS-001", exclude_users=removed)
        self.assertEqual(rerun["compute_version"], delivery["compute_version"] + 1)
        self.assertEqual(rerun["matched_count"], delivery["source_matched_count"] - 10)
        self.assertEqual(rerun["excluded_count"], 10)

        # 旧交付文件不随重算改变，重复下载内容一致
        file_first = get_delivery_file(did)
        file_second = get_delivery_file(did)
        self.assertEqual(file_first, file_second)
        self.assertEqual(file_first["member_ids"], original_members)
        self.assertEqual(file_first["compute_version"], delivery["compute_version"])
        self.assertEqual(file_first["member_count"], delivery["member_count"])

        # 详情能分清当次交付版本与尚未生效的变动
        detail = get_delivery(did)
        self.assertEqual(detail["compute_version"], delivery["compute_version"])
        self.assertEqual(detail["latest_compute_version"], rerun["compute_version"])
        self.assertFalse(detail["is_latest_version"])
        self.assertIsNotNone(detail["pending_change"])
        self.assertEqual(detail["pending_change"]["compute_version"], rerun["compute_version"])
        self.assertEqual(detail["pending_change"]["matched_delta"], -10)

        # 新版本可再导出为新交付，两个版本争用一次交付时各自可区分
        newer = export_delivery("CS-001")
        self.assertNotEqual(newer["delivery_id"], did)
        self.assertEqual(newer["compute_version"], rerun["compute_version"])
        self.assertEqual(newer["source_matched_count"], rerun["matched_count"])
        newer_detail = get_delivery(newer["delivery_id"])
        self.assertTrue(newer_detail["is_latest_version"])
        self.assertIsNone(newer_detail["pending_change"])

    def test_confirm_and_void_flow(self) -> None:
        """签收/作废状态流转：重复签收幂等，已签收不能作废，作废不能签收。"""
        select_crowd("CS-001")
        delivery = export_delivery("CS-001")
        did = delivery["delivery_id"]

        confirmed = confirm_delivery(did)
        self.assertEqual(confirmed["status"], "已签收")
        self.assertFalse(confirmed["pending"])
        self.assertTrue(confirmed["confirmed_at"])
        # 重复签收幂等
        self.assertEqual(confirm_delivery(did)["status"], "已签收")
        # 已签收不能作废
        with self.assertRaises(ValueError):
            void_delivery(did)

        select_crowd("CS-002")
        other = export_delivery("CS-002")
        voided = void_delivery(other["delivery_id"])
        self.assertEqual(voided["status"], "已作废")
        with self.assertRaises(ValueError):
            confirm_delivery(other["delivery_id"])
        with self.assertRaises(ValueError):
            confirm_delivery("CD-NONEXIST")

    def test_verify_delivery_checks_scope_and_count(self) -> None:
        """核对接口能验证选定圈选范围以及名单数量。"""
        select_crowd("CS-001")
        delivery = export_delivery("CS-001")
        report = verify_delivery(delivery["delivery_id"])
        self.assertIsNotNone(report)
        self.assertEqual(report["output_set"], "crowd_high_value_active")
        self.assertEqual(report["logic_expr"], "TAG-001 AND TAG-003")
        self.assertEqual(report["member_count"], delivery["member_count"])
        self.assertTrue(report["count_matches"])
        self.assertTrue(report["checksum_verified"])
        self.assertEqual(report["compute_version"], delivery["compute_version"])

        # 预置交付同样可核对
        seeded = verify_delivery("CD-001")
        self.assertTrue(seeded["count_matches"])
        self.assertTrue(seeded["checksum_verified"])


class TestOverlapWithDelivery(unittest.TestCase):
    """交集分析按交付编号比较活动范围。"""

    def setUp(self) -> None:
        reset_delivery_state()

    def test_overlap_compares_delivery_files(self) -> None:
        """交集分析读取交付文件成员集合，重算圈选不改变已交付人数。"""
        overlap = analyze_overlap("OA-001")
        self.assertEqual(overlap["source"], "delivery_file")
        self.assertEqual(overlap["delivery_a"], "CD-001")
        self.assertEqual(overlap["delivery_b"], "CD-002")
        self.assertEqual(overlap["crowd_a"], "CS-001")
        self.assertEqual(overlap["crowd_b"], "CS-002")
        self.assertEqual(overlap["compute_version_a"], 1)
        self.assertEqual(overlap["compute_version_b"], 1)
        self.assertEqual(overlap["users_a_count"], 80)
        self.assertEqual(overlap["users_b_count"], 80)
        self.assertEqual(overlap["result_count"], 40)

        # 运营重算（版本推进、名单变化）后，交付文件驱动的比较结果不变
        select_crowd("CS-001", exclude_users=["U00001", "U00002", "U00003"])
        select_crowd("CS-002")
        again = analyze_overlap("OA-001")
        self.assertEqual(again["users_a_count"], 80)
        self.assertEqual(again["users_b_count"], 80)
        self.assertEqual(again["result_count"], 40)

    def test_overlap_falls_back_to_crowd_result(self) -> None:
        """未指定交付编号的任务仍按圈选实时结果计算。"""
        overlap = analyze_overlap("OA-002")
        self.assertEqual(overlap["source"], "crowd_result")
        self.assertIsNone(overlap["delivery_a"])
        self.assertIsNone(overlap["delivery_b"])
        self.assertGreater(overlap["users_a_count"], 0)

    def test_overlap_rejects_missing_delivery(self) -> None:
        """交付编号不存在时明确报错，而不是静默换一份名单。"""
        task = store.find_by_field("overlap_analysis", "task_id", "OA-001")
        original = task["delivery_a"]
        task["delivery_a"] = "CD-NONEXIST"
        try:
            with self.assertRaises(ValueError):
                analyze_overlap("OA-001")
        finally:
            task["delivery_a"] = original


if __name__ == "__main__":
    unittest.main(verbosity=2)
