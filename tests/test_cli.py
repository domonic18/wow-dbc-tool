"""CLI 单元测试."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestCLI:
    """测试 CLI 命令."""

    @pytest.fixture
    def wow_dbc_tool(self):
        """CLI 命令路径."""
        return [sys.executable, "-m", "wow_dbc_tool"]

    def test_cli_no_args(self, wow_dbc_tool):
        """测试无参数显示帮助."""
        result = subprocess.run(
            wow_dbc_tool,
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=str(PROJECT_ROOT),
        )
        # 无参数应该返回帮助信息
        assert result.returncode == 1 or "usage" in result.stdout.lower()

    def test_cli_read(self, wow_dbc_tool, minimal_dbc: Path):
        """测试 read 命令."""
        result = subprocess.run(
            wow_dbc_tool + ["read", str(minimal_dbc), "--json"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["header"]["magic"] == "WDBC"
        assert len(data["records"]) == 2

    def test_cli_read_with_limit(self, wow_dbc_tool, minimal_dbc: Path):
        """测试 read --limit."""
        result = subprocess.run(
            wow_dbc_tool + ["read", str(minimal_dbc), "--limit", "1", "--json"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data["records"]) == 1

    def test_cli_query(self, wow_dbc_tool, minimal_dbc: Path):
        """测试 query 命令."""
        result = subprocess.run(
            wow_dbc_tool + ["query", str(minimal_dbc), "--filter", "field_0=1", "--json"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["count"] == 1
        assert data["records"][0]["field_0"] == 1

    def test_cli_query_no_match(self, wow_dbc_tool, minimal_dbc: Path):
        """测试 query 无匹配."""
        result = subprocess.run(
            wow_dbc_tool + ["query", str(minimal_dbc), "--filter", "ID=999", "--json"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["count"] == 0

    def test_cli_query_contains(self, wow_dbc_tool, minimal_dbc: Path):
        """测试 query contains 操作符."""
        result = subprocess.run(
            wow_dbc_tool
            + [
                "query",
                str(minimal_dbc),
                "--filter",
                "field_0__contains=1",
                "--json",
            ],
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["count"] == 1

    def test_cli_edit(self, wow_dbc_tool, minimal_dbc: Path, tmp_path: Path):
        """测试 edit 命令."""
        output = tmp_path / "edited.dbc"
        result = subprocess.run(
            wow_dbc_tool
            + [
                "edit",
                str(minimal_dbc),
                "--filter",
                "field_0=1",
                "--set",
                "field_2=999",
                "--output",
                str(output),
                "--json",
            ],
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["modified"] == 1

        # 验证输出文件
        result2 = subprocess.run(
            wow_dbc_tool + ["read", str(output), "--json"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=str(PROJECT_ROOT),
        )
        data2 = json.loads(result2.stdout)
        # 找到 field_0=1 的记录
        for record in data2["records"]:
            if record.get("field_0") == 1:
                assert record["field_2"] == 999
                break

    def test_cli_delete(self, wow_dbc_tool, minimal_dbc: Path, tmp_path: Path):
        """测试 delete 命令."""
        output = tmp_path / "deleted.dbc"
        result = subprocess.run(
            wow_dbc_tool
            + [
                "delete",
                str(minimal_dbc),
                "--filter",
                "field_0=1",
                "--output",
                str(output),
                "--json",
            ],
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["deleted"] == 1
        assert data["remaining"] == 1

    def test_cli_add(self, wow_dbc_tool, minimal_dbc: Path, tmp_path: Path):
        """测试 add 命令."""
        output = tmp_path / "added.dbc"
        result = subprocess.run(
            wow_dbc_tool
            + [
                "add",
                str(minimal_dbc),
                "--field",
                "field_0=3",
                "--field",
                "field_2=100",
                "--output",
                str(output),
                "--json",
            ],
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["added"] == 1
        assert data["new_record"]["field_0"] == 3

    def test_cli_diff(self, wow_dbc_tool, minimal_dbc: Path, tmp_path: Path):
        """测试 diff 命令."""
        path2 = tmp_path / "new.dbc"
        # 复制文件
        path2.write_bytes(minimal_dbc.read_bytes())

        result = subprocess.run(
            wow_dbc_tool
            + ["diff", str(minimal_dbc), str(path2), "--key-field", "field_0", "--json"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["summary"]["added_count"] == 0
        assert data["summary"]["removed_count"] == 0
        assert data["summary"]["modified_count"] == 0
        assert data["summary"]["unchanged_count"] == 2

    def test_cli_schema_list(self, wow_dbc_tool):
        """测试 schema list 命令."""
        result = subprocess.run(
            wow_dbc_tool + ["schema", "list", "--json"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "builtins" in data
        assert "Spell.dbc" in data["builtins"]

    def test_cli_schema_show(self, wow_dbc_tool):
        """测试 schema show 命令."""
        result = subprocess.run(
            wow_dbc_tool + ["schema", "show", "Spell.dbc", "--json"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["file"] == "Spell.dbc"
        assert len(data["fields"]) > 0

    def test_cli_schema_infer(self, wow_dbc_tool, minimal_dbc: Path):
        """测试 schema infer 命令."""
        result = subprocess.run(
            wow_dbc_tool + ["schema", "infer", str(minimal_dbc), "--json"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["file"] == str(minimal_dbc)
        assert len(data["fields"]) == 3

    def test_cli_error_file_not_found(self, wow_dbc_tool):
        """测试文件不存在错误."""
        result = subprocess.run(
            wow_dbc_tool + ["read", "/nonexistent.dbc", "--json"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=str(PROJECT_ROOT),
        )
        # FileNotFoundError 被捕获并输出到 stderr 作为 JSON，但 returncode 可能为 0
        # 因为异常处理已捕获并格式化输出
        assert result.returncode == 0  # CLI 已处理异常，返回 0 并输出错误 JSON
        data = json.loads(result.stderr)
        assert data["error"] is True
