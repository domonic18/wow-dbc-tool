# Hermes 飞书表格集成指南

## 概述

通过飞书官方 CLI 工具 (`lark-cli`)，Hermes 可以实现对飞书表格的完整增删改查操作。

---

## 前置条件

### 1. 安装飞书 CLI

```bash
# 全局安装
npm install -g @larksuite/cli

# 验证安装
lark-cli --version
```

### 2. 初始化配置

```bash
# 配置应用（首次使用）
lark-cli config init

# 用户授权（访问个人数据需要）
lark-cli auth login

# 检查状态
lark-cli doctor
```

---

## 核心操作

### 一、创建表格

```bash
# 创建空白表格
lark-cli sheets +create --title "坐骑列表"

# 创建带表头的表格
lark-cli sheets +create \
  --title "坐骑配置表" \
  --headers '["Spell ID", "名称", "类型", "状态"]' \
  --data '[["80146", "狡狐魔使", "陆地", "已修复"]]'
```

**Python 封装:**
```python
from tools.feishu_sheets_manager import FeishuSheetsManager

manager = FeishuSheetsManager()
result = manager.create_spreadsheet(
    title="坐骑列表",
    headers=["Spell ID", "名称", "类型", "状态"],
    data=[["80146", "狡狐魔使", "陆地", "已修复"]]
)
# 获取 spreadsheet_token
spreadsheet_token = result['data']['spreadsheet']['spreadsheet_token']
```

---

### 二、读取表格

```bash
# 读取指定范围
lark-cli sheets +read \
  --spreadsheet-token shtcnxxxx \
  --range "A1:D10" \
  --sheet-id "0"

# 通过 URL 读取
lark-cli sheets +read \
  --url "https://feishu.cn/sheets/shtcnxxxx" \
  --range "A1:Z1000"

# 读取并格式化输出
lark-cli sheets +read \
  --spreadsheet-token shtcnxxxx \
  --range "A1:D10" \
  --format table
```

**Python 封装:**
```python
# 读取整个表格
result = manager.read_sheet("shtcnxxxx", "A1:Z1000")
values = result['data']['valueRange']['values']

# 通过 URL 读取
result = manager.read_by_url(
    "https://feishu.cn/sheets/shtcnxxxx",
    "A1:D100"
)

# 获取表格信息（工作表列表）
info = manager.get_spreadsheet_info("shtcnxxxx")
sheets = info['data']['sheets']
```

---

### 三、写入/更新表格

```bash
# 覆盖写入单元格
lark-cli sheets +write \
  --spreadsheet-token shtcnxxxx \
  --range "A1:C3" \
  --values '[["Spell ID", "名称", "状态"],["80146", "狡狐魔使", "已修复"],["80364", "膨水鳐", "正常"]]'

# 追加行
lark-cli sheets +append \
  --spreadsheet-token shtcnxxxx \
  --range "A1:D1" \
  --values '[["80450", "新坐骑", "飞行", "待测试"]]'
```

**Python 封装:**
```python
# 覆盖写入
manager.write_cells(
    "shtcnxxxx",
    "A1:C3",
    [
        ["Spell ID", "名称", "状态"],
        ["80146", "狡狐魔使", "已修复"],
        ["80364", "膨水鳐", "正常"]
    ]
)

# 追加行
manager.append_rows(
    "shtcnxxxx",
    "A1:D1",
    [["80450", "新坐骑", "飞行", "待测试"]]
)
```

---

### 四、删除操作

```bash
# 删除行
lark-cli sheets +delete-dimension \
  --spreadsheet-token shtcnxxxx \
  --sheet-id "0" \
  --dimension ROWS \
  --start-index 4 \
  --count 1

# 删除列
lark-cli sheets +delete-dimension \
  --spreadsheet-token shtcnxxxx \
  --sheet-id "0" \
  --dimension COLUMNS \
  --start-index 2 \
  --count 1
```

**Python 封装:**
```python
# 删除第 5 行（索引 4）
manager.delete_rows("shtcnxxxx", "0", 4, 1)

# 删除第 3 列（索引 2）
manager.delete_columns("shtcnxxxx", "0", 2, 1)
```

---

### 五、查找替换

```bash
# 查找替换
lark-cli sheets +replace \
  --spreadsheet-token shtcnxxxx \
  --sheet-id "0" \
  --find "5160" \
  --replacement "7644"

# 查找单元格
lark-cli sheets +find \
  --spreadsheet-token shtcnxxxx \
  --sheet-id "0" \
  --query "狡狐魔使"
```

**Python 封装:**
```python
# 批量替换
manager.find_and_replace("shtcnxxxx", "0", "5160", "7644")

# 查找单元格
result = manager.find_cells("shtcnxxxx", "0", "狡狐魔使")
```

---

### 六、工作表管理

```bash
# 添加工作表
lark-cli sheets +create-sheet \
  --spreadsheet-token shtcnxxxx \
  --title "自定义坐骑"

# 删除工作表
lark-cli sheets +delete-sheet \
  --spreadsheet-token shtcnxxxx \
  --sheet-id "sheet_id_here"
```

**Python 封装:**
```python
# 添加工作表
manager.add_sheet("shtcnxxxx", "自定义坐骑")

# 删除工作表
manager.delete_sheet("shtcnxxxx", "sheet_id_here")
```

---

### 七、导出表格

```bash
# 导出为 Excel
lark-cli sheets +export \
  --spreadsheet-token shtcnxxxx \
  --format xlsx \
  -o /tmp/mount_list.xlsx

# 导出为 CSV
lark-cli sheets +export \
  --spreadsheet-token shtcnxxxx \
  --format csv \
  -o /tmp/mount_list.csv
```

**Python 封装:**
```python
# 导出表格
file_path = manager.export_spreadsheet(
    "shtcnxxxx",
    "/tmp/mount_list.xlsx",
    "xlsx"
)
```

---

## 完整示例：坐骑数据同步

### 场景：将 DBC 分析结果同步到飞书表格

```python
from tools.feishu_sheets_manager import FeishuSheetsManager, sync_mount_data_to_sheet

# 准备坐骑数据
mount_data = [
    {"Spell ID": 80146, "名称": "狡狐魔使", "原始MaskC3": 5160, "修复后MaskC3": 7644, "状态": "已修复"},
    {"Spell ID": 80364, "名称": "艾萨莉膨水鳐", "原始MaskC3": 7644, "修复后MaskC3": 7644, "状态": "正常"},
    {"Spell ID": 80016, "名称": "尼奥罗萨全视者", "原始MaskC3": 5160, "修复后MaskC3": 7644, "状态": "已修复"},
    {"Spell ID": 80030, "名称": "屠魔者的破邪尖啸者", "原始MaskC3": 5160, "修复后MaskC3": 7644, "状态": "已修复"}
]

# 同步到飞书表格
result = sync_mount_data_to_sheet("shtcnxxxx", mount_data)
print(f"同步完成: {result}")
```

---

## 在 Hermes 中使用

### 方式 1：直接调用 Python 脚本

```python
# 在 Hermes 的 execute_code 中
from tools.feishu_sheets_manager import FeishuSheetsManager

manager = FeishuSheetsManager()

# 读取坐骑列表
data = manager.read_sheet("shtcnxxxx", "A1:Z100")
print(data)

# 更新修复状态
manager.write_cells("shtcnxxxx", "D2", [["已修复"]])
```

### 方式 2：使用 terminal 工具执行 CLI

```bash
# 在 Hermes 的 terminal 中直接执行
lark-cli sheets +read --spreadsheet-token shtcnxxxx --range "A1:D10"
```

### 方式 3：创建 Skill 集成

将 `feishu_sheets_manager.py` 放入 `~/.hermes/skills/` 目录，Hermes 会自动加载。

---

## 常见问题

### 1. 权限不足 (403)

**原因**: 表格未添加应用权限

**解决**:
1. 打开飞书表格
2. 点击右上角 **「...」** → **「更多」** → **「添加文档应用」**
3. 选择你的 CLI 应用

### 2. 认证失败 (401)

**原因**: Token 过期或未登录

**解决**:
```bash
lark-cli auth login
```

### 3. 找不到命令

**原因**: lark-cli 未安装或未加入 PATH

**解决**:
```bash
npm install -g @larksuite/cli
export PATH="$PATH:$(npm root -g)/.bin"
```

---

## 参考资源

- 飞书 CLI GitHub: https://github.com/larksuite/cli
- 飞书开放平台: https://open.feishu.cn/
- 表格 API 文档: https://open.feishu.cn/document/server-docs/docs/sheets-v3/spreadsheet/get

---

*基于飞书 CLI v1.0.27*
