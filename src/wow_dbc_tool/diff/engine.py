"""Diff 引擎 - DBC 文件差异对比."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from wow_dbc_tool.core.dbc_file import DBCFile
from wow_dbc_tool.core.dbc_record import DBCRecord
from wow_dbc_tool.core.exceptions import DBCDiffError


@dataclass
class DiffSummary:
    """差异摘要."""

    total_old: int = 0
    total_new: int = 0
    added_count: int = 0
    removed_count: int = 0
    modified_count: int = 0
    unchanged_count: int = 0

    def to_dict(self) -> dict:
        """转为字典."""
        return {
            "total_old": self.total_old,
            "total_new": self.total_new,
            "added_count": self.added_count,
            "removed_count": self.removed_count,
            "modified_count": self.modified_count,
            "unchanged_count": self.unchanged_count,
        }


@dataclass
class DiffReport:
    """差异报告."""

    added: list[dict] = field(default_factory=list)
    removed: list[dict] = field(default_factory=list)
    modified: list[dict] = field(default_factory=list)
    unchanged: list[dict] = field(default_factory=list)
    summary: DiffSummary = field(default_factory=DiffSummary)

    def to_dict(self) -> dict:
        """转为字典（JSON 输出）."""
        return {
            "summary": self.summary.to_dict(),
            "added": self.added,
            "removed": self.removed,
            "modified": self.modified,
            "unchanged": self.unchanged,
        }


class DBCDiff:
    """DBC 文件差异对比引擎.

    对比两个 DBC 文件，输出结构化差异报告。
    """

    def __init__(
        self,
        old: DBCFile,
        new: DBCFile,
        key_field: str = "ID",
    ):
        """初始化 Diff 引擎.

        Args:
            old: 旧版本 DBC 文件
            new: 新版本 DBC 文件
            key_field: 用于匹配记录的主键字段（默认 'ID'）
        """
        self.old = old
        self.new = new
        self.key_field = key_field

    def compare(self) -> DiffReport:
        """对比两个 DBC 文件.

        以 key_field 为键，建立 old 和 new 的索引，
        找出 added、removed、modified 和 unchanged 记录。

        如果 key_field 不存在，自动回退到 compare_by_index。

        Returns:
            结构化差异报告

        Raises:
            DBCDiffError: key_field 不存在且无法回退
        """
        # 验证 key_field 存在，不存在则回退
        try:
            self._validate_key_field()
        except DBCDiffError:
            # 回退到按索引对比
            return self.compare_by_index()

        # 建立索引
        old_index = self._build_index(self.old)
        new_index = self._build_index(self.new)

        old_keys = set(old_index.keys())
        new_keys = set(new_index.keys())

        added_keys = new_keys - old_keys
        removed_keys = old_keys - new_keys
        common_keys = old_keys & new_keys

        report = DiffReport()

        # 新增记录
        for key in sorted(added_keys):
            record = new_index[key]
            report.added.append(record.to_dict())

        # 删除记录
        for key in sorted(removed_keys):
            record = old_index[key]
            report.removed.append(record.to_dict())

        # 修改和未变更记录
        for key in sorted(common_keys):
            old_record = old_index[key]
            new_record = new_index[key]
            changes = self._find_changes(old_record, new_record)

            if changes:
                report.modified.append(
                    {
                        "key": {self.key_field: key},
                        "changes": changes,
                    }
                )
            else:
                report.unchanged.append(new_record.to_dict())

        # 生成摘要
        report.summary = DiffSummary(
            total_old=len(self.old.records),
            total_new=len(self.new.records),
            added_count=len(report.added),
            removed_count=len(report.removed),
            modified_count=len(report.modified),
            unchanged_count=len(report.unchanged),
        )

        return report

    def compare_by_index(self) -> DiffReport:
        """按记录索引对比（不依赖 key_field）.

        逐行对比，用于记录顺序有意义的场景。

        Returns:
            结构化差异报告
        """
        report = DiffReport()
        max_len = max(len(self.old.records), len(self.new.records))

        for i in range(max_len):
            if i >= len(self.old.records):
                # 新增
                report.added.append(self.new.records[i].to_dict())
            elif i >= len(self.new.records):
                # 删除
                report.removed.append(self.old.records[i].to_dict())
            else:
                old_record = self.old.records[i]
                new_record = self.new.records[i]
                changes = self._find_changes(old_record, new_record)

                if changes:
                    report.modified.append(
                        {
                            "index": i,
                            "changes": changes,
                        }
                    )
                else:
                    report.unchanged.append(new_record.to_dict())

        report.summary = DiffSummary(
            total_old=len(self.old.records),
            total_new=len(self.new.records),
            added_count=len(report.added),
            removed_count=len(report.removed),
            modified_count=len(report.modified),
            unchanged_count=len(report.unchanged),
        )

        return report

    def _validate_key_field(self) -> None:
        """验证 key_field 在两边都存在."""
        if not self.old.records:
            return
        if not self.new.records:
            return

        try:
            self.old.records[0].get(self.key_field)
        except Exception as err:
            raise DBCDiffError(f"旧文件中 key_field '{self.key_field}' 不存在") from err

        try:
            self.new.records[0].get(self.key_field)
        except Exception as err:
            raise DBCDiffError(f"新文件中 key_field '{self.key_field}' 不存在") from err

    def _build_index(self, dbc: DBCFile) -> dict[Any, DBCRecord]:
        """以 key_field 为键建立记录索引.

        Args:
            dbc: DBC 文件

        Returns:
            键到记录的映射
        """
        index: dict[Any, DBCRecord] = {}
        for record in dbc.records:
            try:
                key = record.get(self.key_field)
                index[key] = record
            except Exception:
                # 跳过无法获取 key 的记录
                pass
        return index

    def _find_changes(
        self,
        old: DBCRecord,
        new: DBCRecord,
    ) -> dict[str, dict[str, Any]]:
        """找出两条记录的差异字段.

        Args:
            old: 旧记录
            new: 新记录

        Returns:
            差异字段映射：{字段名: {"old": 旧值, "new": 新值}}
        """
        changes: dict[str, dict[str, Any]] = {}

        # 获取所有字段名
        old_fields = {f.name for f in old._schema}
        new_fields = {f.name for f in new._schema}
        all_fields = old_fields | new_fields

        for field_name in all_fields:
            try:
                old_value = old.get(field_name)
            except Exception:
                old_value = None

            try:
                new_value = new.get(field_name)
            except Exception:
                new_value = None

            if old_value != new_value:
                changes[field_name] = {
                    "old": old_value,
                    "new": new_value,
                }

        return changes
