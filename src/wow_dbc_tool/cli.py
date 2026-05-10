"""CLI 入口 - 命令行接口."""

import argparse
import contextlib
import json
import sys
from pathlib import Path
from typing import Any

from wow_dbc_tool.core.dbc_file import DBCFile
from wow_dbc_tool.core.exceptions import DBCError
from wow_dbc_tool.diff.engine import DBCDiff
from wow_dbc_tool.schema.registry import SchemaRegistry


class _JSONEncoder(json.JSONEncoder):
    """自定义 JSON 编码器，处理 NaN/Inf 等特殊浮点值."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, float):
            if obj != obj:  # NaN
                return None
            if obj == float("inf"):
                return None
            if obj == float("-inf"):
                return None
        return super().default(obj)

    def encode(self, obj: Any) -> str:
        """重写 encode 以处理 JSON 默认不支持的 NaN/Inf."""
        # 预处理对象，将 NaN/Inf 替换为 None
        obj = self._sanitize_floats(obj)
        return super().encode(obj)

    def _sanitize_floats(self, obj: Any) -> Any:
        """递归清理浮点特殊值."""
        if isinstance(obj, float):
            if obj != obj or obj == float("inf") or obj == float("-inf"):
                return None
            return obj
        elif isinstance(obj, dict):
            return {k: self._sanitize_floats(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._sanitize_floats(item) for item in obj]
        return obj


def _output_json(data: dict, pretty: bool = True) -> None:
    """输出 JSON 数据."""
    encoded = _JSONEncoder(indent=2, ensure_ascii=False).encode(data)
    if isinstance(encoded, bytes):
        encoded = encoded.decode("utf-8")
    print(encoded)


def _error_json(message: str, error_type: str = "DBCError") -> None:
    """输出错误 JSON."""
    data = {
        "error": True,
        "type": error_type,
        "message": message,
    }
    print(json.dumps(data, indent=2, ensure_ascii=False), file=sys.stderr)


def _parse_filters(filter_args: list[str]) -> dict[str, Any]:
    """解析 --filter 参数.

    格式: ID=123 或 ID__gt=100
    """
    filters: dict[str, Any] = {}
    for arg in filter_args:
        if "=" not in arg:
            raise ValueError(f"无效的 filter 格式: {arg}")
        key, value = arg.split("=", 1)

        # 尝试类型转换
        try:
            value = int(value)
        except ValueError:
            try:
                value = float(value)
            except ValueError:
                pass  # 保持字符串

        filters[key] = value
    return filters


def _parse_fields(field_args: list[str]) -> dict[str, Any]:
    """解析 --field 参数."""
    fields: dict[str, Any] = {}
    for arg in field_args:
        if "=" not in arg:
            raise ValueError(f"无效的 field 格式: {arg}")
        key, value = arg.split("=", 1)

        # 尝试类型转换
        try:
            value = int(value)
        except ValueError:
            with contextlib.suppress(ValueError):
                value = float(value)

        fields[key] = value
    return fields


def cmd_read(args: argparse.Namespace) -> int:
    """read 子命令."""
    dbc = DBCFile(args.file)
    if args.schema:
        SchemaRegistry.load_from_file(args.schema)
    dbc.load()

    records = dbc.to_json()
    if args.limit:
        records = records[: args.limit]

    data = {
        "file": str(args.file),
        "header": dbc.header.to_dict(),
        "records": records,
    }
    _output_json(data, pretty=not args.compact)
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    """query 子命令."""
    dbc = DBCFile(args.file)
    if args.schema:
        SchemaRegistry.load_from_file(args.schema)
    dbc.load()

    filters = _parse_filters(args.filter)
    records = dbc.query(**filters)

    data = {
        "file": str(args.file),
        "filters": filters,
        "count": len(records),
        "records": [r.to_dict() for r in records],
    }
    _output_json(data, pretty=not args.compact)
    return 0


def cmd_edit(args: argparse.Namespace) -> int:
    """edit 子命令."""
    dbc = DBCFile(args.file)
    if args.schema:
        SchemaRegistry.load_from_file(args.schema)
    dbc.load()

    filters = _parse_filters(args.filter)
    changes = _parse_fields(args.set)

    records = dbc.query(**filters)
    for record in records:
        dbc.edit(record, **changes)

    output_path = args.output or args.file
    dbc.save(output_path)

    data = {
        "file": str(args.file),
        "output": str(output_path),
        "filters": filters,
        "changes": changes,
        "modified": len(records),
        "records": [r.to_dict() for r in records],
    }
    _output_json(data, pretty=not args.compact)
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    """delete 子命令."""
    dbc = DBCFile(args.file)
    if args.schema:
        SchemaRegistry.load_from_file(args.schema)
    dbc.load()

    filters = _parse_filters(args.filter)
    deleted = dbc.delete(**filters)

    output_path = args.output or args.file
    dbc.save(output_path)

    data = {
        "file": str(args.file),
        "output": str(output_path),
        "filters": filters,
        "deleted": deleted,
        "remaining": len(dbc.records),
    }
    _output_json(data, pretty=not args.compact)
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    """add 子命令."""
    dbc = DBCFile(args.file)
    if args.schema:
        SchemaRegistry.load_from_file(args.schema)
    dbc.load()

    values = _parse_fields(args.field)
    record = dbc.add(**values)

    output_path = args.output or args.file
    dbc.save(output_path)

    data = {
        "file": str(args.file),
        "output": str(output_path),
        "added": 1,
        "new_record": record.to_dict(),
    }
    _output_json(data, pretty=not args.compact)
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    """diff 子命令."""
    # 先加载 schema（如果指定）
    schema = None
    if args.schema:
        SchemaRegistry.load_from_file(args.schema)
        # 获取加载的 schema（第一个自定义定义）
        custom_names = [name for name in SchemaRegistry.list_all() if name not in SchemaRegistry.list_builtins()]
        if custom_names:
            schema = SchemaRegistry.get(custom_names[0])

    old = DBCFile(args.file1, schema=schema)
    new = DBCFile(args.file2, schema=schema)
    old.load()
    new.load()

    differ = DBCDiff(old, new, key_field=args.key_field)

    report = differ.compare_by_index() if args.by_index else differ.compare()

    _output_json(report.to_dict(), pretty=not args.compact)
    return 0


def cmd_schema(args: argparse.Namespace) -> int:
    """schema 子命令."""
    if args.schema_command == "list":
        builtins = SchemaRegistry.list_builtins()
        custom = [name for name in SchemaRegistry.list_all() if name not in builtins]
        data = {
            "builtins": builtins,
            "custom": custom,
        }
        _output_json(data, pretty=not args.compact)

    elif args.schema_command == "show":
        dbc_name = Path(args.file).name
        schema = SchemaRegistry.get(dbc_name)
        if schema is None:
            _error_json(f"未找到 {dbc_name} 的字段定义", "DBCSchemaError")
            return 1
        data = {
            "file": dbc_name,
            "fields": [f.to_dict() for f in schema],
        }
        _output_json(data, pretty=not args.compact)

    elif args.schema_command == "infer":
        dbc = DBCFile(args.file)
        dbc.load()
        schema = dbc.schema
        data = {
            "file": str(args.file),
            "fields": [f.to_dict() for f in schema],
        }
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        _output_json(data, pretty=not args.compact)

    elif args.schema_command == "validate":
        dbc = DBCFile(args.file)
        if args.schema_file:
            SchemaRegistry.load_from_file(args.schema_file)
        dbc.load()
        schema = dbc.schema
        header = dbc.header

        errors = []
        warnings = []

        if header:
            expected_size = header.field_count * 4
            if header.record_size != expected_size:
                errors.append(f"记录大小不匹配: {header.record_size} != {expected_size}")

            if len(schema) != header.field_count:
                warnings.append(
                    f"字段定义数量 ({len(schema)}) 与文件头 " f"({header.field_count}) 不一致"
                )

        data = {
            "file": str(args.file),
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
        _output_json(data, pretty=not args.compact)

    return 0


def _add_common_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """为子命令添加通用参数."""
    parser.add_argument("--json", action="store_true", help="JSON 输出（默认美化）")
    parser.add_argument("--compact", action="store_true", help="紧凑 JSON 输出（无缩进）")
    parser.add_argument("--schema", type=Path, help="指定字段定义文件")
    parser.add_argument("--output", "-o", type=Path, help="输出到文件")
    return parser


def main() -> int:
    """CLI 主入口."""
    parser = argparse.ArgumentParser(
        prog="wow-dbc-tool",
        description="魔兽世界 3.3.5 DBC 文件操作工具",
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # read
    read_parser = _add_common_args(subparsers.add_parser("read", help="读取 DBC 文件"))
    read_parser.add_argument("file", type=Path, help="DBC 文件路径")
    read_parser.add_argument("--limit", type=int, help="限制输出条数")
    read_parser.set_defaults(func=cmd_read)

    # query
    query_parser = _add_common_args(subparsers.add_parser("query", help="查询记录"))
    query_parser.add_argument("file", type=Path, help="DBC 文件路径")
    query_parser.add_argument("--filter", action="append", default=[], help="过滤条件")
    query_parser.set_defaults(func=cmd_query)

    # edit
    edit_parser = _add_common_args(subparsers.add_parser("edit", help="修改记录"))
    edit_parser.add_argument("file", type=Path, help="DBC 文件路径")
    edit_parser.add_argument(
        "--filter", action="append", default=[], required=True, help="过滤条件"
    )
    edit_parser.add_argument(
        "--set", action="append", default=[], required=True, help="要修改的字段"
    )
    edit_parser.set_defaults(func=cmd_edit)

    # delete
    delete_parser = _add_common_args(subparsers.add_parser("delete", help="删除记录"))
    delete_parser.add_argument("file", type=Path, help="DBC 文件路径")
    delete_parser.add_argument(
        "--filter", action="append", default=[], required=True, help="过滤条件"
    )
    delete_parser.set_defaults(func=cmd_delete)

    # add
    add_parser = _add_common_args(subparsers.add_parser("add", help="添加记录"))
    add_parser.add_argument("file", type=Path, help="DBC 文件路径")
    add_parser.add_argument("--field", action="append", default=[], required=True, help="字段值")
    add_parser.set_defaults(func=cmd_add)

    # diff
    diff_parser = _add_common_args(subparsers.add_parser("diff", help="对比两个 DBC 文件"))
    diff_parser.add_argument("file1", type=Path, help="旧 DBC 文件")
    diff_parser.add_argument("file2", type=Path, help="新 DBC 文件")
    diff_parser.add_argument("--key-field", default="ID", help="主键字段")
    diff_parser.add_argument("--by-index", action="store_true", help="按索引对比")
    diff_parser.set_defaults(func=cmd_diff)

    # schema
    schema_parser = _add_common_args(subparsers.add_parser("schema", help="字段定义管理"))
    schema_parser.add_argument(
        "schema_command",
        choices=["list", "show", "infer", "validate"],
        help="schema 子命令",
    )
    schema_parser.add_argument("file", type=Path, nargs="?", help="DBC 文件路径")
    schema_parser.add_argument("--schema-file", type=Path, help="字段定义文件")
    schema_parser.set_defaults(func=cmd_schema)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        return args.func(args)
    except DBCError as e:
        _error_json(str(e), type(e).__name__)
        return 1
    except FileNotFoundError as e:
        _error_json(str(e), "FileNotFoundError")
        return 1
    except Exception as e:
        _error_json(str(e), type(e).__name__)
        return 1


if __name__ == "__main__":
    sys.exit(main())
