# Faction.dbc

> 来源: https://wowdev.wiki/Faction.dbc
> 版本: 3.3.5a
> 最后同步: 2025-05-10

## 概述

Faction.dbc 包含游戏中所有 阵营定义 的数据。

## 文件头信息

| 属性 | 值 |
|------|-----|
| field_count | 20 |
| record_size | 80 |

## 字段定义

### ID
- **偏移**: 0
- **类型**: uint32
- **说明**: 唯一标识符
- **示例**: 1

### Name
- **偏移**: 4
- **类型**: string
- **说明**: 名称

## 常见用法

```bash
wow-dbc-tool query Faction.dbc --filter ID=1 --json
wow-dbc-tool read Faction.dbc --limit 10 --json
```
