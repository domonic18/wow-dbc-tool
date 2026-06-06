"""Schema 注册表 - 管理所有 DBC 文件的字段定义."""

from __future__ import annotations

import json
from pathlib import Path

from wow_dbc_tool.schema.field_def import FieldDef


class SchemaRegistry:
    """管理所有 DBC 文件的字段定义.

    内置常见 DBC 定义，支持自定义注册和从文件加载。

    Attributes:
        _builtins: 内置字段定义字典
        _custom: 用户注册的自定义定义
    """

    # 内置常见 DBC 定义
    _builtins: dict[str, list[FieldDef]] = {
        # Spell.dbc - 基础法术定义（示例）
        "Spell.dbc": [
            FieldDef("ID", "uint32", 0),
            FieldDef("Category", "uint32", 4),
            FieldDef("Dispel", "uint32", 8),
            FieldDef("Mechanic", "uint32", 12),
            FieldDef("Attributes", "uint32", 16),
            FieldDef("AttributesEx", "uint32", 20),
            FieldDef("AttributesEx2", "uint32", 24),
            FieldDef("AttributesEx3", "uint32", 28),
            FieldDef("AttributesEx4", "uint32", 32),
            FieldDef("AttributesEx5", "uint32", 36),
            FieldDef("AttributesEx6", "uint32", 40),
            FieldDef("AttributesEx7", "uint32", 44),
            FieldDef("Stances", "uint32", 48),
            FieldDef("StancesNot", "uint32", 52),
            FieldDef("Targets", "uint32", 56),
            FieldDef("TargetCreatureType", "uint32", 60),
            FieldDef("RequiresSpellFocus", "uint32", 64),
            FieldDef("FacingCasterFlags", "uint32", 68),
            FieldDef("CasterAuraState", "uint32", 72),
            FieldDef("TargetAuraState", "uint32", 76),
            FieldDef("CasterAuraStateNot", "uint32", 80),
            FieldDef("TargetAuraStateNot", "uint32", 84),
            FieldDef("CasterAuraSpell", "uint32", 88),
            FieldDef("TargetAuraSpell", "uint32", 92),
            FieldDef("ExcludeCasterAuraSpell", "uint32", 96),
            FieldDef("ExcludeTargetAuraSpell", "uint32", 100),
            FieldDef("CastingTimeIndex", "uint32", 104),
            FieldDef("RecoveryTime", "uint32", 108),
            FieldDef("CategoryRecoveryTime", "uint32", 112),
            FieldDef("InterruptFlags", "uint32", 116),
            FieldDef("AuraInterruptFlags", "uint32", 120),
            FieldDef("ChannelInterruptFlags", "uint32", 124),
            FieldDef("ProcFlags", "uint32", 128),
            FieldDef("ProcChance", "uint32", 132),
            FieldDef("ProcCharges", "uint32", 136),
            FieldDef("MaxLevel", "uint32", 140),
            FieldDef("BaseLevel", "uint32", 144),
            FieldDef("SpellLevel", "uint32", 148),
            FieldDef("DurationIndex", "uint32", 152),
            FieldDef("PowerType", "uint32", 156),
            FieldDef("ManaCost", "uint32", 160),
            FieldDef("ManaCostPerlevel", "uint32", 164),
            FieldDef("ManaPerSecond", "uint32", 168),
            FieldDef("ManaPerSecondPerLevel", "uint32", 172),
            FieldDef("RangeIndex", "uint32", 176),
            FieldDef("Speed", "float", 180),
            FieldDef("ModalNextSpell", "uint32", 184),
            FieldDef("StackAmount", "uint32", 188),
            FieldDef("Totem1", "uint32", 192),
            FieldDef("Totem2", "uint32", 196),
            FieldDef("Reagent1", "uint32", 200),
            FieldDef("Reagent2", "uint32", 204),
            FieldDef("Reagent3", "uint32", 208),
            FieldDef("Reagent4", "uint32", 212),
            FieldDef("Reagent5", "uint32", 216),
            FieldDef("Reagent6", "uint32", 220),
            FieldDef("Reagent7", "uint32", 224),
            FieldDef("Reagent8", "uint32", 228),
            FieldDef("ReagentCount1", "uint32", 232),
            FieldDef("ReagentCount2", "uint32", 236),
            FieldDef("ReagentCount3", "uint32", 240),
            FieldDef("ReagentCount4", "uint32", 244),
            FieldDef("ReagentCount5", "uint32", 248),
            FieldDef("ReagentCount6", "uint32", 252),
            FieldDef("ReagentCount7", "uint32", 256),
            FieldDef("ReagentCount8", "uint32", 260),
            FieldDef("EquippedItemClass", "uint32", 264),
            FieldDef("EquippedItemSubClassMask", "uint32", 268),
            FieldDef("EquippedItemInventoryTypeMask", "uint32", 272),
            FieldDef("Effect1", "uint32", 276),
            FieldDef("Effect2", "uint32", 280),
            FieldDef("Effect3", "uint32", 284),
            FieldDef("EffectDieSides1", "uint32", 288),
            FieldDef("EffectDieSides2", "uint32", 292),
            FieldDef("EffectDieSides3", "uint32", 296),
            FieldDef("EffectBaseDice1", "uint32", 300),
            FieldDef("EffectBaseDice2", "uint32", 304),
            FieldDef("EffectBaseDice3", "uint32", 308),
            FieldDef("EffectRealPointsPerLevel1", "float", 312),
            FieldDef("EffectRealPointsPerLevel2", "float", 316),
            FieldDef("EffectRealPointsPerLevel3", "float", 320),
            FieldDef("EffectBasePoints1", "uint32", 324),
            FieldDef("EffectBasePoints2", "uint32", 328),
            FieldDef("EffectBasePoints3", "uint32", 332),
            FieldDef("EffectMechanic1", "uint32", 336),
            FieldDef("EffectMechanic2", "uint32", 340),
            FieldDef("EffectMechanic3", "uint32", 344),
            FieldDef("EffectImplicitTargetA1", "uint32", 348),
            FieldDef("EffectImplicitTargetA2", "uint32", 352),
            FieldDef("EffectImplicitTargetA3", "uint32", 356),
            FieldDef("EffectImplicitTargetB1", "uint32", 360),
            FieldDef("EffectImplicitTargetB2", "uint32", 364),
            FieldDef("EffectImplicitTargetB3", "uint32", 368),
            FieldDef("EffectRadiusIndex1", "uint32", 372),
            FieldDef("EffectRadiusIndex2", "uint32", 376),
            FieldDef("EffectRadiusIndex3", "uint32", 380),
            FieldDef("EffectApplyAuraName1", "uint32", 384),
            FieldDef("EffectApplyAuraName2", "uint32", 388),
            FieldDef("EffectApplyAuraName3", "uint32", 392),
            FieldDef("EffectAmplitude1", "uint32", 396),
            FieldDef("EffectAmplitude2", "uint32", 400),
            FieldDef("EffectAmplitude3", "uint32", 404),
            FieldDef("EffectValueMultiplier1", "float", 408),
            FieldDef("EffectValueMultiplier2", "float", 412),
            FieldDef("EffectValueMultiplier3", "float", 416),
            FieldDef("EffectChainTarget1", "uint32", 420),
            FieldDef("EffectChainTarget2", "uint32", 424),
            FieldDef("EffectChainTarget3", "uint32", 428),
            FieldDef("EffectItemType1", "uint32", 432),
            FieldDef("EffectItemType2", "uint32", 436),
            FieldDef("EffectItemType3", "uint32", 440),
            FieldDef("EffectMiscValue1", "uint32", 444),
            FieldDef("EffectMiscValue2", "uint32", 448),
            FieldDef("EffectMiscValue3", "uint32", 452),
            FieldDef("EffectMiscValueB1", "uint32", 456),
            FieldDef("EffectMiscValueB2", "uint32", 460),
            FieldDef("EffectMiscValueB3", "uint32", 464),
            FieldDef("EffectTriggerSpell1", "uint32", 468),
            FieldDef("EffectTriggerSpell2", "uint32", 472),
            FieldDef("EffectTriggerSpell3", "uint32", 476),
            FieldDef("EffectPointsPerComboPoint1", "float", 480),
            FieldDef("EffectPointsPerComboPoint2", "float", 484),
            FieldDef("EffectPointsPerComboPoint3", "float", 488),
            FieldDef("EffectSpellClassMaskA1", "uint32", 492),
            FieldDef("EffectSpellClassMaskA2", "uint32", 496),
            FieldDef("EffectSpellClassMaskA3", "uint32", 500),
            FieldDef("EffectSpellClassMaskB1", "uint32", 504),
            FieldDef("EffectSpellClassMaskB2", "uint32", 508),
            FieldDef("EffectSpellClassMaskB3", "uint32", 512),
            FieldDef("EffectSpellClassMaskC1", "uint32", 516),
            FieldDef("EffectSpellClassMaskC2", "uint32", 520),
            FieldDef("EffectSpellClassMaskC3", "uint32", 524),
            FieldDef("SpellVisual1", "uint32", 528),
            FieldDef("SpellVisual2", "uint32", 532),
            FieldDef("SpellIconID", "uint32", 536),
            FieldDef("ActiveIconID", "uint32", 540),
            FieldDef("SpellPriority", "uint32", 544),
            FieldDef("SpellName", "string", 548),
            FieldDef("SpellName2", "string", 552),
            FieldDef("SpellName3", "string", 556),
            FieldDef("SpellName4", "string", 560),
            FieldDef("SpellName5", "string", 564),
            FieldDef("SpellName6", "string", 568),
            FieldDef("SpellName7", "string", 572),
            FieldDef("SpellName8", "string", 576),
            FieldDef("SpellName9", "string", 580),
            FieldDef("SpellName10", "string", 584),
            FieldDef("SpellName11", "string", 588),
            FieldDef("SpellName12", "string", 592),
            FieldDef("SpellName13", "string", 596),
            FieldDef("SpellName14", "string", 600),
            FieldDef("SpellName15", "string", 604),
            FieldDef("SpellName16", "string", 608),
            FieldDef("Rank", "string", 612),
            FieldDef("Rank2", "string", 616),
            FieldDef("Rank3", "string", 620),
            FieldDef("Rank4", "string", 624),
            FieldDef("Rank5", "string", 628),
            FieldDef("Rank6", "string", 632),
            FieldDef("Rank7", "string", 636),
            FieldDef("Rank8", "string", 640),
            FieldDef("Rank9", "string", 644),
            FieldDef("Rank10", "string", 648),
            FieldDef("Rank11", "string", 652),
            FieldDef("Rank12", "string", 656),
            FieldDef("Rank13", "string", 660),
            FieldDef("Rank14", "string", 664),
            FieldDef("Rank15", "string", 668),
            FieldDef("Rank16", "string", 672),
            FieldDef("Description", "string", 676),
            FieldDef("Description2", "string", 680),
            FieldDef("Description3", "string", 684),
            FieldDef("Description4", "string", 688),
            FieldDef("Description5", "string", 692),
            FieldDef("Description6", "string", 696),
            FieldDef("Description7", "string", 700),
            FieldDef("Description8", "string", 704),
            FieldDef("Description9", "string", 708),
            FieldDef("Description10", "string", 712),
            FieldDef("Description11", "string", 716),
            FieldDef("Description12", "string", 720),
            FieldDef("Description13", "string", 724),
            FieldDef("Description14", "string", 728),
            FieldDef("Description15", "string", 732),
            FieldDef("Description16", "string", 736),
            FieldDef("ToolTip", "string", 740),
            FieldDef("ToolTip2", "string", 744),
            FieldDef("ToolTip3", "string", 748),
            FieldDef("ToolTip4", "string", 752),
            FieldDef("ToolTip5", "string", 756),
            FieldDef("ToolTip6", "string", 760),
            FieldDef("ToolTip7", "string", 764),
            FieldDef("ToolTip8", "string", 768),
            FieldDef("ToolTip9", "string", 772),
            FieldDef("ToolTip10", "string", 776),
            FieldDef("ToolTip11", "string", 780),
            FieldDef("ToolTip12", "string", 784),
            FieldDef("ToolTip13", "string", 788),
            FieldDef("ToolTip14", "string", 792),
            FieldDef("ToolTip15", "string", 796),
            FieldDef("ToolTip16", "string", 800),
            FieldDef("ManaCostPercentage", "uint32", 804),
            FieldDef("StartRecoveryCategory", "uint32", 808),
            FieldDef("StartRecoveryTime", "uint32", 812),
            FieldDef("MaxTargetLevel", "uint32", 816),
            FieldDef("SpellFamilyName", "uint32", 820),
            FieldDef("SpellFamilyFlags", "uint32", 824),
            FieldDef("SpellFamilyFlags2", "uint32", 828),
            FieldDef("MaxAffectedTargets", "uint32", 832),
            FieldDef("DmgClass", "uint32", 836),
            FieldDef("PreventionType", "uint32", 840),
            FieldDef("StanceBarOrder", "uint32", 844),
            FieldDef("DmgMultiplier1", "float", 848),
            FieldDef("DmgMultiplier2", "float", 852),
            FieldDef("DmgMultiplier3", "float", 856),
            FieldDef("MinFactionId", "uint32", 860),
            FieldDef("MinReputation", "uint32", 864),
            FieldDef("RequiredAuraVision", "uint32", 868),
            FieldDef("TotemCategory1", "uint32", 872),
            FieldDef("TotemCategory2", "uint32", 876),
            FieldDef("AreaGroupId", "uint32", 880),
            FieldDef("SchoolMask", "uint32", 884),
            FieldDef("RuneCostID", "uint32", 888),
            FieldDef("SpellMissileID", "uint32", 892),
            FieldDef("PowerDisplayId", "uint32", 896),
            FieldDef("EffectBonusMultiplier1", "float", 900),
            FieldDef("EffectBonusMultiplier2", "float", 904),
            FieldDef("EffectBonusMultiplier3", "float", 908),
            FieldDef("SpellDescriptionVariableID", "uint32", 912),
            FieldDef("SpellDifficultyId", "uint32", 916),
        ],
    }

    _custom: dict[str, list[FieldDef]] = {}

    @classmethod
    def get(cls, dbc_name: str) -> list[FieldDef] | None:
        """获取指定 DBC 的字段定义.

        优先返回自定义定义，其次返回内置定义。

        Args:
            dbc_name: DBC 文件名（如 "Spell.dbc"）

        Returns:
            字段定义列表，未找到返回 None
        """
        if dbc_name in cls._custom:
            return cls._custom[dbc_name]
        return cls._builtins.get(dbc_name)

    @classmethod
    def register(cls, dbc_name: str, fields: list[FieldDef]) -> None:
        """注册自定义字段定义.

        Args:
            dbc_name: DBC 文件名
            fields: 字段定义列表
        """
        cls._custom[dbc_name] = fields

    @classmethod
    def load_from_file(cls, path: str | Path) -> None:
        """从 JSON 文件加载字段定义.

        JSON 格式:
        {
            "Spell.dbc": {
                "fields": [
                    {"name": "ID", "type": "uint32", "offset": 0},
                    ...
                ]
            }
        }

        Args:
            path: JSON 文件路径

        Raises:
            FileNotFoundError: 文件不存在
            json.JSONDecodeError: JSON 格式错误
        """
        path = Path(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        for dbc_name, schema_data in data.items():
            fields = [FieldDef.from_dict(fd) for fd in schema_data.get("fields", [])]
            cls.register(dbc_name, fields)

    @classmethod
    def list_builtins(cls) -> list[str]:
        """列出所有内置定义的 DBC 名称.

        Returns:
            DBC 文件名列表
        """
        return list(cls._builtins.keys())

    @classmethod
    def list_all(cls) -> list[str]:
        """列出所有已知定义（内置 + 自定义）.

        Returns:
            DBC 文件名列表
        """
        return list(set(cls._builtins.keys()) | set(cls._custom.keys()))

    @classmethod
    def clear_custom(cls) -> None:
        """清除所有自定义定义."""
        cls._custom.clear()

    @classmethod
    def infer_schema(cls, field_count: int, record_size: int) -> list[FieldDef]:
        """根据 field_count 和 record_size 推断字段布局.

        当没有 Schema 定义时，提供基础推断：
        - 如果 record_size == field_count * 4：所有字段为 int32（DBC 中常用 -1 表示无效值）
        - 否则：按 4 字节均分，标记为 "unknown"

        Args:
            field_count: 字段数量
            record_size: 记录大小

        Returns:
            推断的字段定义列表
        """
        if record_size == field_count * 4:
            return [FieldDef(f"field_{i}", "int32", i * 4) for i in range(field_count)]
        else:
            # 非标准情况，按 4 字节分段
            num_fields = record_size // 4
            return [FieldDef(f"field_{i}", "int32", i * 4) for i in range(num_fields)]
