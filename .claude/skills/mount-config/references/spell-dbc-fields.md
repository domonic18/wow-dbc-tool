# Spell.dbc 坐骑相关字段参考

## 核心字段表

| 字段名 | 类型 | 说明 | 坐骑推荐值 |
|--------|------|------|-----------|
| `ID` | uint32 | Spell 唯一标识 | 自定义建议 80000+ |
| `Mechanic` | uint32 | 机制类型 | **21** = MOUNT |
| `EffectApplyAuraName1` | uint32 | 第一个效果的 Aura 类型 | **207** = SPELL_AURA_MOUNTED |
| `EffectApplyAuraName2` | uint32 | 第二个效果的 Aura 类型 | 速度相关 (如 32) |
| `EffectApplyAuraName3` | uint32 | 第三个效果的 Aura 类型 | 0 或其他 |
| `EffectBasePoints1` | int32 | 效果1基础值 | CreatureDisplayID (坐骑模型) |
| `EffectBasePoints2` | int32 | 效果2基础值 | 速度加成值 |
| `EffectBasePoints3` | int32 | 效果3基础值 | 0 或其他 |
| `Attributes` | uint32 | 基础属性标志 | 0 或 2147483648 |
| `AttributesEx4` | uint32 | 扩展属性4标志 | 0 或 67108864 |
| `AreaGroupId` | uint32 | 区域组限制 | 0 = 无限制 |
| `SpellVisual2` | uint32 | 视觉效果 | 坐骑外观模型 |
| `EffectItemType3` | uint32 | 物品类型 | 关联 Item ID |
| `EffectSpellClassMaskC3` | uint32 | 法术类别掩码 | **7644** (标准坐骑) |

## Mechanic 值

| 值 | 名称 | 说明 |
|----|------|------|
| 21 | MOUNT | 坐骑 |

## Aura 类型 (EffectApplyAuraName)

| 值 | 名称 | 说明 |
|----|------|------|
| 32 | SPELL_AURA_MOD_INCREASE_SPEED | 增加移动速度 |
| 207 | SPELL_AURA_MOUNTED | 坐骑状态 |

## 典型坐骑 Spell 结构

```
Spell.dbc 记录（坐骑）:
├── ID: [SpellID]
├── Mechanic: 21
├── EffectApplyAuraName1: 207 (MOUNTED)
├── EffectBasePoints1: [CreatureDisplayID]
├── EffectApplyAuraName2: 32 (速度)
├── EffectBasePoints2: [速度值]
├── Attributes: [标志位组合]
├── AttributesEx4: [标志位组合]
├── AreaGroupId: [区域组ID 或 0]
└── EffectSpellClassMaskC3: 7644
```

## 标志位字段说明

### Attributes (uint32)

位掩码组合值，常见坐骑相关标志：

| 标志名 | 十六进制 | 十进制 | 说明 |
|--------|----------|--------|------|
| SPELL_ATTR0_OUTDOORS_ONLY | 0x80000000 | 2147483648 | 只能在户外使用 |

### AttributesEx4 (uint32)

| 标志名 | 十六进制 | 十进制 | 说明 |
|--------|----------|--------|------|
| SPELL_ATTR4_ONLY_FLYING_AREAS | 0x00400000 | 67108864 | 只能在飞行区域使用 |

## 区域限制 (AreaGroupId)

AreaGroupId 指向 AreaGroup.dbc，用于限制特定区域组可用。
设置为 0 表示无区域限制。

## 服务器端覆盖规则

即使 DBC 中配置允许飞行，服务器端仍会强制限制：

- 副本/战场默认不允许飞行
- 艾泽拉斯地球默认不允许飞行（除非服务器修改）
- 冬拥湖战斗期间不允许飞行
- 诺森德需要寒冷天气飞行技能 (Spell 54197)
