"""CLI 入口 - 命令行接口."""

import argparse
import contextlib
import csv
import json
import sys
from pathlib import Path
from typing import Any, cast

from wow_dbc_tool.core.dbc_file import DBCFile
from wow_dbc_tool.core.exceptions import DBCError
from wow_dbc_tool.diff.engine import DBCDiff
from wow_dbc_tool.schema.field_def import FieldDef
from wow_dbc_tool.schema.registry import SchemaRegistry
from wow_dbc_tool.utils.doc_store import DocStore
from wow_dbc_tool.utils.help_system import HelpSystem


# 类型映射：将 generate-schemas.py 生成的类型转换为 wow-dbc-tool 支持的类型
SCHEMA_TYPE_MAP = {
    "int": "int32",
    "uint": "uint32",
    "float": "float",
    "string": "string",
    "locstring": "string",
}


def _load_json_schema(schema_path: Path) -> list[FieldDef]:
    """从 generate-schemas.py 生成的 JSON schema 文件加载字段定义.

    输入格式:
    {
        "field_order": ["ID", "Name", ...],
        "properties": {
            "ID": {"type": "int", ...},
            "Name": {"type": "locstring", ...},
            ...
        }
    }
    """
    with open(schema_path, encoding="utf-8") as f:
        data = json.load(f)

    field_order = data.get("field_order", [])
    properties = data.get("properties", {})

    fields: list[FieldDef] = []
    for i, name in enumerate(field_order):
        prop = properties.get(name, {})
        raw_type = prop.get("type", "int32")
        field_type = SCHEMA_TYPE_MAP.get(raw_type, raw_type)
        # 如果映射后仍然不支持，回退为 int32
        if field_type not in FieldDef.VALID_TYPES:
            field_type = "int32"
        fields.append(FieldDef(name, field_type, i * 4))

    return fields


def _auto_load_project_schema(dbc_path: Path) -> list[FieldDef] | None:
    """自动查找并加载对应 schema.

    查找路径（按优先级）:
    1. 工具自身的 schemas/ 目录（tools/wow-dbc-tool/schemas/）
    2. DBC 文件同级目录下的 .schema.json
    3. 项目根目录下的 tools/wow-dbc-tool/schemas/{name}.schema.json
    4. 兼容旧路径：src/schemas/{name}.schema.json
    """
    dbc_name = dbc_path.name
    schema_name = dbc_name.replace(".dbc", ".schema.json")

    # 1. 工具自身的 schemas/ 目录
    # cli.py 位于 tools/wow-dbc-tool/src/wow_dbc_tool/cli.py
    tool_schemas_dir = Path(__file__).parent.parent.parent / "schemas"

    candidates = [
        tool_schemas_dir / schema_name,
        # 2. DBC 同级目录
        dbc_path.parent / schema_name,
    ]

    # 3. 向上查找项目根目录下的 tools/wow-dbc-tool/schemas/
    # 4. 兼容旧路径 src/schemas/
    project_root = dbc_path.parent
    for _ in range(6):
        candidates.append(project_root / "tools" / "wow-dbc-tool" / "schemas" / schema_name)
        candidates.append(project_root / "src" / "schemas" / schema_name)
        project_root = project_root.parent
        if len(str(project_root)) <= 3:
            break

    for candidate in candidates:
        if candidate.exists():
            print(f"  自动加载 schema: {candidate}")
            return _load_json_schema(candidate)

    return None


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
        key, raw_value = arg.split("=", 1)
        value: int | float | str = raw_value

        # 尝试类型转换
        try:
            value = int(raw_value)
        except ValueError:
            with contextlib.suppress(ValueError):
                value = float(raw_value)

        filters[key] = value
    return filters


def _parse_fields(field_args: list[str]) -> dict[str, Any]:
    """解析 --field 参数."""
    fields: dict[str, Any] = {}
    for arg in field_args:
        if "=" not in arg:
            raise ValueError(f"无效的 field 格式: {arg}")
        key, raw_value = arg.split("=", 1)
        value: int | float | str = raw_value

        # 尝试类型转换
        try:
            value = int(raw_value)
        except ValueError:
            with contextlib.suppress(ValueError):
                value = float(raw_value)

        fields[key] = value
    return fields


def _read_csv_header(csv_path: Path) -> list[str]:
    """读取 CSV 文件的第一行（列名）."""
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        return next(reader)


def _format_value(value: Any) -> str:
    """将字段值格式化为 CSV 字符串."""
    if value is None:
        return ""
    if isinstance(value, float):
        s = f"{value:.6f}"
        s = s.rstrip("0").rstrip(".")
        return s
    return str(value)


def cmd_export(args: argparse.Namespace) -> int:
    """export 子命令 - 将 DBC 导出为 CSV."""
    # 优先尝试自动加载项目中的 JSON schema
    project_schema = None
    if args.schema:
        # 如果用户指定了 schema 文件
        project_schema = _load_json_schema(args.schema)
    else:
        # 自动从项目 schemas 目录查找
        project_schema = _auto_load_project_schema(args.file)

    if project_schema:
        dbc = DBCFile(args.file, schema=project_schema)
    else:
        dbc = DBCFile(args.file)
        if args.schema:
            SchemaRegistry.load_from_file(args.schema)
    dbc.load()

    if not dbc.records:
        print(f"警告: {args.file} 中没有记录", file=sys.stderr)
        return 0

    # 获取 schema 字段定义列表（按 DBC 中物理顺序）
    schema_fields = dbc.schema
    if not schema_fields:
        print(f"错误: 无法获取字段定义", file=sys.stderr)
        return 1

    # 确定导出的列名
    if args.keep_header:
        # 读取现有 CSV 的 header，保留其列名
        csv_headers = _read_csv_header(args.keep_header)
        print(f"保留 CSV 列名: {len(csv_headers)} 列")
    else:
        # 使用 DBC schema 中的字段名作为列名
        csv_headers = [f.name for f in schema_fields]

    # 确定实际导出的字段数（取 CSV列数 和 DBC字段数 的最小值）
    dbc_field_count = len(schema_fields)
    export_count = min(len(csv_headers), dbc_field_count)

    if len(csv_headers) != dbc_field_count:
        print(
            f"注意: CSV列数({len(csv_headers)}) 与 DBC字段数({dbc_field_count}) 不一致，"
            f"只导出前 {export_count} 列",
            file=sys.stderr,
        )

    # 生成 CSV 行：按 schema 顺序获取字段值
    # 第 i 个 schema 字段 -> CSV 第 i 列
    csv_rows = []
    for record in dbc.records:
        row = []
        for i in range(export_count):
            field_name = schema_fields[i].name
            try:
                value = record.get(field_name)
            except Exception:
                value = ""
            row.append(_format_value(value))
        csv_rows.append(row)

    # 输出
    # 使用与原始 CSV 一致的格式：
    # - 所有字段用双引号包裹 (QUOTE_ALL)
    # - 使用 LF 换行符 (与 Git 中旧 CSV 一致)
    # - 空字符串输出为 ""
    csv_kwargs = {
        "quoting": csv.QUOTE_ALL,
        "lineterminator": "\n",
    }

    output_path = args.output
    if output_path:
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, **csv_kwargs)
            writer.writerow(csv_headers[:export_count])
            writer.writerows(csv_rows)
        print(f"已导出 {len(csv_rows)} 条记录到: {output_path}")
    else:
        # 输出到 stdout
        writer = csv.writer(sys.stdout, **csv_kwargs)
        writer.writerow(csv_headers[:export_count])
        writer.writerows(csv_rows)

    return 0


def cmd_read(args: argparse.Namespace) -> int:
    """read 子命令."""
    dbc = DBCFile(args.file)
    if args.schema:
        SchemaRegistry.load_from_file(args.schema)
    dbc.load()
    assert dbc.header is not None

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
        custom_names = [
            name for name in SchemaRegistry.list_all() if name not in SchemaRegistry.list_builtins()
        ]
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
    data: dict[str, Any]
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

        errors: list[str] = []
        warnings: list[str] = []

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

    elif args.schema_command == "generate":
        from wow_dbc_tool.schema.generator import generate_schemas

        csv_dir = args.csv_dir or Path("tables")
        dbd_dir = args.dbd_dir or (
            Path(__file__).parent.parent.parent / "third-party" / "WoWDBDefs" / "definitions"
        )
        output_dir = args.output or (Path(__file__).parent.parent.parent / "schemas")
        tables = [args.table] if args.table else None

        if not dbd_dir.exists():
            _error_json(f"WoWDBDefs 未找到: {dbd_dir}", "FileNotFoundError")
            return 1

        result = generate_schemas(
            csv_dir=csv_dir,
            dbd_dir=dbd_dir,
            output_dir=output_dir,
            tables=tables,
            target_version=args.target_version,
        )
        _output_json(result, pretty=not args.compact)

    return 0


def cmd_help(args: argparse.Namespace) -> int:
    """help 子命令."""
    help_system = HelpSystem()
    data: dict[str, Any] | None

    if args.full:
        data = help_system.get_full_help()
    elif args.command_name:
        data = help_system.get_command_help(args.command_name)
        if data is None:
            _error_json(f"未知命令: {args.command_name}", "HelpError")
            return 1
    else:
        data = help_system.get_brief_help()

    _output_json(data, pretty=not args.compact)
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    """explain 子命令."""
    store = DocStore()
    entry = store.get(args.dbc_name)

    if entry is None:
        _error_json(
            f"未找到 {args.dbc_name} 的说明文档。",
            "DocError",
        )
        return 1

    if args.field:
        # 查询特定字段
        results = {}
        not_found = []
        for field_name in args.field:
            found = None
            for field in entry.fields:
                if field.get("name") == field_name:
                    found = field
                    break
            if found:
                results[field_name] = found
            else:
                not_found.append(field_name)

        data = {
            "dbc_name": args.dbc_name,
            "fields": results,
            "not_found": not_found,
        }
    else:
        # 查询整个文件
        data = {
            "dbc_name": entry.name,
            "title": entry.title,
            "overview": entry.overview,
            "field_count": entry.field_count,
            "record_size": entry.record_size,
            "source": entry.source,
            "last_sync": entry.last_sync,
            "fields_summary": [
                {
                    "name": f.get("name", ""),
                    "type": f.get("type", ""),
                    "offset": f.get("offset", 0),
                    "description": f.get("description", ""),
                }
                for f in entry.fields
            ],
            "examples": entry.examples,
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
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

    parser = argparse.ArgumentParser(
        prog="wow-dbc-tool",
        description="魔兽世界 3.3.5 DBC 文件操作工具",
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # export
    export_parser = subparsers.add_parser("export", help="导出 DBC 为 CSV")
    export_parser.add_argument("file", type=Path, help="DBC 文件路径")
    export_parser.add_argument(
        "--keep-header",
        type=Path,
        help="指定现有 CSV 文件，保留其列名（只导出 CSV 中已有的列）",
    )
    export_parser.add_argument("--output", "-o", type=Path, help="输出 CSV 文件路径")
    export_parser.add_argument("--schema", type=Path, help="指定字段定义文件")
    export_parser.set_defaults(func=cmd_export)

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
        choices=["list", "show", "infer", "validate", "generate"],
        help="schema 子命令",
    )
    schema_parser.add_argument("file", type=Path, nargs="?", help="DBC 文件路径")
    schema_parser.add_argument("--schema-file", type=Path, help="字段定义文件")
    schema_parser.add_argument("--csv-dir", type=Path, help="CSV 输入目录（generate 用）")
    schema_parser.add_argument("--dbd-dir", type=Path, help="WoWDBDefs 定义目录（generate 用）")
    schema_parser.add_argument("--table", type=str, help="仅生成指定表（generate 用）")
    schema_parser.add_argument("--target-version", type=str, default="3.3.5.12340", help="目标版本（generate 用，默认: 3.3.5.12340)")
    schema_parser.set_defaults(func=cmd_schema)

    # help
    help_parser = subparsers.add_parser("help", help="显示帮助信息")
    help_parser.add_argument("command_name", nargs="?", help="子命令名称（可选）")
    help_parser.add_argument("--full", action="store_true", help="显示完整帮助")
    help_parser.add_argument("--compact", action="store_true", help="紧凑 JSON")
    help_parser.set_defaults(func=cmd_help)

    # explain
    explain_parser = subparsers.add_parser("explain", help="查询 DBC 说明")
    explain_parser.add_argument("dbc_name", help="DBC 文件名")
    explain_parser.add_argument("--field", action="append", default=[], help="查询特定字段")
    explain_parser.add_argument("--compact", action="store_true", help="紧凑 JSON")
    explain_parser.set_defaults(func=cmd_explain)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        return cast(int, args.func(args))
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
