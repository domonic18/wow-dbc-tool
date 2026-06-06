"""帮助系统 - 分级帮助管理.

提供三级帮助输出：
- Level 1 (--help): 简洁模式（命令列表 + 基本用法）
- Level 2 (<command> --help): 子命令详细帮助
- Level 3 (--help-full): 完整模式（含示例、常见用例）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CommandHelp:
    """子命令帮助信息."""

    name: str
    brief: str = ""  # 一句话说明
    description: str = ""  # 详细描述
    args: list[dict[str, Any]] = field(default_factory=list)  # 参数列表
    examples: list[str] = field(default_factory=list)  # 示例
    notes: list[str] = field(default_factory=list)  # 注意事项


class HelpSystem:
    """分级帮助系统.

    管理所有帮助文本，支持分级输出和 JSON 格式。
    帮助文本内嵌在代码中，不依赖外部文件。
    """

    def __init__(self) -> None:
        """初始化帮助系统."""
        self._commands: dict[str, CommandHelp] = {}
        self._global_options: list[dict[str, Any]] = []
        self._tool_description = ""
        self._usage_tips: list[str] = []
        self._load_builtin_helps()

    def _load_builtin_helps(self) -> None:
        """加载内置帮助文本."""
        self._tool_description = (
            "wow-dbc-tool: 魔兽世界 3.3.5 DBC 文件操作工具\n"
            "支持读取、查询、编辑、删除、添加记录以及 Diff 对比、字段定义查询。"
        )

        self._global_options = [
            {"name": "--json", "type": "flag", "help": "JSON 输出（默认美化）"},
            {"name": "--compact", "type": "flag", "help": "紧凑 JSON 输出（无缩进）"},
            {"name": "--schema", "type": "Path", "help": "指定字段定义文件"},
            {"name": "--output, -o", "type": "Path", "help": "输出到文件"},
        ]

        self._usage_tips = [
            "所有命令默认输出 JSON，便于 Agent 消费",
            "使用 --compact 获取紧凑 JSON",
            "使用 --schema 指定自定义字段定义",
            "使用 --help-full 查看完整帮助和示例",
        ]

        # read 命令
        self._commands["read"] = CommandHelp(
            name="read",
            brief="读取 DBC 文件内容",
            description="读取 DBC 文件并输出所有记录。支持限制输出条数和指定字段定义。",
            args=[
                {"name": "file", "type": "Path", "required": True, "help": "DBC 文件路径"},
                {"name": "--limit", "type": "int", "required": False, "help": "限制输出条数"},
                {"name": "--schema", "type": "Path", "required": False, "help": "字段定义文件"},
            ],
            examples=[
                "wow-dbc-tool read Spell.dbc",
                "wow-dbc-tool read Spell.dbc --limit 10 --compact",
            ],
            notes=["默认输出 JSON 格式", "大文件建议配合 --limit 使用"],
        )

        # query 命令
        self._commands["query"] = CommandHelp(
            name="query",
            brief="查询记录",
            description="根据过滤条件查询 DBC 记录。支持等值过滤和比较操作符。",
            args=[
                {"name": "file", "type": "Path", "required": True, "help": "DBC 文件路径"},
                {
                    "name": "--filter",
                    "type": "str",
                    "required": False,
                    "help": "过滤条件（如 ID=123 或 ID__gt=100）",
                },
                {"name": "--schema", "type": "Path", "required": False, "help": "字段定义文件"},
            ],
            examples=[
                "wow-dbc-tool query Spell.dbc --filter ID=133",
                "wow-dbc-tool query Spell.dbc --filter ID__gt=100 --compact",
            ],
            notes=["支持 __gt, __lt, __gte, __lte, __ne 操作符", "多个 --filter 为 AND 关系"],
        )

        # edit 命令
        self._commands["edit"] = CommandHelp(
            name="edit",
            brief="修改记录",
            description="根据过滤条件查找并修改记录字段值。",
            args=[
                {"name": "file", "type": "Path", "required": True, "help": "DBC 文件路径"},
                {"name": "--filter", "type": "str", "required": True, "help": "过滤条件"},
                {
                    "name": "--set",
                    "type": "str",
                    "required": True,
                    "help": "要修改的字段（如 Name=NewName）",
                },
                {
                    "name": "--output, -o",
                    "type": "Path",
                    "required": False,
                    "help": "输出到文件（默认覆盖原文件）",
                },
            ],
            examples=[
                'wow-dbc-tool edit Spell.dbc --filter ID=133 --set Name="New Spell"',
            ],
            notes=["修改后会自动保存", "建议先备份原文件"],
        )

        # delete 命令
        self._commands["delete"] = CommandHelp(
            name="delete",
            brief="删除记录",
            description="根据过滤条件删除记录。",
            args=[
                {"name": "file", "type": "Path", "required": True, "help": "DBC 文件路径"},
                {"name": "--filter", "type": "str", "required": True, "help": "过滤条件"},
                {"name": "--output, -o", "type": "Path", "required": False, "help": "输出到文件"},
            ],
            examples=[
                "wow-dbc-tool delete Spell.dbc --filter ID=133",
            ],
            notes=["删除操作不可逆", "建议先备份原文件"],
        )

        # add 命令
        self._commands["add"] = CommandHelp(
            name="add",
            brief="添加记录",
            description="向 DBC 文件添加新记录。",
            args=[
                {"name": "file", "type": "Path", "required": True, "help": "DBC 文件路径"},
                {
                    "name": "--field",
                    "type": "str",
                    "required": True,
                    "help": '字段值（如 ID=999 Name="New")',
                },
                {"name": "--output, -o", "type": "Path", "required": False, "help": "输出到文件"},
            ],
            examples=[
                'wow-dbc-tool add Spell.dbc --field ID=999 --field Name="Custom Spell"',
            ],
            notes=["需要指定所有必填字段", "ID 不能与现有记录重复"],
        )

        # diff 命令
        self._commands["diff"] = CommandHelp(
            name="diff",
            brief="对比两个 DBC 文件",
            description="对比两个 DBC 文件的差异，输出新增、删除、修改的记录。",
            args=[
                {"name": "file1", "type": "Path", "required": True, "help": "旧 DBC 文件"},
                {"name": "file2", "type": "Path", "required": True, "help": "新 DBC 文件"},
                {
                    "name": "--key-field",
                    "type": "str",
                    "required": False,
                    "help": "主键字段（默认 ID）",
                },
                {"name": "--by-index", "type": "flag", "required": False, "help": "按索引对比"},
            ],
            examples=[
                "wow-dbc-tool diff Spell_old.dbc Spell_new.dbc",
                "wow-dbc-tool diff Spell_old.dbc Spell_new.dbc --key-field ID --compact",
            ],
            notes=["默认按主键对比", "--by-index 按记录顺序对比"],
        )

        # schema 命令
        self._commands["schema"] = CommandHelp(
            name="schema",
            brief="字段定义管理",
            description="管理 DBC 字段定义：列出、查看、推断、验证、生成。",
            args=[
                {
                    "name": "schema_command",
                    "type": "str",
                    "required": True,
                    "help": "子命令: list, show, infer, validate, generate",
                },
                {"name": "file", "type": "Path", "required": False, "help": "DBC 文件路径"},
                {
                    "name": "--schema-file",
                    "type": "Path",
                    "required": False,
                    "help": "字段定义文件",
                },
                {"name": "--output, -o", "type": "Path", "required": False, "help": "输出到文件"},
            ],
            examples=[
                "wow-dbc-tool schema list",
                "wow-dbc-tool schema show Spell.dbc",
                "wow-dbc-tool schema infer Spell.dbc",
                "wow-dbc-tool schema validate Spell.dbc",
                "wow-dbc-tool schema generate",
                "wow-dbc-tool schema generate --table Spell",
            ],
            notes=["list 不需要 file 参数", "infer 从文件结构推断字段定义", "generate 从 CSV + WoWDBDefs 生成 schema"],
        )

        # help 命令
        self._commands["help"] = CommandHelp(
            name="help",
            brief="显示帮助信息",
            description="显示分级帮助信息。支持简洁帮助、子命令帮助和完整帮助。",
            args=[
                {"name": "command", "type": "str", "required": False, "help": "子命令名称（可选）"},
                {"name": "--full", "type": "flag", "required": False, "help": "显示完整帮助"},
            ],
            examples=[
                "wow-dbc-tool help",
                "wow-dbc-tool help read",
                "wow-dbc-tool help --full",
            ],
            notes=["不带参数显示简洁帮助", "--full 显示所有命令详细说明"],
        )

        # explain 命令
        self._commands["explain"] = CommandHelp(
            name="explain",
            brief="查询 DBC 说明",
            description="查询 DBC 文件或字段的说明文档。",
            args=[
                {"name": "dbc_name", "type": "str", "required": True, "help": "DBC 文件名"},
                {"name": "--field", "type": "str", "required": False, "help": "查询特定字段"},
            ],
            examples=[
                "wow-dbc-tool explain Spell.dbc",
                "wow-dbc-tool explain Spell.dbc --field Name",
            ],
            notes=["需要本地有文档定义"],
        )

    def get_brief_help(self) -> dict[str, Any]:
        """获取简洁帮助（Level 1）.

        Returns:
            JSON 可序列化的帮助信息
        """
        return {
            "tool": "wow-dbc-tool",
            "description": self._tool_description,
            "commands": [{"name": cmd.name, "brief": cmd.brief} for cmd in self._commands.values()],
            "global_options": self._global_options,
        }

    def get_command_help(self, command: str) -> dict[str, Any] | None:
        """获取子命令帮助（Level 2）.

        Args:
            command: 子命令名称

        Returns:
            帮助信息，命令不存在返回 None
        """
        cmd = self._commands.get(command)
        if cmd is None:
            return None

        return {
            "command": cmd.name,
            "description": cmd.description,
            "args": cmd.args,
            "examples": cmd.examples,
            "notes": cmd.notes,
        }

    def get_full_help(self) -> dict[str, Any]:
        """获取完整帮助（Level 3）.

        Returns:
            JSON 可序列化的完整帮助信息
        """
        return {
            "tool": "wow-dbc-tool",
            "description": self._tool_description,
            "commands": [
                {
                    "name": cmd.name,
                    "brief": cmd.brief,
                    "description": cmd.description,
                    "args": cmd.args,
                    "examples": cmd.examples,
                    "notes": cmd.notes,
                }
                for cmd in self._commands.values()
            ],
            "global_options": self._global_options,
            "usage_tips": self._usage_tips,
        }

    def list_commands(self) -> list[str]:
        """列出所有支持的命令.

        Returns:
            命令名称列表
        """
        return list(self._commands.keys())
