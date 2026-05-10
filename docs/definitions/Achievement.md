# Achievement.dbc

> 来源: https://wowdev.wiki/Achievement.dbc
> 版本: 3.3.5a
> 最后同步: 2025-05-10

## 概述

Achievement.dbc 包含游戏中所有 成就定义 的数据。

## 文件头信息

| 属性 | 值 |
|------|-----|
| field_count | 12 |
| record_size | 48 |

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
wow-dbc-tool query Achievement.dbc --filter ID=1 --json
wow-dbc-tool read Achievement.dbc --limit 10 --json
```
