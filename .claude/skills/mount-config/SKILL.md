---
name: mount-config
description: >
  Configure WoW 3.3.5a custom mounts via Spell.dbc editing.
  Covers land, flying, water, and hybrid mounts with field-level guidance
  for Mechanic, Attributes, Aura effects, and server-side rules.
argument-hint: <mount-type> [constraints...]
allowed-tools: [Read, Edit, Write, Bash]
model: sonnet
---

# 魔兽世界 3.3.5a 坐骑配置 Skill

## 适用场景

- 为自定义服务器添加新坐骑
- 修改现有坐骑的行为（飞行/陆地/水上）
- 调整坐骑的区域限制、户外限制等属性
- 通过 wow-dbc-tool CLI 编辑 Spell.dbc

## 坐骑类型速查

| 类型 | Mechanic | Aura | AttributesEx4 | 典型用途 |
|------|----------|------|---------------|----------|
| 陆地坐骑 | 21 | 207 | 0 | 地面移动，无限制 |
| 飞行坐骑 | 21 | 207 | 67108864 | 仅飞行区域可用 |
| 户外限制坐骑 | 21 | 207 | 0 + Attributes=2147483648 | 只能在户外使用 |
| 区域限制坐骑 | 21 | 207 | 0 + AreaGroupId=xx | 限制特定区域 |

## 核心字段

### Spell.dbc 关键字段

| 字段 | 说明 | 推荐值 |
|------|------|--------|
| `Mechanic` | 机制类型 | **21** (MOUNT) |
| `EffectApplyAuraName1` | Aura 效果 | **207** (SPELL_AURA_MOUNTED) |
| `EffectBasePoints1` | 坐骑模型 ID | CreatureDisplayID |
| `Attributes` | 基础属性 | 0 或 2147483648 (户外限制) |
| `AttributesEx4` | 扩展属性4 | 0 或 67108864 (仅飞行区域) |
| `AreaGroupId` | 区域组限制 | 0 (无限制) 或特定区域组 ID |
| `EffectSpellClassMaskC3` | 法术类别掩码 | **7644** (标准坐骑类别) |

### 关键 Attributes 标志位

```cpp
// SPELL_ATTR0 (Attributes)
SPELL_ATTR0_OUTDOORS_ONLY = 0x80000000  // 2147483648，只能在户外使用

// SPELL_ATTR4 (AttributesEx4)
SPELL_ATTR4_ONLY_FLYING_AREAS = 0x00400000  // 67108864，只能在飞行区域使用
```

## 控制优先级（从高到低）

1. **服务器端硬编码** (SpellMgr.cpp case 判断) — 最优先
2. **DBC Attributes 标志位** — 户外/飞行区域限制
3. **DBC AreaGroupId** — 特定区域限制
4. **服务器端通用规则** — 副本/战场默认禁飞等

## 常用 CLI 操作

```bash
# 查询现有坐骑配置
python -m wow_dbc_tool query Spell.dbc --filter "Mechanic=21" --json

# 读取特定 Spell ID 的详细信息
python -m wow_dbc_tool read Spell.dbc --query "ID=458" --json

# 对比原始和修改后的 Spell.dbc
python -m wow_dbc_tool diff Spell.dbc Spell_modified.dbc --key-field ID --json

# 导出坐骑相关记录到 JSON
python -m wow_dbc_tool read Spell.dbc --query "Mechanic=21" --json > mounts.json
```

## 自定义坐骑推荐配置

### 方案 1: 纯陆地坐骑（推荐大多数自定义坐骑）

```
Mechanic: 21
EffectApplyAuraName1: 207
EffectBasePoints1: [模型ID]
Attributes: 0
AttributesEx4: 0
AreaGroupId: 0
EffectSpellClassMaskC3: 7644
```

- 任何区域可召唤（包括副本）
- 只能在地面移动

### 方案 2: 飞行坐骑

```
Mechanic: 21
EffectApplyAuraName1: 207
EffectBasePoints1: [模型ID]
Attributes: 0
AttributesEx4: 67108864
AreaGroupId: 0
EffectSpellClassMaskC3: 7644
```

- 只能在允许飞行的区域召唤
- 艾泽拉斯地球默认无法召唤

### 方案 3: 户外限制坐骑

```
Mechanic: 21
EffectApplyAuraName1: 207
EffectBasePoints1: [模型ID]
Attributes: 2147483648
AttributesEx4: 0
AreaGroupId: 0
EffectSpellClassMaskC3: 7644
```

- 只能在户外使用
- 室内/副本中无法召唤

## 飞行区域规则速查

| 区域 | 默认飞行规则 | 备注 |
|------|-------------|------|
| 艾泽拉斯地球 (0/1) | 默认禁止 | 需服务器特殊配置或寒冷天气飞行 |
| 外域 (530) | 允许 | 需飞行技能 |
| 诺森德 (571) | 允许 | 需寒冷天气飞行 (54197) |
| 副本/战场 | 默认禁止 | 服务器端强制限制 |
| 冬拥湖 | 战斗时禁止 | 服务器端硬编码控制 |

## 注意事项

- `EffectSpellClassMaskC3: 7644` 是标准坐骑类别，确保服务器正确识别为坐骑
- 服务器端规则（如副本禁飞）会覆盖 DBC 中的 Attributes 设置
- 特殊坐骑（冬拥湖飞行坐骑等）需要服务器端 SpellMgr.cpp 配合
- 修改后务必进行 diff 对比，确认只修改了预期字段
