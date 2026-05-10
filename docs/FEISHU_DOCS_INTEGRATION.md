# Hermes 访问飞书云文档配置指南

## 概述

基于飞书开放平台 API 文档，要让 Hermes 能够访问和操作飞书云文档，需要以下步骤：

---

## 一、前提条件

### 1. 创建飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 登录开发者账号
3. 创建企业自建应用（Custom App）
4. 获取 **App ID** 和 **App Secret**

### 2. 开通权限

在应用管理后台，开通以下权限：

| 权限 | 说明 | 用途 |
|------|------|------|
| `drive:drive` | 查看、评论、编辑和管理云空间中所有文件 | 完整操作权限 |
| `drive:drive:readonly` | 查看、评论和下载云空间中所有文件 | 只读权限 |
| `space:document:retrieve` | 获取云空间文件夹下的云文档清单 | 列出文档 |
| `docx:document` | 创建及编辑新版文档 | 编辑 docx |
| `docx:document:readonly` | 查看新版文档 | 读取 docx |

### 3. 为文档添加应用权限

**关键步骤**：在飞书云文档页面，点击右上角 **「...」** → **「更多」** → **「添加文档应用」**，选择你的应用。

> ⚠️ **注意**：必须先为文档添加应用权限，否则 API 调用会返回 403 错误！

---

## 二、API 调用流程

### 步骤 1：获取 Access Token

```bash
# 使用 tenant_access_token（应用级权限）
curl -X POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "cli_xxxxxxxxxxxx",
    "app_secret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  }'
```

响应：
```json
{
  "code": 0,
  "msg": "ok",
  "tenant_access_token": "t-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "expire": 7200
}
```

### 步骤 2：获取文件夹下的文件清单

```bash
# 获取根目录文件清单
curl -X GET "https://open.feishu.cn/open-apis/drive/v1/files?page_size=200" \
  -H "Authorization: Bearer t-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

响应包含文件的 `token` 和 `type`：
```json
{
  "code": 0,
  "data": {
    "files": [
      {
        "name": "坐骑列表.docx",
        "token": "doxcnePuYufKa49ISjhD8Iabcef",
        "type": "docx",
        "url": "https://feishu.cn/docx/doxcnePuYufKa49ISjhD8Iabcef"
      }
    ],
    "has_more": false
  }
}
```

### 步骤 3：获取文档内容

```bash
# 获取文档基本信息
curl -X GET "https://open.feishu.cn/open-apis/docx/v1/documents/doxcnePuYufKa49ISjhD8Iabcef" \
  -H "Authorization: Bearer t-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 获取文档内容（blocks）
curl -X GET "https://open.feishu.cn/open-apis/docx/v1/documents/doxcnePuYufKa49ISjhD8Iabcef/blocks?document_revision_id=-1" \
  -H "Authorization: Bearer t-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

### 步骤 4：编辑文档

```bash
# 批量更新文档内容
curl -X PATCH "https://open.feishu.cn/open-apis/docx/v1/documents/doxcnePuYufKa49ISjhD8Iabcef/blocks/bockcnePuYufKa49ISjhD8Iabcef" \
  -H "Authorization: Bearer t-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "operations": [
      {
        "action": "replace",
        "block_id": "block_xxx",
        "content": "新的内容"
      }
    ]
  }'
```

---

## 三、关键 API 列表

### 云空间（Drive）API

| API | 用途 |
|-----|------|
| `GET /drive/v1/files` | 获取文件夹下的文件清单 |
| `GET /drive/v1/files/:file_token` | 获取文件信息 |
| `POST /drive/v1/files/:file_token/copy` | 复制文件 |
| `DELETE /drive/v1/files/:file_token` | 删除文件 |

### 新版文档（Docx）API

| API | 用途 |
|-----|------|
| `GET /docx/v1/documents/:document_id` | 获取文档基本信息 |
| `GET /docx/v1/documents/:document_id/blocks` | 获取文档内容（blocks） |
| `PATCH /docx/v1/documents/:document_id/blocks/:block_id` | 更新文档块 |
| `POST /docx/v1/documents/:document_id/blocks` | 创建文档块 |
| `DELETE /docx/v1/documents/:document_id/blocks/:block_id` | 删除文档块 |

---

## 四、Hermes 集成方案

### 方案 1：使用 curl 命令（简单直接）

在 Hermes 的 `terminal` 工具中执行 curl 命令：

```bash
# 1. 获取 token
export FEISHU_APP_ID="cli_xxxxxxxxxxxx"
export FEISHU_APP_SECRET="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

TOKEN=$(curl -s -X POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal \
  -H "Content-Type: application/json" \
  -d "{\"app_id\":\"$FEISHU_APP_ID\",\"app_secret\":\"$FEISHU_APP_SECRET\"}" | jq -r '.tenant_access_token')

# 2. 获取文档内容
curl -s -X GET "https://open.feishu.cn/open-apis/docx/v1/documents/你的文档ID/blocks?document_revision_id=-1" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

### 方案 2：创建 Python 脚本工具

创建 `tools/feishu_docs.py`：

```python
#!/usr/bin/env python3
"""飞书云文档操作工具"""

import requests
import json
import os

class FeishuDocs:
    def __init__(self, app_id=None, app_secret=None):
        self.app_id = app_id or os.getenv('FEISHU_APP_ID')
        self.app_secret = app_secret or os.getenv('FEISHU_APP_SECRET')
        self.token = None
        self._get_token()
    
    def _get_token(self):
        """获取 tenant_access_token"""
        resp = requests.post(
            'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
            json={'app_id': self.app_id, 'app_secret': self.app_secret}
        )
        data = resp.json()
        if data.get('code') == 0:
            self.token = data['tenant_access_token']
        else:
            raise Exception(f"获取 token 失败: {data}")
    
    def list_files(self, folder_token=''):
        """获取文件夹下的文件清单"""
        resp = requests.get(
            f'https://open.feishu.cn/open-apis/drive/v1/files',
            headers={'Authorization': f'Bearer {self.token}'},
            params={'page_size': 200, 'folder_token': folder_token}
        )
        return resp.json()
    
    def get_document(self, document_id):
        """获取文档基本信息"""
        resp = requests.get(
            f'https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}',
            headers={'Authorization': f'Bearer {self.token}'}
        )
        return resp.json()
    
    def get_document_content(self, document_id):
        """获取文档内容"""
        resp = requests.get(
            f'https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks',
            headers={'Authorization': f'Bearer {self.token}'},
            params={'document_revision_id': '-1'}
        )
        return resp.json()

# 使用示例
if __name__ == '__main__':
    docs = FeishuDocs()
    
    # 列出根目录文件
    files = docs.list_files()
    print(json.dumps(files, indent=2, ensure_ascii=False))
    
    # 获取指定文档内容
    # content = docs.get_document_content('你的文档ID')
    # print(json.dumps(content, indent=2, ensure_ascii=False))
```

### 方案 3：集成到 Hermes 工具集

在 `~/.hermes/profiles/commander/tools/` 目录下创建飞书文档工具，Hermes 会自动识别并加载。

---

## 五、注意事项

### 1. 权限问题

**最常见的问题！** 如果 API 返回 403 错误，通常是因为：
- 应用没有开通相应权限
- 文档没有添加应用权限

**解决方法**：
1. 在应用管理后台确认权限已开通
2. 在云文档页面点击 **「...」** → **「更多」** → **「添加文档应用」**

### 2. 频率限制

- 获取 token：无限制
- 文档操作：单个应用每秒 5 次
- 云空间操作：20 次/秒

### 3. 文档类型

| 类型 | API 前缀 | 说明 |
|------|---------|------|
| 新版文档 (docx) | `/docx/v1/` | 推荐使用 |
| 旧版文档 (doc) | `/doc/v2/` | 兼容旧文档 |
| 表格 (sheet) | `/sheets/v3/` | 多维表格 |
| 多维表格 (bitable) | `/bitable/v1/` | 数据库表格 |

### 4. 文档 ID 获取

- 从 URL 获取：`https://feishu.cn/docx/doxcnePuYufKa49ISjhD8Iabcef`
- 文档 ID = `doxcnePuYufKa49ISjhD8Iabcef`
- 注意：知识库中的文档 URL token 不是 document_id，需要通过知识库 API 获取

---

## 六、快速开始步骤

1. ✅ 访问 https://open.feishu.cn/ 创建应用
2. ✅ 记录 App ID 和 App Secret
3. ✅ 开通 `drive:drive:readonly` 和 `docx:document:readonly` 权限
4. ✅ 在目标文档页面添加应用权限
5. ✅ 使用 curl 或 Python 脚本测试 API
6. ✅ 集成到 Hermes 工作流

---

## 七、参考资源

- 飞书开放平台：https://open.feishu.cn/
- 云空间 API 文档：https://open.feishu.cn/document/server-docs/docs/drive-v1/folder/list
- 新版文档 API 文档：https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/document/get
- 权限说明：https://open.feishu.cn/document/ukTMukTMukTM/uYTM5UjL2ETO14iNxkTN/scope-list

---

*文档生成时间：基于飞书开放平台官方 API 文档*
