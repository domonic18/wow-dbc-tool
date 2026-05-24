"""测试帮助系统模块."""

import pytest

from wow_dbc_tool.utils.help_system import CommandHelp, HelpSystem


class TestCommandHelp:
    """测试 CommandHelp 数据类."""

    def test_default_creation(self):
        """测试默认创建."""
        cmd = CommandHelp(name="test")
        assert cmd.name == "test"
        assert cmd.brief == ""
        assert cmd.description == ""
        assert cmd.args == []
        assert cmd.examples == []
        assert cmd.notes == []

    def test_full_creation(self):
        """测试完整创建."""
        cmd = CommandHelp(
            name="read",
            brief="读取文件",
            description="读取 DBC 文件",
            args=[{"name": "file", "type": "Path"}],
            examples=["wow-dbc-tool read Spell.dbc"],
            notes=["注意备份"],
        )
        assert cmd.name == "read"
        assert cmd.brief == "读取文件"


class TestHelpSystem:
    """测试 HelpSystem 类."""

    def test_init_loads_builtins(self):
        """测试初始化加载内置帮助."""
        hs = HelpSystem()
        commands = hs.list_commands()
        assert "read" in commands
        assert "query" in commands
        assert "edit" in commands
        assert "delete" in commands
        assert "add" in commands
        assert "diff" in commands
        assert "schema" in commands
        assert "help" in commands
        assert "explain" in commands
        assert "wiki" in commands

    def test_get_brief_help_structure(self):
        """测试简洁帮助结构."""
        hs = HelpSystem()
        brief = hs.get_brief_help()

        assert "tool" in brief
        assert "description" in brief
        assert "commands" in brief
        assert "global_options" in brief
        assert brief["tool"] == "wow-dbc-tool"

    def test_get_brief_help_commands(self):
        """测试简洁帮助包含所有命令."""
        hs = HelpSystem()
        brief = hs.get_brief_help()
        command_names = [c["name"] for c in brief["commands"]]
        assert "read" in command_names
        assert "explain" in command_names
        assert "wiki" in command_names

    def test_get_command_help_valid(self):
        """测试获取有效命令帮助."""
        hs = HelpSystem()
        help_data = hs.get_command_help("read")

        assert help_data is not None
        assert help_data["command"] == "read"
        assert "description" in help_data
        assert "args" in help_data
        assert "examples" in help_data
        assert "notes" in help_data

    def test_get_command_help_invalid(self):
        """测试获取无效命令帮助."""
        hs = HelpSystem()
        help_data = hs.get_command_help("nonexistent")
        assert help_data is None

    def test_get_full_help_structure(self):
        """测试完整帮助结构."""
        hs = HelpSystem()
        full = hs.get_full_help()

        assert "tool" in full
        assert "description" in full
        assert "commands" in full
        assert "global_options" in full
        assert "usage_tips" in full

    def test_get_full_help_commands_detail(self):
        """测试完整帮助包含详细命令信息."""
        hs = HelpSystem()
        full = hs.get_full_help()
        read_cmd = next(c for c in full["commands"] if c["name"] == "read")

        assert "brief" in read_cmd
        assert "description" in read_cmd
        assert "args" in read_cmd
        assert "examples" in read_cmd
        assert "notes" in read_cmd

    def test_list_commands(self):
        """测试列出命令."""
        hs = HelpSystem()
        commands = hs.list_commands()
        assert isinstance(commands, list)
        assert len(commands) >= 10

    def test_all_commands_have_brief(self):
        """测试所有命令都有简介."""
        hs = HelpSystem()
        brief = hs.get_brief_help()
        for cmd in brief["commands"]:
            assert cmd["brief"] != ""

    def test_all_commands_have_examples(self):
        """测试所有命令都有示例."""
        hs = HelpSystem()
        full = hs.get_full_help()
        for cmd in full["commands"]:
            assert len(cmd["examples"]) > 0

    def test_help_command_self_reference(self):
        """测试 help 命令帮助包含自身."""
        hs = HelpSystem()
        help_data = hs.get_command_help("help")
        assert help_data is not None
        assert "帮助" in help_data["description"]

    def test_explain_command_help(self):
        """测试 explain 命令帮助."""
        hs = HelpSystem()
        help_data = hs.get_command_help("explain")
        assert help_data is not None
        assert "说明" in help_data["description"]

    def test_wiki_command_help(self):
        """测试 wiki 命令帮助."""
        hs = HelpSystem()
        help_data = hs.get_command_help("wiki")
        assert help_data is not None
        assert "Wiki" in help_data["description"]
