# wow-dbc-tool Help + Explain + Wowdev Wiki 集成 — 架构设计完成报告

> 任务: t_84a58f35  
> 设计人: Architect  
> 日期: 2025-05-10  
> 状态: 已完成

---

## 交付物清单

| 文档 | 路径 | 说明 |
|------|--------|------|
| 架构设计文档 | `docs/help-explain-wowdev-architecture.md` | 完整设计文档，包含所有模块的接口定义和数据流图 |
| 现有架构文档 | `docs/architecture.md` | 已存在，本次设计的基础 |

---

## 设计概览

### 新增模块 (3个)

```
src/wow_dbc_tool/
├── docs/          # 文档存储与查询
│   ├── store.py    # DocStore - Markdown 文档管理
│   └── explain.py  # ExplainService - 文件/字段说明查询
├── help/          # 帮助系统
│   └── system.py   # HelpSystem - 分级帮助
└── wiki/          # Wiki 爬虫（可选）
    └── crawler.py  # WikiCrawler - 从 wowdev.wiki 同步字段定义
```

### 新增 CLI 命令 (3个)

| 命令 | 用法 | 输出 |
|------|------|------|
| `help` | `wow-dbc-tool help [command] [--full]` | 分级帮助 JSON |
| `explain` | `wow-dbc-tool explain <dbc> [--field NAME]` | 文件/字段说明 JSON |
| `wiki` | `wow-dbc-tool wiki sync|list` | 同步状态/文档列表 JSON |

### 文档存储结构

```
docs/definitions/
├── index.json          # 索引: {dbc_name: markdown_file}
├── Spell.md            # Spell.dbc 说明
├── Item.md             # Item.dbc 说明
└── ...
```

---

## 架构决策记录 (ADR)

| ADR | 决策 | 理由 |
|-----|-------|------|
| ADR-006 | Markdown 作为文档格式 | 兼顾人类可读性和 Agent 解析，与现有 docs 一致 |
| ADR-007 | 帮助文本内嵌在代码中 | 无额外文件依赖，与版本同步 |
| ADR-008 | Wiki 数据预下载为主 | 离线可用，减少外部依赖，3.3.5a DBC 定义固定 |
| ADR-009 | 文档与 Schema 独立 | 用途不同，不应耦合，可通过工具同步 |
| ADR-010 | 新增模块放在包内 | 与现有结构一致，便于导入 |

---

## 质量检查结果

- [x] 所有需求已覆盖（Help/Explain/Wiki 集成）
- [x] 向后兼容（不破坏现有 CLI 接口）
- [x] 新增模块职责单一
- [x] 文档格式规范明确
- [x] 帮助系统分级清晰
- [x] Explain 输出 JSON 可序列化
- [x] Wiki 爬虫为可选依赖
- [x] 错误处理策略明确
- [x] 测试策略覆盖新增模块
- [x] 架构决策有记录和 rationale
- [x] 项目目录结构更新完整

---

## 实现建议

### 开发顺序

1. **第一阶段**: `help` 模块
   - 实现 HelpSystem
   - 添加 `help` 子命令
   - 测试: test_help.py

2. **第二阶段**: `docs` 模块
   - 实现 DocStore + Markdown 解析/渲染
   - 创建示例文档（Spell.dbc）
   - 测试: test_docs.py

3. **第三阶段**: `explain` 功能
   - 实现 ExplainService
   - 添加 `explain` 子命令
   - 测试: test_explain.py

4. **第四阶段**: `wiki` 模块（可选）
   - 实现 WikiCrawler
   - 添加 `wiki sync/list` 子命令
   - 测试: 需要网络的测试标记为 @pytest.mark.online

### pyproject.toml 更新

```toml
[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov>=4.0", "mypy>=1.0", "black>=23.0", "ruff>=0.1.0"]
wiki = ["requests>=2.28.0", "beautifulsoup4>=4.11.0"]
```

### 分支

在 `feature/help-explain-wowdev-docs` 分支上开发，与主分支保持独立。

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Markdown 解析错误 | 中 | 简单解析器，并有回退处理 |
| Wiki 结构变化 | 低 | 预下载为主，爬虫为可选 |
| 文档与 Schema 不一致 | 中 | 定期审查，可通过工具自动同步 |
| 帮助文本过时 | 低 | 帮助文本与代码内嵌，变更时同步更新 |

---

*架构设计已完成，可进入开发阶段。*
