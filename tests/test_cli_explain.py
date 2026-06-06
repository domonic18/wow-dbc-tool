"""测试 CLI explain 和 help 集成."""

import json

from wow_dbc_tool.cli import cmd_explain, cmd_help


class TestCmdHelp:
    """测试 CLI help 命令."""

    def test_help_brief(self, capsys):
        """测试简洁帮助."""

        class Args:
            full = False
            command_name = None
            compact = True

        result = cmd_help(Args())
        assert result == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "tool" in data
        assert "commands" in data
        assert any(c["name"] == "explain" for c in data["commands"])

    def test_help_command(self, capsys):
        """测试子命令帮助."""

        class Args:
            full = False
            command_name = "read"
            compact = True

        result = cmd_help(Args())
        assert result == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["command"] == "read"
        assert "examples" in data

    def test_help_full(self, capsys):
        """测试完整帮助."""

        class Args:
            full = True
            command_name = None
            compact = True

        result = cmd_help(Args())
        assert result == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "usage_tips" in data
        assert len(data["commands"]) >= 9

    def test_help_unknown_command(self, capsys):
        """测试未知命令帮助."""

        class Args:
            full = False
            command_name = "nonexistent"
            compact = True

        result = cmd_help(Args())
        assert result == 1

        captured = capsys.readouterr()
        assert "error" in captured.err


class TestCmdExplain:
    """测试 CLI explain 命令."""

    def test_explain_missing_doc(self, capsys, tmp_path):
        """测试查询不存在的文档."""

        class Args:
            dbc_name = "Nonexistent.dbc"
            field = []
            compact = True

        result = cmd_explain(Args())
        assert result == 1

        captured = capsys.readouterr()
        assert "error" in captured.err

    def test_explain_file(self, capsys, tmp_path):
        """测试查询文件说明."""
        # 创建测试文档
        from wow_dbc_tool.utils.doc_store import DocEntry, DocStore

        store = DocStore(tmp_path)
        entry = DocEntry(
            name="Test.dbc",
            title="Test DBC",
            field_count=2,
            fields=[
                {"name": "ID", "type": "uint32", "offset": 0, "description": "ID"},
                {"name": "Name", "type": "string", "offset": 4, "description": "Name"},
            ],
            overview="Test overview",
        )
        store.save(entry)

        class Args:
            dbc_name = "Test.dbc"
            field = []
            compact = True

        # 使用测试目录的 store
        original_find = DocStore._find_default_docs_dir
        DocStore._find_default_docs_dir = lambda self: tmp_path

        try:
            result = cmd_explain(Args())
            assert result == 0

            captured = capsys.readouterr()
            data = json.loads(captured.out)
            assert data["dbc_name"] == "Test.dbc"
            assert "fields_summary" in data
            assert len(data["fields_summary"]) == 2
        finally:
            DocStore._find_default_docs_dir = original_find

    def test_explain_field(self, capsys, tmp_path):
        """测试查询特定字段."""
        from wow_dbc_tool.utils.doc_store import DocEntry, DocStore

        store = DocStore(tmp_path)
        entry = DocEntry(
            name="Test.dbc",
            title="Test DBC",
            fields=[
                {"name": "ID", "type": "uint32", "offset": 0, "description": "ID"},
                {"name": "Name", "type": "string", "offset": 4, "description": "Name"},
            ],
        )
        store.save(entry)

        class Args:
            dbc_name = "Test.dbc"
            field = ["ID", "Missing"]
            compact = True

        original_find = DocStore._find_default_docs_dir
        DocStore._find_default_docs_dir = lambda self: tmp_path

        try:
            result = cmd_explain(Args())
            assert result == 0

            captured = capsys.readouterr()
            data = json.loads(captured.out)
            assert "ID" in data["fields"]
            assert "Missing" in data["not_found"]
        finally:
            DocStore._find_default_docs_dir = original_find


