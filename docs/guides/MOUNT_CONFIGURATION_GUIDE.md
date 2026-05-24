# 魔兽世界 3.3.5a 坐骑配置完整指南

## 概述

本文档基于 AzerothCore 开源代码和 DBC 文件分析，详细说明坐骑的几种配置方法。

---

## 一、坐骑类型分类

### 1. 陆地坐骑 (Land Mount)
- **特征**: 只能在地面移动
- **Aura**: `SPELL_AURA_MOUNTED` (207)
- **速度**: 由 `SPELL_AURA_MOD_INCREASE_SPEED` (32) 控制
- **限制**: 无特殊飞行或水上能力

### 2. 飞行坐骑 (Flying Mount)
- **特征**: 可以在允许飞行的区域飞行
- **Aura**: `SPELL_AURA_MOUNTED` (207) + 飞行相关 Aura
- **关键字段**: 
  - `AttributesEx4` 包含 `SPELL_ATTR4_ONLY_FLYING_AREAS` (0x00400000 = 67108864)
  - 或服务器端硬编码 Spell ID 判断

### 3. 水上坐骑 (Water Mount)
- **特征**: 可以在水上/水下移动
- **Aura**: 水中速度相关 Aura
- **示例**: 海龟、海龟坐骑

### 4. 混合坐骑 (Hybrid Mount)
- **特征**: 同时具备多种移动能力
- **示例**: 既能飞行又能水上移动

---

## 二、DBC 文件关键字段

### Spell.dbc 关键字段

| 字段 | 说明 | 用途 |
|------|------|------|
| `Mechanic` | 机制类型 | 21 = MOUNT (坐骑) |
| `EffectApplyAuraName1/2/3` | Aura 效果类型 | 207 = MOUNTED, 其他 = 速度/飞行 |
| `EffectBasePoints1/2/3` | 效果基础值 | 坐骑模型 ID (CreatureDisplayID) |
| `Attributes` | 基础属性 | `SPELL_ATTR0_OUTDOORS_ONLY` = 户外限制 |
| `AttributesEx4` | 扩展属性4 | `SPELL_ATTR4_ONLY_FLYING_AREAS` = 仅飞行区域 |
| `AreaGroupId` | 区域组限制 | 限制特定区域可用 |
| `SpellVisual2` | 视觉效果 | 坐骑外观模型 |
| `EffectItemType3` | 物品类型 | 关联 Item ID |
| `EffectSpellClassMaskC3` | 法术类别掩码 | 服务器判断坐骑子类型 |

### 关键 Attributes 标志位

```cpp
// SPELL_ATTR0 (Attributes)
SPELL_ATTR0_OUTDOORS_ONLY = 0x80000000  // 只能在户外使用

// SPELL_ATTR4 (AttributesEx4)  
SPELL_ATTR4_ONLY_FLYING_AREAS = 0x00400000  // 只能在飞行区域使用
```

---

## 三、坐骑配置方法详解

### 方法 1: 基础陆地坐骑配置

```
Spell ID: [任意]
Mechanic: 21 (MOUNT)
EffectApplyAuraName1: 207 (SPELL_AURA_MOUNTED)
EffectBasePoints1: [CreatureDisplayID]
Attributes: 0 (无特殊限制)
AttributesEx4: 0 (无飞行限制)
AreaGroupId: 0 (无区域限制)
```

**示例**: 棕马 (Spell 458)
- 只能在地面移动
- 无户外限制
- 无区域限制

---

### 方法 2: 飞行坐骑配置

#### 方式 A: 使用 AttributesEx4 标志位

```
Spell ID: [任意]
Mechanic: 21 (MOUNT)
EffectApplyAuraName1: 207 (SPELL_AURA_MOUNTED)
EffectBasePoints1: [CreatureDisplayID]
Attributes: 0
AttributesEx4: 67108864 (SPELL_ATTR4_ONLY_FLYING_AREAS)
AreaGroupId: 0
```

**效果**: 
- 只能在允许飞行的区域召唤
- 在艾泽拉斯地球（无飞行许可区域）无法召唤

#### 方式 B: 服务器端硬编码 Spell ID

AzerothCore 源码中的特殊处理：

```cpp
// 迅捷幽灵狮鹫 (55164) 和 迅捷飞行小精灵 (55173)
case 55164:
case 55173:
{
    Battlefield* Bf = sBattlefieldMgr->GetBattlefieldToZoneId(player->GetZoneId());
    return !Bf || Bf->CanFlyIn();
}
```

**特点**:
- 不依赖 DBC 标志位
- 服务器直接判断 Spell ID
- 用于冬拥湖等特殊战场的飞行坐骑

---

### 方法 3: 户外限制坐骑配置

```
Spell ID: [任意]
Mechanic: 21 (MOUNT)
EffectApplyAuraName1: 207 (SPELL_AURA_MOUNTED)
EffectBasePoints1: [CreatureDisplayID]
Attributes: 2147483648 (SPELL_ATTR0_OUTDOORS_ONLY)
AttributesEx4: 0
AreaGroupId: 0
```

**效果**:
- 只能在户外召唤
- 室内/副本中无法使用
- 不限制飞行能力

---

### 方法 4: 区域限制坐骑配置

```
Spell ID: [任意]
Mechanic: 21 (MOUNT)
EffectApplyAuraName1: 207 (SPELL_AURA_MOUNTED)
EffectBasePoints1: [CreatureDisplayID]
Attributes: 0
AttributesEx4: 0
AreaGroupId: [AreaGroup ID]
```

**效果**:
- 只能在 AreaGroup 指定的区域使用
- 用于限制特定大陆/区域的坐骑

---

### 方法 5: 服务器端脚本控制（最灵活）

AzerothCore 使用 `SpellScript` 或 `AuraScript` 控制：

```cpp
// 示例：冬拥湖精华
 case 57940: // Essence of Wintergrasp OUTSIDE
 case 58045: // Essence of Wintergrasp INSIDE
 {
     if (!player)
         return false;
     
     if (sWorld->getIntConfig(CONFIG_WINTERGRASP_ENABLE) != 1)
         return false;
     
     Battlefield* Bf = sBattlefieldMgr->GetBattlefieldByBattleId(BATTLEFIELD_BATTLEID_WG);
     if (!Bf || player->GetTeamId() != Bf->GetDefenderTeam() || Bf->IsWarTime())
         return false;
     break;
 }
```

**特点**:
- 最灵活的控制方式
- 可以检查玩家状态、战场状态、阵营等
- 不受 DBC 字段限制

---

## 四、飞行坐骑在不同地方的实现方式

### 1. 艾泽拉斯地球 (Eastern Kingdoms / Kalimdor)

**默认规则**: 
- 3.3.5a 版本中，艾泽拉斯地球**不允许飞行**
- 除非服务器特殊配置

**实现方式**:
```cpp
// 服务器端检查
if (map_id == 0 || map_id == 1) {  // 艾泽拉斯地图
    if (!player->HasSpell(SPELL_COLD_WEATHER_FLYING)) {
        return SPELL_FAILED_NOT_HERE;
    }
}
```

### 2. 外域 (Outland)

**默认规则**:
- 允许飞行（需要飞行技能）

**实现方式**:
- 地图本身允许飞行
- 坐骑 Spell 无特殊限制即可飞行

### 3. 诺森德 (Northrend)

**默认规则**:
- 允许飞行（需要寒冷天气飞行技能）

**实现方式**:
```cpp
// 检查寒冷天气飞行
if (!player->HasSpell(54197)) {  // Cold Weather Flying
    return SPELL_FAILED_NOT_HERE;
}
```

### 4. 副本/战场 (Dungeon/Battleground)

**默认规则**:
- 大多数副本/战场**不允许飞行**

**实现方式**:
```cpp
// 战场检查
Battlefield* Bf = sBattlefieldMgr->GetBattlefieldToZoneId(player->GetZoneId());
if (Bf && !Bf->CanFlyIn()) {
    return SPELL_FAILED_NOT_HERE;
}

// 副本检查
if (map->IsDungeon() || map->IsRaid()) {
    return SPELL_FAILED_NOT_HERE;
}
```

### 5. 冬拥湖 (Wintergrasp)

**特殊规则**:
- 战斗期间不允许飞行
- 非战斗期间允许飞行

**实现方式**:
```cpp
case 55164: // 迅捷幽灵狮鹫
case 55173: // 迅捷飞行小精灵
{
    Battlefield* Bf = sBattlefieldMgr->GetBattlefieldToZoneId(player->GetZoneId());
    return !Bf || Bf->CanFlyIn();  // 战场期间 CanFlyIn = false
}
```

---

## 五、自定义坐骑配置建议

### 方案 1: 纯陆地坐骑（推荐大多数自定义坐骑）

```
Spell ID: 8xxxx
Mechanic: 21
EffectApplyAuraName1: 207
EffectBasePoints1: [模型ID]
Attributes: 0
AttributesEx4: 0
AreaGroupId: 0
EffectSpellClassMaskC3: 7644  (与膨水鳐相同)
```

**效果**:
- 只能在地面移动
- 任何区域都可以召唤（包括副本）
- 但只能在地面行走

### 方案 2: 飞行坐骑

```
Spell ID: 8xxxx
Mechanic: 21
EffectApplyAuraName1: 207
EffectBasePoints1: [模型ID]
Attributes: 0
AttributesEx4: 67108864  (SPELL_ATTR4_ONLY_FLYING_AREAS)
AreaGroupId: 0
EffectSpellClassMaskC3: 7644
```

**效果**:
- 只能在允许飞行的区域召唤
- 艾泽拉斯地球无法召唤（除非服务器修改规则）

### 方案 3: 区域限制坐骑

```
Spell ID: 8xxxx
Mechanic: 21
EffectApplyAuraName1: 207
EffectBasePoints1: [模型ID]
Attributes: 0
AttributesEx4: 0
AreaGroupId: [特定区域组ID]
EffectSpellClassMaskC3: 7644
```

**效果**:
- 只能在指定区域组使用
- 用于限制特定大陆的坐骑

---

## 六、关键总结

### 坐骑行为控制优先级（从高到低）

1. **服务器端硬编码** (SpellMgr.cpp 中的 case 判断)
   - 最优先，可以覆盖所有其他设置
   - 用于特殊坐骑（冬拥湖飞行坐骑等）

2. **DBC Attributes 标志位**
   - `SPELL_ATTR0_OUTDOORS_ONLY` = 户外限制
   - `SPELL_ATTR4_ONLY_FLYING_AREAS` = 飞行区域限制

3. **DBC AreaGroupId**
   - 限制特定区域可用

4. **服务器端通用规则**
   - 副本/战场默认不允许飞行
   - 地图飞行许可检查

### 修复建议

对于自定义坐骑（如狡狐魔使），建议配置：

```
EffectSpellClassMaskC3: 7644  (标准坐骑类别)
EffectItemType3: 9140364      (与膨水鳐相同)
```

这样服务器会将其识别为**标准陆地坐骑**，应用默认规则：
- ✅ 任何区域可召唤
- ✅ 地面移动
- ❌ 不能飞行（除非地图允许且坐骑有飞行配置）

---

## 七、参考资源

- AzerothCore 源码: https://github.com/azerothcore/azerothcore-wotlk
- SpellMgr.cpp: 坐骑特殊处理逻辑
- SpellInfo.cpp: `CheckLocation` 函数（区域检查）
- SpellAuraDefines.h: Aura 类型定义
- SpellDefines.h: Attributes 标志位定义

---

*文档生成时间: 基于 wow-dbc-tool 项目 DBC 分析和 AzerothCore 源码研究*
