"""Schema 生成器 - 从 CSV + WoWDBDefs 生成物理字段定义.

由 CLI `schema generate` 子命令调用，也可独立使用。
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

# 字符串类型字段名模式（用于从 CSV header 推断字段类型）
STRING_FIELD_PATTERNS = [
    r"_Lang_",
    r"_lang_",
    r"^(ModelName|ModelTexture|InventoryIcon|Texture|PortraitTextureName)",
    r"^(TextureFilename|IconFilename)$",
    r"Name$",
]

DEFAULT_TARGET_VERSION = "3.3.5.12340"

# 3.3.5a locstring 展开的物理字段顺序（与现有 schema 保持一致）
LOCALE_ORDER = [
    "enUS",
    "enGB",
    "koKR",
    "frFR",
    "deDE",
    "enCN",
    "zhCN",
    "enTW",
    "zhTW",
    "esES",
    "esMX",
    "ruRU",
    "ptPT",
    "ptBR",
    "itIT",
    "Unk",
]


def _is_string_field(field_name: str) -> bool:
    return any(re.search(pattern, field_name, re.IGNORECASE) for pattern in STRING_FIELD_PATTERNS)


def _parse_build_version(version_str: str) -> tuple[int, ...]:
    parts = version_str.strip().split(".")
    return tuple(int(p) for p in parts)


def _version_in_range(target: tuple[int, ...], build_def: str) -> bool:
    content = build_def.replace("BUILD", "", 1).strip()
    if "-" in content:
        left, right = content.split("-", 1)
        left_ver = _parse_build_version(left)
        right_ver = _parse_build_version(right)
        return left_ver <= target <= right_ver
    if "," in content:
        versions = [v.strip() for v in content.split(",")]
        return any(_parse_build_version(v) == target for v in versions)
    return _parse_build_version(content) == target


def _parse_dbd_columns(content: str) -> dict[str, dict[str, str]]:
    """解析 .dbd 文件的 COLUMNS 部分."""
    columns: dict[str, dict[str, str]] = {}
    in_columns = False
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("BUILD", "LAYOUT", "COMMENT")):
            in_columns = False
            continue
        if stripped == "COLUMNS":
            in_columns = True
            continue
        if in_columns:
            comment_idx = stripped.find("//")
            if comment_idx >= 0:
                stripped = stripped[:comment_idx].strip()

            fk_match = re.match(r"(\w+)<(\w+)::(\w+)>\s+(\S+)", stripped)
            if fk_match:
                field_type = fk_match.group(1)
                name = fk_match.group(4)
            else:
                simple_match = re.match(r"(\w+)\s+(\S+)", stripped)
                if simple_match:
                    field_type = simple_match.group(1)
                    name = simple_match.group(2)
                else:
                    continue

            if name.endswith("?"):
                name = name[:-1]

            columns[name] = {"type": field_type, "name": name}
    return columns


def _find_dbd_path(dbd_dir: Path, table_name: str) -> Path | None:
    """查找 .dbd 文件，支持大小写不敏感匹配.

    在大小写不敏感文件系统上，直接调用 exists() 会返回 True 但路径中的
    文件名大小写可能与磁盘实际文件名不一致，因此通过 glob 列出的真实
    文件名进行匹配。
    """
    candidates = {p.name: p for p in dbd_dir.glob("*.dbd")}
    exact_name = f"{table_name}.dbd"
    if exact_name in candidates:
        return candidates[exact_name]

    lower_target = table_name.lower()
    for name, path in candidates.items():
        if Path(name).stem.lower() == lower_target:
            return path
    return None


def _get_dbd_columns_for_version(dbd_path: Path, target_version: str) -> dict[str, dict[str, str]]:
    if not dbd_path.exists():
        return {}
    with open(dbd_path, encoding="utf-8") as f:
        content = f.read()
    return _parse_dbd_columns(content)


def _parse_dbd_builds(content: str) -> list[dict[str, Any]]:
    """解析 .dbd 文件中的所有 BUILD 段.

    返回每个 BUILD 段的版本定义与字段声明列表。
    """
    builds: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue

        if stripped.startswith("BUILD"):
            if current is not None:
                builds.append(current)
            current = {"build_def": stripped, "declarations": []}
            continue

        if stripped in ("COLUMNS", "LAYOUT"):
            if current is not None:
                builds.append(current)
                current = None
            continue

        if current is not None:
            current["declarations"].append(stripped)

    if current is not None:
        builds.append(current)

    return builds


def _select_build(builds: list[dict[str, Any]], target_version: str) -> dict[str, Any] | None:
    """选择包含目标版本的 BUILD 段."""
    target = _parse_build_version(target_version)
    for build in builds:
        if _version_in_range(target, build["build_def"]):
            return build
    return None


def _width_to_type(width: str | None, column_type: str | None) -> str:
    """根据 BUILD 段宽度和 COLUMNS 类型确定物理字段类型."""
    if width == "u32":
        return "uint32"
    if width in ("u16", "u8"):
        return "uint32"
    if width == "32":
        if column_type == "float":
            return "float"
        if column_type == "uint":
            return "uint32"
        return "int32"
    if width == "8":
        return "int32"
    # 无显式宽度时回退到 COLUMNS 类型
    if column_type == "float":
        return "float"
    if column_type == "uint":
        return "uint32"
    if column_type == "string":
        return "string"
    if column_type == "locstring":
        return "string"
    return "int32"


def _expand_locstring(field_name: str) -> list[tuple[str, str]]:
    """展开 locstring 为 16 个语言字段 + 1 个 Mask 字段."""
    base = field_name.replace("_lang", "").replace("Lang", "")
    result: list[tuple[str, str]] = []
    for locale in LOCALE_ORDER:
        result.append((f"{base}_Lang_{locale}", "string"))
    result.append((f"{base}_Lang_Mask", "uint32"))
    return result


def _expand_array(field_name: str, count: int, field_type: str) -> list[tuple[str, str]]:
    """展开数组字段."""
    return [(f"{field_name}_{i}", field_type) for i in range(1, count + 1)]


_BUILD_DECL_RE = re.compile(
    r"^(?:\$id\$)?(?P<name>\w+)(?:<(?P<width>[^>]+)>)?(?:\[(?P<count>\d+)\])?$"
)


def _parse_build_declarations(
    declarations: list[str],
    columns: dict[str, dict[str, str]],
) -> list[tuple[str, str]]:
    """解析 BUILD 段字段声明，返回展开的物理字段列表.

    每个元素为 (field_name, field_type)。
    """
    fields: list[tuple[str, str]] = []
    for decl in declarations:
        match = _BUILD_DECL_RE.match(decl)
        if not match:
            continue

        name = match.group("name")
        width = match.group("width")
        count_str = match.group("count")
        count = int(count_str) if count_str else 1

        column_info = columns.get(name, {})
        column_type = column_info.get("type")

        if column_type == "locstring":
            expanded = _expand_locstring(name)
            if count > 1:
                # locstring 数组极为罕见，简单复制多组
                for _ in range(count):
                    fields.extend(expanded)
            else:
                fields.extend(expanded)
            continue

        field_type = _width_to_type(width, column_type)

        if count > 1:
            fields.extend(_expand_array(name, count, field_type))
        else:
            fields.append((name, field_type))

    return fields


def _expand_locstring_field(
    field_name: str, csv_headers: list[str], start_idx: int
) -> list[tuple[str, str]]:
    """从 CSV header 中识别 locstring 展开后的物理字段."""
    result: list[tuple[str, str]] = []
    base_name = field_name.replace("_lang", "").replace("Lang", "")

    for i in range(start_idx, len(csv_headers)):
        header = csv_headers[i]
        if (
            header.startswith(field_name)
            or header.startswith(field_name.replace("_lang", "_Lang"))
            or header.startswith(base_name)
            and "_Lang_" in header
        ):
            if "_Mask" in header:
                result.append((header, "int32"))
            else:
                result.append((header, "string"))
        else:
            break

    return result


def _generate_schema_from_build(
    table_name: str,
    dbd_path: Path,
    target_version: str,
) -> dict[str, Any] | None:
    """基于 .dbd BUILD 段生成 schema（无需 CSV）."""
    if not dbd_path.exists():
        return None

    content = dbd_path.read_text(encoding="utf-8")
    columns = _parse_dbd_columns(content)
    builds = _parse_dbd_builds(content)
    build = _select_build(builds, target_version)

    if not build:
        return None

    fields = _parse_build_declarations(build["declarations"], columns)

    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": f"{table_name} Physical Schema",
        "description": f"{table_name}.dbc 物理字段定义 (版本 {target_version})",
        "source": "https://github.com/wowdev/WoWDBDefs",
        "table_name": table_name,
        "version": target_version,
        "type": "object",
        "field_count": len(fields),
        "field_order": [f[0] for f in fields],
        "properties": {name: {"type": t, "offset": i * 4} for i, (name, t) in enumerate(fields)},
    }


def generate_physical_schema(
    table_name: str,
    csv_dir: Path | None,
    dbd_dir: Path,
    target_version: str = DEFAULT_TARGET_VERSION,
) -> dict[str, Any] | None:
    """生成与 DBC 物理结构完全一致的 schema.

    优先使用 .dbd 的 BUILD 段生成；若不可用则回退到 CSV + COLUMNS。

    Args:
        table_name: 表名（如 "Spell"）
        csv_dir: CSV 文件所在目录，None 时跳过 CSV 回退
        dbd_dir: WoWDBDefs .dbd 文件所在目录
        target_version: 目标版本号

    Returns:
        schema 字典，失败返回 None
    """
    dbd_path = _find_dbd_path(dbd_dir, table_name)

    # 优先使用 .dbd BUILD 段
    schema = _generate_schema_from_build(table_name, dbd_path, target_version) if dbd_path else None
    if schema is not None:
        return schema

    # 回退：CSV + COLUMNS
    if csv_dir is None:
        return None

    csv_path = csv_dir / f"{table_name}.csv"
    if not csv_path.exists():
        return None

    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        csv_headers = next(reader)

    dbd_columns = _get_dbd_columns_for_version(dbd_path, target_version) if dbd_path else {}

    fields: list[dict[str, Any]] = []
    csv_idx = 0

    if dbd_columns:
        for col_name, col_info in dbd_columns.items():
            if csv_idx >= len(csv_headers):
                break

            col_type = col_info["type"]

            if col_type == "locstring":
                expanded = _expand_locstring_field(col_name, csv_headers, csv_idx)
                if expanded:
                    for phys_name, phys_type in expanded:
                        fields.append({"name": phys_name, "type": phys_type, "offset": csv_idx * 4})
                        csv_idx += 1
                else:
                    fields.append(
                        {"name": csv_headers[csv_idx], "type": "string", "offset": csv_idx * 4}
                    )
                    csv_idx += 1
            elif col_type in ("int", "uint"):
                fields.append(
                    {
                        "name": csv_headers[csv_idx],
                        "type": "int32" if col_type == "int" else "uint32",
                        "offset": csv_idx * 4,
                    }
                )
                csv_idx += 1
            elif col_type == "float":
                fields.append(
                    {"name": csv_headers[csv_idx], "type": "float", "offset": csv_idx * 4}
                )
                csv_idx += 1
            elif col_type == "string":
                fields.append(
                    {"name": csv_headers[csv_idx], "type": "string", "offset": csv_idx * 4}
                )
                csv_idx += 1
            else:
                field_type = "string" if _is_string_field(csv_headers[csv_idx]) else "int32"
                fields.append(
                    {"name": csv_headers[csv_idx], "type": field_type, "offset": csv_idx * 4}
                )
                csv_idx += 1
    else:
        for i, header in enumerate(csv_headers):
            field_type = "string" if _is_string_field(header) else "int32"
            fields.append({"name": header, "type": field_type, "offset": i * 4})

    while csv_idx < len(csv_headers):
        header = csv_headers[csv_idx]
        field_type = "string" if _is_string_field(header) else "int32"
        fields.append({"name": header, "type": field_type, "offset": csv_idx * 4})
        csv_idx += 1

    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": f"{table_name} Physical Schema",
        "description": f"{table_name}.dbc 物理字段定义 (版本 {target_version})",
        "source": "https://github.com/wowdev/WoWDBDefs + CSV header",
        "table_name": table_name,
        "version": target_version,
        "type": "object",
        "field_count": len(fields),
        "field_order": [f["name"] for f in fields],
        "properties": {f["name"]: {"type": f["type"], "offset": f["offset"]} for f in fields},
    }


def generate_schemas(
    csv_dir: Path | None,
    dbd_dir: Path,
    output_dir: Path,
    tables: list[str] | None = None,
    target_version: str = DEFAULT_TARGET_VERSION,
    dbc_dir: Path | None = None,
) -> dict[str, Any]:
    """批量生成 schema 文件.

    Args:
        csv_dir: CSV 文件所在目录，None 时跳过 CSV 回退
        dbd_dir: WoWDBDefs .dbd 文件所在目录
        output_dir: 输出目录
        tables: 指定表名列表，None 时自动发现
        target_version: 目标版本号
        dbc_dir: 原始 DBC 文件目录；提供时按 DBC 文件名生成 schema，
                 并按大小写不敏感匹配查找 .dbd 定义

    Returns:
        {"generated": int, "failed": int, "total": int, "details": {table: bool}}
    """
    if not dbd_dir.exists():
        raise FileNotFoundError(f"WoWDBDefs 子模块未找到: {dbd_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    if tables is None:
        if dbc_dir is not None and dbc_dir.exists():
            tables = sorted([p.stem for p in dbc_dir.glob("*.dbc")])
        elif csv_dir is not None and csv_dir.exists():
            tables = sorted([p.stem for p in csv_dir.glob("*.csv")])
        else:
            tables = sorted([p.stem for p in dbd_dir.glob("*.dbd")])

    if not tables:
        raise ValueError(f"未在 {dbc_dir or csv_dir or dbd_dir} 找到输入文件")

    generated = 0
    failed = 0
    details: dict[str, bool] = {}

    for table_name in tables:
        schema = generate_physical_schema(table_name, csv_dir, dbd_dir, target_version)
        if schema:
            output_path = output_dir / f"{table_name}.schema.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(schema, f, ensure_ascii=False, indent=2)
            generated += 1
            details[table_name] = True
        else:
            failed += 1
            details[table_name] = False

    return {
        "generated": generated,
        "failed": failed,
        "total": len(tables),
        "details": details,
    }
