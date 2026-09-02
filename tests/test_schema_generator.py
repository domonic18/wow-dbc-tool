"""Schema 生成器测试."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wow_dbc_tool.schema.generator import (
    LOCALE_ORDER,
    _expand_locstring,
    _find_dbd_path,
    _parse_build_declarations,
    _parse_dbd_builds,
    _select_build,
    _width_to_type,
    generate_physical_schema,
    generate_schemas,
)

SAMPLE_DBD = """COLUMNS
int ID
float Speed
uint Flags
string ModelName
locstring Name_lang
int Effect<32>[3]
float EffectRealPointsPerLevel<32>[3]

LAYOUT 1A2B3C4D

BUILD 3.3.0.10958-3.3.5.12340
$id$ID
Speed
Flags
ModelName
Name_lang
Effect<32>[3]
EffectRealPointsPerLevel<32>[3]

BUILD 4.0.0.12911
$id$ID
Speed
Name_lang
"""


def test_parse_dbd_builds() -> None:
    builds = _parse_dbd_builds(SAMPLE_DBD)
    assert len(builds) == 2
    assert builds[0]["build_def"] == "BUILD 3.3.0.10958-3.3.5.12340"
    assert builds[0]["declarations"] == [
        "$id$ID",
        "Speed",
        "Flags",
        "ModelName",
        "Name_lang",
        "Effect<32>[3]",
        "EffectRealPointsPerLevel<32>[3]",
    ]
    assert builds[1]["build_def"] == "BUILD 4.0.0.12911"


def test_select_build() -> None:
    builds = _parse_dbd_builds(SAMPLE_DBD)
    selected = _select_build(builds, "3.3.5.12340")
    assert selected is not None
    assert selected["build_def"] == "BUILD 3.3.0.10958-3.3.5.12340"

    assert _select_build(builds, "4.0.0.12911") is not None
    assert _select_build(builds, "1.0.0.0") is None


def test_width_to_type() -> None:
    assert _width_to_type("u32", None) == "uint32"
    assert _width_to_type("u16", None) == "uint32"
    assert _width_to_type("u8", None) == "uint32"
    assert _width_to_type("32", "float") == "float"
    assert _width_to_type("32", "uint") == "uint32"
    assert _width_to_type("32", "int") == "int32"
    assert _width_to_type("8", None) == "int32"
    assert _width_to_type(None, "float") == "float"
    assert _width_to_type(None, "uint") == "uint32"
    assert _width_to_type(None, "string") == "string"
    assert _width_to_type(None, "locstring") == "string"
    assert _width_to_type(None, None) == "int32"


def test_expand_locstring() -> None:
    expanded = _expand_locstring("Name_lang")
    assert len(expanded) == 17
    locales = [name for name, _ in expanded[:16]]
    assert locales == [f"Name_Lang_{loc}" for loc in LOCALE_ORDER]
    assert expanded[16] == ("Name_Lang_Mask", "uint32")

    # base name normalization
    expanded2 = _expand_locstring("DescriptionLang")
    assert expanded2[0][0] == "Description_Lang_enUS"


def test_parse_build_declarations_array() -> None:
    columns = {
        "Effect": {"type": "int", "name": "Effect"},
        "EffectRealPointsPerLevel": {"type": "float", "name": "EffectRealPointsPerLevel"},
    }
    decls = ["Effect<32>[3]", "EffectRealPointsPerLevel<32>[3]"]
    fields = _parse_build_declarations(decls, columns)

    assert fields[:3] == [
        ("Effect_1", "int32"),
        ("Effect_2", "int32"),
        ("Effect_3", "int32"),
    ]
    assert fields[3:] == [
        ("EffectRealPointsPerLevel_1", "float"),
        ("EffectRealPointsPerLevel_2", "float"),
        ("EffectRealPointsPerLevel_3", "float"),
    ]


def test_parse_build_declarations_locstring() -> None:
    columns = {"Name_lang": {"type": "locstring", "name": "Name_lang"}}
    fields = _parse_build_declarations(["Name_lang"], columns)
    assert len(fields) == 17
    assert fields[0] == ("Name_Lang_enUS", "string")
    assert fields[-1] == ("Name_Lang_Mask", "uint32")


def test_parse_build_declarations_string() -> None:
    columns = {"ModelName": {"type": "string", "name": "ModelName"}}
    fields = _parse_build_declarations(["ModelName"], columns)
    assert fields == [("ModelName", "string")]


def test_find_dbd_path_case_insensitive(tmp_path: Path) -> None:
    dbd_dir = tmp_path / "definitions"
    dbd_dir.mkdir()
    (dbd_dir / "BannedAddons.dbd").write_text("COLUMNS\n", encoding="utf-8")

    assert _find_dbd_path(dbd_dir, "BannedAddons") == dbd_dir / "BannedAddons.dbd"
    assert _find_dbd_path(dbd_dir, "BannedAddOns") == dbd_dir / "BannedAddons.dbd"
    assert _find_dbd_path(dbd_dir, "Missing") is None


@pytest.fixture
def dbd_dir() -> Path:
    """WoWDBDefs definitions 目录."""
    path = Path(__file__).parent.parent / "third-party" / "WoWDBDefs" / "definitions"
    if not path.exists():
        pytest.skip("WoWDBDefs 子模块未初始化")
    return path


def test_generate_physical_schema_spell(dbd_dir: Path) -> None:
    schema = generate_physical_schema("Spell", None, dbd_dir, "3.3.5.12340")
    assert schema is not None
    assert schema["field_count"] == 234
    props = schema["properties"]

    assert props["ID"]["type"] == "int32"
    assert props["Category"]["type"] == "int32"
    assert props["Mechanic"]["type"] == "int32"
    assert props["Attributes"]["type"] == "int32"
    assert props["Name_Lang_zhCN"]["type"] == "string"
    assert props["EffectRealPointsPerLevel_1"]["type"] == "float"
    assert props["Effect_1"]["type"] == "int32"


def test_generate_physical_schema_creature_model_data(dbd_dir: Path) -> None:
    schema = generate_physical_schema("CreatureModelData", None, dbd_dir, "3.3.5.12340")
    assert schema is not None
    assert schema["field_count"] == 28
    assert schema["properties"]["ModelName"]["type"] == "string"
    assert schema["properties"]["ModelScale"]["type"] == "float"


def test_generate_physical_schema_creature_display_info(dbd_dir: Path) -> None:
    schema = generate_physical_schema("CreatureDisplayInfo", None, dbd_dir, "3.3.5.12340")
    assert schema is not None
    assert schema["field_count"] == 16
    props = schema["properties"]
    assert props["TextureVariation_1"]["type"] == "string"
    assert props["TextureVariation_2"]["type"] == "string"
    assert props["TextureVariation_3"]["type"] == "string"
    assert props["PortraitTextureName"]["type"] == "string"


def test_generate_physical_schema_item(dbd_dir: Path) -> None:
    schema = generate_physical_schema("Item", None, dbd_dir, "3.3.5.12340")
    assert schema is not None
    assert schema["field_count"] == 8
    for field in schema["field_order"]:
        assert schema["properties"][field]["type"] == "int32"


def test_generate_physical_schema_case_insensitive_lookup(dbd_dir: Path) -> None:
    schema = generate_physical_schema("BannedAddOns", None, dbd_dir, "3.3.5.12340")
    assert schema is not None
    assert schema["table_name"] == "BannedAddOns"


def test_generate_schemas_with_dbc_dir(dbd_dir: Path, tmp_path: Path) -> None:
    dbc_src = tmp_path / "dbc"
    dbc_src.mkdir()
    (dbc_src / "Item.dbc").write_bytes(b"WDBC" + b"\x00" * 20)
    (dbc_src / "Spell.dbc").write_bytes(b"WDBC" + b"\x00" * 20)

    output_dir = tmp_path / "out"
    result = generate_schemas(
        csv_dir=None,
        dbd_dir=dbd_dir,
        output_dir=output_dir,
        target_version="3.3.5.12340",
        dbc_dir=dbc_src,
    )

    assert result["generated"] == 2
    assert result["failed"] == 0
    assert (output_dir / "Item.schema.json").exists()
    assert (output_dir / "Spell.schema.json").exists()

    item_schema = json.loads((output_dir / "Item.schema.json").read_text(encoding="utf-8"))
    assert item_schema["field_count"] == 8
