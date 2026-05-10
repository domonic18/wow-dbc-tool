# SkillLine.dbc

> 来源: https://wowdev.wiki/SkillLine.dbc
> 版本: 3.3.5a
> 最后同步: 2025-05-10

## 概述

SkillLine.dbc 包含游戏中所有 技能线 的数据。

## 文件头信息

| 属性 | 值 |
|------|-----|
| field_count | 7 |
| record_size | 28 |

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
wow-dbc-tool query SkillLine.dbc --filter ID=1 --json
wow-dbc-tool read SkillLine.dbc --limit 10 --json
```
