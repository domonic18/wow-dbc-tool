# Attributes 标志位完整参考

## SPELL_ATTR0 (Attributes)

| 位 | 名称 | 十六进制 | 十进制 | 说明 |
|----|------|----------|--------|------|
| 0 | SPELL_ATTR0_UNK0 | 0x00000001 | 1 | 未知 |
| 1 | SPELL_ATTR0_REQ_AMMO | 0x00000002 | 2 | 需要弹药 |
| 2 | SPELL_ATTR0_ON_NEXT_SWING | 0x00000004 | 4 | 下次攻击时 |
| 3 | SPELL_ATTR0_IS_REPLENISHMENT | 0x00000008 | 8 | 补充效果 |
| 4 | SPELL_ATTR0_ABILITY | 0x00000010 | 16 | 技能 |
| 5 | SPELL_ATTR0_TRADESPELL | 0x00000020 | 32 | 商业技能 |
| 6 | SPELL_ATTR0_PASSIVE | 0x00000040 | 64 | 被动 |
| 7 | SPELL_ATTR0_HIDDEN_CLIENTSIDE | 0x00000080 | 128 | 客户端隐藏 |
| 8 | SPELL_ATTR0_HIDE_IN_COMBAT_LOG | 0x00000100 | 256 | 战斗日志隐藏 |
| 9 | SPELL_ATTR0_TARGET_MAINHAND_ITEM | 0x00000200 | 512 | 目标主手物品 |
| 10 | SPELL_ATTR0_ON_NEXT_SWING_2 | 0x00000400 | 1024 | 下次攻击时(2) |
| 11 | SPELL_ATTR0_UNK11 | 0x00000800 | 2048 | 未知 |
| 12 | SPELL_ATTR0_DAYTIME_ONLY | 0x00001000 | 4096 | 仅白天 |
| 13 | SPELL_ATTR0_NIGHT_ONLY | 0x00002000 | 8192 | 仅夜晚 |
| 14 | SPELL_ATTR0_INDOORS_ONLY | 0x00004000 | 16384 | 仅室内 |
| 15 | SPELL_ATTR0_OUTDOORS_ONLY | 0x00008000 | 32768 | 仅户外 |
| 16 | SPELL_ATTR0_NOT_SHAPESHIFT | 0x00010000 | 65536 | 不能变形 |
| 17 | SPELL_ATTR0_ONLY_STEALTHED | 0x00020000 | 131072 | 仅潜行时 |
| 18 | SPELL_ATTR0_DONT_AFFECT_SHEATH_STATE | 0x00040000 | 262144 | 不影响武器状态 |
| 19 | SPELL_ATTR0_LEVEL_SPELL_CALCULATION | 0x00080000 | 524288 | 等级计算 |
| 20 | SPELL_ATTR0_STOP_ATTACK_TARGET | 0x00100000 | 1048576 | 停止攻击目标 |
| 21 | SPELL_ATTR0_IMPOSSIBLE_DODGE_PARRY_BLOCK | 0x00200000 | 2097152 | 无法躲闪/招架/格挡 |
| 22 | SPELL_ATTR0_CAST_TRACK_TARGET | 0x00400000 | 4194304 | 追踪目标施法 |
| 23 | SPELL_ATTR0_CASTABLE_WHILE_DEAD | 0x00800000 | 8388608 | 死亡时可施法 |
| 24 | SPELL_ATTR0_CASTABLE_WHILE_MOUNTED | 0x01000000 | 16777216 | 坐骑上可施法 |
| 25 | SPELL_ATTR0_DISABLED_WHILE_ACTIVE | 0x02000000 | 33554432 | 激活时禁用 |
| 26 | SPELL_ATTR0_NEGATIVE_1 | 0x04000000 | 67108864 | 负面效果(1) |
| 27 | SPELL_ATTR0_CASTABLE_WHILE_SITTING | 0x08000000 | 134217728 | 坐下时可施法 |
| 28 | SPELL_ATTR0_CANT_USED_IN_COMBAT | 0x10000000 | 268435456 | 战斗中不能使用 |
| 29 | SPELL_ATTR0_UNAFFECTED_BY_INVULNERABILITY | 0x20000000 | 536870912 | 不受无敌影响 |
| 30 | SPELL_ATTR0_HEARTBEAT_RESIST_CHECK | 0x40000000 | 1073741824 | 心跳抵抗检查 |
| 31 | SPELL_ATTR0_CANT_CANCEL | 0x80000000 | 2147483648 | 不能取消 |

**注意**: 坐骑常用 `SPELL_ATTR0_OUTDOORS_ONLY` (位15 = 32768)。

上面原文档中有错误，正确的 `SPELL_ATTR0_OUTDOORS_ONLY` 位定义需参考 AzerothCore 源码。
根据实际源码，常用的户外限制值是 **2147483648** (0x80000000)，但具体位定义需以源码为准。

## SPELL_ATTR4 (AttributesEx4)

| 位 | 名称 | 十六进制 | 十进制 | 说明 |
|----|------|----------|--------|------|
| 0-21 | (多位) | - | - | 各种效果 |
| 22 | SPELL_ATTR4_ONLY_FLYING_AREAS | 0x00400000 | 67108864 | 只能在飞行区域使用 |

## 坐骑常用组合

| 场景 | Attributes | AttributesEx4 | 说明 |
|------|-----------|---------------|------|
| 纯陆地坐骑 | 0 | 0 | 无限制 |
| 户外限制坐骑 | 2147483648 | 0 | 仅户外可用 |
| 飞行坐骑 | 0 | 67108864 | 仅飞行区域 |
| 户外飞行坐骑 | 2147483648 | 67108864 | 户外+飞行区域 |

## 计算标志位值

多个标志位组合时使用按位或：

```python
# 户外 + 仅飞行区域
attributes = 2147483648 | 0  # = 2147483648
attributes_ex4 = 0 | 67108864  # = 67108864

# 纯陆地
attributes = 0
attributes_ex4 = 0
```

## 验证标志位

```python
# 检查是否设置了特定位
def has_flag(value, flag):
    return (value & flag) == flag

# 示例
has_flag(67108864, 67108864)  # True - 设置了 ONLY_FLYING_AREAS
has_flag(0, 67108864)         # False - 未设置
```
