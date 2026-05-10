"""Diff 引擎单元测试."""

from __future__ import annotations

from pathlib import Path

import pytest

from wow_dbc_tool.core.dbc_file import DBCFile
from wow_dbc_tool.diff.engine import DBCDiff, DiffReport
from wow_dbc_tool.schema.field_def import FieldDef


class TestDBCDiff:
    """测试 DBCDiff."""

    @pytest.fixture
    def sample_schema(self):
        """示例字段定义."""
        return [
            FieldDef("ID", "uint32", 0),
            FieldDef("Name", "string", 4),
            FieldDef("Value", "uint32", 8),
        ]

    def test_compare_no_changes(self, tmp_path: Path, sample_schema):
        """测试无变化的对比."""
        from tests.conftest import create_dbc_with_data

        path1 = tmp_path / "old.dbc"
        path2 = tmp_path / "new.dbc"

        data = [
            {"ID": 1, "Name": "A", "Value": 10},
            {"ID": 2, "Name": "B", "Value": 20},
        ]
        create_dbc_with_data(path1, data, ["ID", "Name", "Value"], {"Name"})
        create_dbc_with_data(path2, data, ["ID", "Name", "Value"], {"Name"})

        old = DBCFile(path1, schema=sample_schema).load()
        new = DBCFile(path2, schema=sample_schema).load()

        diff = DBCDiff(old, new)
        report = diff.compare()

        assert report.summary.added_count == 0
        assert report.summary.removed_count == 0
        assert report.summary.modified_count == 0
        assert report.summary.unchanged_count == 2

    def test_compare_added(self, tmp_path: Path, sample_schema):
        """测试新增记录检测."""
        from tests.conftest import create_dbc_with_data

        path1 = tmp_path / "old.dbc"
        path2 = tmp_path / "new.dbc"

        data1 = [
            {"ID": 1, "Name": "A", "Value": 10},
        ]
        data2 = [
            {"ID": 1, "Name": "A", "Value": 10},
            {"ID": 2, "Name": "B", "Value": 20},
        ]
        create_dbc_with_data(path1, data1, ["ID", "Name", "Value"], {"Name"})
        create_dbc_with_data(path2, data2, ["ID", "Name", "Value"], {"Name"})

        old = DBCFile(path1, schema=sample_schema).load()
        new = DBCFile(path2, schema=sample_schema).load()

        diff = DBCDiff(old, new)
        report = diff.compare()

        assert report.summary.added_count == 1
        assert report.summary.removed_count == 0
        assert report.summary.modified_count == 0
        assert len(report.added) == 1
        assert report.added[0]["ID"] == 2

    def test_compare_removed(self, tmp_path: Path, sample_schema):
        """测试删除记录检测."""
        from tests.conftest import create_dbc_with_data

        path1 = tmp_path / "old.dbc"
        path2 = tmp_path / "new.dbc"

        data1 = [
            {"ID": 1, "Name": "A", "Value": 10},
            {"ID": 2, "Name": "B", "Value": 20},
        ]
        data2 = [
            {"ID": 1, "Name": "A", "Value": 10},
        ]
        create_dbc_with_data(path1, data1, ["ID", "Name", "Value"], {"Name"})
        create_dbc_with_data(path2, data2, ["ID", "Name", "Value"], {"Name"})

        old = DBCFile(path1, schema=sample_schema).load()
        new = DBCFile(path2, schema=sample_schema).load()

        diff = DBCDiff(old, new)
        report = diff.compare()

        assert report.summary.added_count == 0
        assert report.summary.removed_count == 1
        assert report.summary.modified_count == 0
        assert len(report.removed) == 1
        assert report.removed[0]["ID"] == 2

    def test_compare_modified(self, tmp_path: Path, sample_schema):
        """测试修改记录检测."""
        from tests.conftest import create_dbc_with_data

        path1 = tmp_path / "old.dbc"
        path2 = tmp_path / "new.dbc"

        data1 = [
            {"ID": 1, "Name": "A", "Value": 10},
        ]
        data2 = [
            {"ID": 1, "Name": "A-Modified", "Value": 99},
        ]
        create_dbc_with_data(path1, data1, ["ID", "Name", "Value"], {"Name"})
        create_dbc_with_data(path2, data2, ["ID", "Name", "Value"], {"Name"})

        old = DBCFile(path1, schema=sample_schema).load()
        new = DBCFile(path2, schema=sample_schema).load()

        diff = DBCDiff(old, new)
        report = diff.compare()

        assert report.summary.added_count == 0
        assert report.summary.removed_count == 0
        assert report.summary.modified_count == 1
        assert len(report.modified) == 1

        changes = report.modified[0]["changes"]
        assert "Name" in changes
        assert changes["Name"]["old"] == "A"
        assert changes["Name"]["new"] == "A-Modified"
        assert "Value" in changes
        assert changes["Value"]["old"] == 10
        assert changes["Value"]["new"] == 99

    def test_compare_mixed_changes(self, tmp_path: Path, sample_schema):
        """测试混合变化."""
        from tests.conftest import create_dbc_with_data

        path1 = tmp_path / "old.dbc"
        path2 = tmp_path / "new.dbc"

        data1 = [
            {"ID": 1, "Name": "A", "Value": 10},
            {"ID": 2, "Name": "B", "Value": 20},
            {"ID": 3, "Name": "C", "Value": 30},
        ]
        data2 = [
            {"ID": 1, "Name": "A-Modified", "Value": 10},
            {"ID": 3, "Name": "C", "Value": 30},
            {"ID": 4, "Name": "D", "Value": 40},
        ]
        create_dbc_with_data(path1, data1, ["ID", "Name", "Value"], {"Name"})
        create_dbc_with_data(path2, data2, ["ID", "Name", "Value"], {"Name"})

        old = DBCFile(path1, schema=sample_schema).load()
        new = DBCFile(path2, schema=sample_schema).load()

        diff = DBCDiff(old, new)
        report = diff.compare()

        assert report.summary.total_old == 3
        assert report.summary.total_new == 3
        assert report.summary.added_count == 1  # ID=4
        assert report.summary.removed_count == 1  # ID=2
        assert report.summary.modified_count == 1  # ID=1
        assert report.summary.unchanged_count == 1  # ID=3

    def test_compare_by_index(self, tmp_path: Path, sample_schema):
        """测试按索引对比."""
        from tests.conftest import create_dbc_with_data

        path1 = tmp_path / "old.dbc"
        path2 = tmp_path / "new.dbc"

        data1 = [
            {"ID": 1, "Name": "A", "Value": 10},
            {"ID": 2, "Name": "B", "Value": 20},
        ]
        data2 = [
            {"ID": 1, "Name": "A", "Value": 10},
            {"ID": 2, "Name": "B-Modified", "Value": 20},
        ]
        create_dbc_with_data(path1, data1, ["ID", "Name", "Value"], {"Name"})
        create_dbc_with_data(path2, data2, ["ID", "Name", "Value"], {"Name"})

        old = DBCFile(path1, schema=sample_schema).load()
        new = DBCFile(path2, schema=sample_schema).load()

        diff = DBCDiff(old, new)
        report = diff.compare_by_index()

        assert report.summary.modified_count == 1
        assert len(report.modified) == 1
        assert report.modified[0]["index"] == 1

    def test_compare_custom_key_field(self, tmp_path: Path):
        """测试自定义主键字段."""
        from tests.conftest import create_dbc_with_data

        schema = [
            FieldDef("Name", "string", 0),
            FieldDef("Value", "uint32", 4),
        ]

        path1 = tmp_path / "old.dbc"
        path2 = tmp_path / "new.dbc"

        data1 = [
            {"Name": "A", "Value": 10},
        ]
        data2 = [
            {"Name": "A", "Value": 99},
        ]
        create_dbc_with_data(path1, data1, ["Name", "Value"], {"Name"})
        create_dbc_with_data(path2, data2, ["Name", "Value"], {"Name"})

        old = DBCFile(path1, schema=schema).load()
        new = DBCFile(path2, schema=schema).load()

        diff = DBCDiff(old, new, key_field="Name")
        report = diff.compare()

        assert report.summary.modified_count == 1
        assert report.modified[0]["key"] == {"Name": "A"}


class TestDiffReport:
    """测试 DiffReport."""

    def test_to_dict(self):
        """测试转为字典."""
        from wow_dbc_tool.diff.engine import DiffSummary

        report = DiffReport()
        report.summary = DiffSummary(
            total_old=10,
            total_new=12,
            added_count=2,
            removed_count=1,
            modified_count=3,
            unchanged_count=6,
        )
        report.added = [{"ID": 11}]
        report.removed = [{"ID": 2}]

        data = report.to_dict()
        assert data["summary"]["total_old"] == 10
        assert data["summary"]["added_count"] == 2
        assert len(data["added"]) == 1
        assert len(data["removed"]) == 1
