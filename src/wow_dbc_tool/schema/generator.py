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


def _get_dbd_columns_for_version(dbd_path: Path, target_version: str) -> dict[str, dict[str, str]]:
    if not dbd_path.exists():
        return {}
    with open(dbd_path, encoding="utf-8") as f:
        content = f.read()
    return _parse_dbd_columns(content)


def _expand_locstring_field(field_name: str, csv_headers: list[str], start_idx: int) -> list[tuple[str, str]]:
    """从 CSV header 中识别 locstring 展开后的物理字段."""
    result: list[tuple[str, str]] = []
    base_name = field_name.replace("_lang", "").replace("Lang", "")

    for i in range(start_idx, len(csv_headers)):
        header = csv_headers[i]
        if header.startswith(field_name) or header.startswith(field_name.replace("_lang", "_Lang")) or header.startswith(base_name) and "_Lang_" in header:
            if "_Mask" in header:
                result.append((header, "int32"))
            else:
                result.append((header, "string"))
        else:
            break

    return result


def generate_physical_schema(
    table_name: str,
    csv_dir: Path,
    dbd_dir: Path,
    target_version: str = DEFAULT_TARGET_VERSION,
) -> dict[str, Any] | None:
    """生成与 DBC 物理结构完全一致的 schema.

    Args:
        table_name: 表名（如 "Spell"）
        csv_dir: CSV 文件所在目录
        dbd_dir: WoWDBDefs .dbd 文件所在目录
        target_version: 目标版本号

    Returns:
        schema 字典，失败返回 None
    """
    csv_path = csv_dir / f"{table_name}.csv"
    dbd_path = dbd_dir / f"{table_name}.dbd"

    if not csv_path.exists():
        return None

    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        csv_headers = next(reader)

    dbd_columns = _get_dbd_columns_for_version(dbd_path, target_version)

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
                    fields.append({"name": csv_headers[csv_idx], "type": "string", "offset": csv_idx * 4})
                    csv_idx += 1
            elif col_type in ("int", "uint"):
                fields.append({
                    "name": csv_headers[csv_idx],
                    "type": "int32" if col_type == "int" else "uint32",
                    "offset": csv_idx * 4,
                })
                csv_idx += 1
            elif col_type == "float":
                fields.append({"name": csv_headers[csv_idx], "type": "float", "offset": csv_idx * 4})
                csv_idx += 1
            elif col_type == "string":
                fields.append({"name": csv_headers[csv_idx], "type": "string", "offset": csv_idx * 4})
                csv_idx += 1
            else:
                field_type = "string" if _is_string_field(csv_headers[csv_idx]) else "int32"
                fields.append({"name": csv_headers[csv_idx], "type": field_type, "offset": csv_idx * 4})
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
    csv_dir: Path,
    dbd_dir: Path,
    output_dir: Path,
    tables: list[str] | None = None,
    target_version: str = DEFAULT_TARGET_VERSION,
) -> dict[str, Any]:
    """批量生成 schema 文件.

    Args:
        csv_dir: CSV 文件所在目录
        dbd_dir: WoWDBDefs .dbd 文件所在目录
        output_dir: 输出目录
        tables: 指定表名列表，None 时从 csv_dir 自动发现
        target_version: 目标版本号

    Returns:
        {"generated": int, "failed": int, "total": int, "details": {table: bool}}
    """
    if not dbd_dir.exists():
        raise FileNotFoundError(f"WoWDBDefs 子模块未找到: {dbd_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    if tables is None:
        tables = sorted([p.stem for p in csv_dir.glob("*.csv")])

    if not tables:
        raise ValueError(f"未在 {csv_dir} 找到 CSV 文件")

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
