#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate-schemas.py
从现有 CSV 的 header 和 WoWDBDefs 的 .dbd 定义生成准确的 DBC 字段 schema，
输出到 tools/wow-dbc-tool/schemas/*.json，供 wow-dbc-tool 读取和导出使用。

用法:
    python tools/wow-dbc-tool/scripts/generate-schemas.py
    python tools/wow-dbc-tool/scripts/generate-schemas.py --version 3.3.5.12340
    python tools/wow-dbc-tool/scripts/generate-schemas.py --table Spell

关键设计:
- schema 中的字段数必须与 DBC 物理字段数完全一致
- locstring 逻辑字段需要展开为多个物理 string 字段（如 Title_Lang_enUS, Title_Lang_enGB...）
- 字段类型根据 CSV 列名模式 + WoWDBDefs 定义综合推断
"""

import csv
import json
import os
import re
import sys
import argparse
from pathlib import Path


TOOL_ROOT = Path(__file__).parent.parent
PROJECT_ROOT = TOOL_ROOT.parent.parent

DBD_DIR = TOOL_ROOT / "third-party" / "WoWDBDefs" / "definitions"
SCHEMAS_DIR = TOOL_ROOT / "schemas"
CSV_DIR = PROJECT_ROOT / "tables"

DEFAULT_TARGET_VERSION = "3.3.5.12340"


# 字符串类型字段名模式（用于从 CSV header 推断字段类型）
STRING_FIELD_PATTERNS = [
    # 本地化字符串字段（由 locstring 展开）
    r"_Lang_",
    r"_lang_",
    # 模型/贴图/图标名称
    r"^(ModelName|ModelTexture|InventoryIcon|Texture|PortraitTextureName)",
    r"^(TextureFilename|IconFilename)$",
    r"Name$",  # 如 CreatureModelData.ModelName
]


def is_string_field(field_name: str) -> bool:
    """根据字段名判断是否应为 string 类型."""
    for pattern in STRING_FIELD_PATTERNS:
        if re.search(pattern, field_name, re.IGNORECASE):
            return True
    return False


def parse_build_version(version_str: str) -> tuple:
    parts = version_str.strip().split(".")
    return tuple(int(p) for p in parts)


def version_in_range(target: tuple, build_def: str) -> bool:
    content = build_def.replace("BUILD", "", 1).strip()
    if "-" in content:
        left, right = content.split("-", 1)
        left_ver = parse_build_version(left)
        right_ver = parse_build_version(right)
        return left_ver <= target <= right_ver
    if "," in content:
        versions = [v.strip() for v in content.split(",")]
        return any(parse_build_version(v) == target for v in versions)
    return parse_build_version(content) == target


def parse_dbd_columns(content: str) -> dict:
    """解析 .dbd 文件的 COLUMNS 部分，获取逻辑字段定义."""
    columns = {}
    in_columns = False
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("BUILD") or stripped.startswith("LAYOUT") or stripped.startswith("COMMENT"):
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

            columns[name] = {
                "type": field_type,
                "name": name,
            }
    return columns


def get_dbd_columns_for_version(dbd_path: Path, target_version: str) -> dict:
    """获取指定版本的 .dbd 字段定义（仅 COLUMNS 部分）."""
    if not dbd_path.exists():
        return {}
    with open(dbd_path, "r", encoding="utf-8") as f:
        content = f.read()
    return parse_dbd_columns(content)


def expand_locstring_field(field_name: str, csv_headers: list, start_idx: int) -> list:
    """
    从 CSV header 中识别一个 locstring 字段展开后的物理字段。
    返回 [(物理字段名, 类型), ...]，直到遇到非该 locstring 的字段。
    """
    result = []
    base_name = field_name.replace("_lang", "").replace("Lang", "")

    for i in range(start_idx, len(csv_headers)):
        header = csv_headers[i]
        if header.startswith(field_name) or header.startswith(field_name.replace("_lang", "_Lang")):
            if "_Mask" in header:
                result.append((header, "int32"))
            else:
                result.append((header, "string"))
        elif header.startswith(base_name) and "_Lang_" in header:
            if "_Mask" in header:
                result.append((header, "int32"))
            else:
                result.append((header, "string"))
        else:
            break

    return result


def generate_physical_schema(table_name: str, target_version: str = DEFAULT_TARGET_VERSION) -> dict:
    """
    生成与 DBC 物理结构完全一致的 schema。
    """
    csv_path = CSV_DIR / f"{table_name}.csv"
    dbd_path = DBD_DIR / f"{table_name}.dbd"

    if not csv_path.exists():
        print(f"  未找到 CSV: {csv_path}")
        return None

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        csv_headers = next(reader)

    dbd_columns = get_dbd_columns_for_version(dbd_path, target_version)

    fields = []
    csv_idx = 0

    if dbd_columns:
        for col_name, col_info in dbd_columns.items():
            if csv_idx >= len(csv_headers):
                break

            col_type = col_info["type"]

            if col_type == "locstring":
                expanded = expand_locstring_field(col_name, csv_headers, csv_idx)
                if expanded:
                    for phys_name, phys_type in expanded:
                        fields.append({
                            "name": phys_name,
                            "type": phys_type,
                            "offset": csv_idx * 4,
                        })
                        csv_idx += 1
                else:
                    fields.append({
                        "name": csv_headers[csv_idx],
                        "type": "string",
                        "offset": csv_idx * 4,
                    })
                    csv_idx += 1
            elif col_type in ("int", "uint"):
                fields.append({
                    "name": csv_headers[csv_idx],
                    "type": "int32" if col_type == "int" else "uint32",
                    "offset": csv_idx * 4,
                })
                csv_idx += 1
            elif col_type == "float":
                fields.append({
                    "name": csv_headers[csv_idx],
                    "type": "float",
                    "offset": csv_idx * 4,
                })
                csv_idx += 1
            elif col_type == "string":
                fields.append({
                    "name": csv_headers[csv_idx],
                    "type": "string",
                    "offset": csv_idx * 4,
                })
                csv_idx += 1
            else:
                field_type = "string" if is_string_field(csv_headers[csv_idx]) else "int32"
                fields.append({
                    "name": csv_headers[csv_idx],
                    "type": field_type,
                    "offset": csv_idx * 4,
                })
                csv_idx += 1
    else:
        for i, header in enumerate(csv_headers):
            field_type = "string" if is_string_field(header) else "int32"
            fields.append({
                "name": header,
                "type": field_type,
                "offset": i * 4,
            })

    while csv_idx < len(csv_headers):
        header = csv_headers[csv_idx]
        field_type = "string" if is_string_field(header) else "int32"
        fields.append({
            "name": header,
            "type": field_type,
            "offset": csv_idx * 4,
        })
        csv_idx += 1

    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": f"{table_name} Physical Schema",
        "description": f"{table_name}.dbc 物理字段定义 (版本 {target_version})",
        "source": "https://github.com/wowdev/WoWDBDefs + CSV header",
        "table_name": table_name,
        "version": target_version,
        "type": "object",
        "field_count": len(fields),
        "field_order": [f["name"] for f in fields],
        "properties": {},
    }

    for field in fields:
        schema["properties"][field["name"]] = {
            "type": field["type"],
            "offset": field["offset"],
        }

    return schema


def main():
    parser = argparse.ArgumentParser(description="生成准确的 DBC 物理字段 Schema")
    parser.add_argument("--version", default=DEFAULT_TARGET_VERSION, help=f"目标版本 (默认: {DEFAULT_TARGET_VERSION})")
    parser.add_argument("--table", help="仅生成指定表")
    args = parser.parse_args()

    if not DBD_DIR.exists():
        print(f"错误: 未找到 WoWDBDefs 子模块: {DBD_DIR}")
        sys.exit(1)

    SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)

    if args.table:
        tables = [args.table]
    else:
        tables = sorted([p.stem for p in CSV_DIR.glob("*.csv")])

    if not tables:
        print(f"未在 {CSV_DIR} 找到CSV文件")
        sys.exit(1)

    print(f"目标版本: {args.version}")
    print(f"CSV目录: {CSV_DIR}")
    print(f"WoWDBDefs目录: {DBD_DIR}")
    print(f"输出目录: {SCHEMAS_DIR}")
    print(f"生成表数: {len(tables)}")
    print("-" * 60)

    generated = 0
    for table_name in tables:
        print(f"生成: {table_name}.schema.json ...", end=" ")
        schema = generate_physical_schema(table_name, args.version)

        if schema:
            output_path = SCHEMAS_DIR / f"{table_name}.schema.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(schema, f, ensure_ascii=False, indent=2)
            print(f"({schema['field_count']} 个物理字段)")
            generated += 1
        else:
            print("失败")

    print("-" * 60)
    print(f"完成: 成功 {generated}/{len(tables)} 个")


if __name__ == "__main__":
    main()
