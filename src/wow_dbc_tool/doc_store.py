"""文档存储模块 - Markdown 文档管理.

管理 docs/definitions/ 目录下的 Markdown 文档和 JSON 索引。
支持加载、保存、查询 DBC 字段定义文档。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class DocEntry:
    """文档条目."""

    name: str  # DBC 名称（如 "Spell.dbc"）
    title: str = ""  # 文档标题
    source: str = ""  # 来源 URL
    version: str = "3.3.5a"  # 游戏版本
    last_sync: str = ""  # 最后同步时间
    field_count: int = 0  # 字段数量
    record_size: int = 0  # 记录大小
    fields: list[dict[str, Any]] = field(default_factory=list)  # 字段定义列表
    overview: str = ""  # 概述文本
    examples: list[str] = field(default_factory=list)  # 示例用法

    def to_dict(self) -> dict[str, Any]:
        """转为字典（JSON 输出）."""
        return {
            "name": self.name,
            "title": self.title,
            "source": self.source,
            "version": self.version,
            "last_sync": self.last_sync,
            "field_count": self.field_count,
            "record_size": self.record_size,
            "fields": self.fields,
            "overview": self.overview,
            "examples": self.examples,
        }


class DocStore:
    """文档存储管理器.

    管理 docs/definitions/ 目录下的 Markdown 文档和索引。
    """

    def __init__(self, docs_dir: str | Path | None = None) -> None:
        """初始化文档存储.

        Args:
            docs_dir: 文档目录路径，None 使用默认路径
        """
        if docs_dir is None:
            self.docs_dir = self._find_default_docs_dir()
        else:
            self.docs_dir = Path(docs_dir)

        self.index_path = self.docs_dir / "index.json"
        self._index: dict[str, str] = {}  # name -> markdown_file
        self._cache: dict[str, DocEntry] = {}  # 解析缓存

    def _find_default_docs_dir(self) -> Path:
        """查找默认文档目录.

        从安装位置或开发位置查找。
        """
        # 1. 尝试从包路径推导
        try:
            import wow_dbc_tool
            pkg_dir = Path(wow_dbc_tool.__file__).parent
            # 向上找到项目根目录
            project_root = pkg_dir.parent.parent  # src/wow_dbc_tool -> src -> project_root
            docs_dir = project_root / "docs" / "definitions"
            if docs_dir.exists():
                return docs_dir

            # 2. 使用包内嵌文档（安装模式）
            embedded = pkg_dir / "docs" / "definitions"
            if embedded.exists():
                return embedded
        except ImportError:
            pass

        # 3. 默认创建在当前工作目录
        return Path.cwd() / "docs" / "definitions"

    def load_index(self) -> dict[str, str]:
        """加载索引文件.

        Returns:
            索引字典: {dbc_name: markdown_filename}
        """
        if self.index_path.exists():
            with open(self.index_path, encoding="utf-8") as f:
                self._index = json.load(f)
        return self._index

    def save_index(self) -> None:
        """保存索引文件."""
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(self._index, f, indent=2, ensure_ascii=False)

    def get(self, dbc_name: str) -> DocEntry | None:
        """获取指定 DBC 的文档.

        Args:
            dbc_name: DBC 文件名（如 "Spell.dbc"）

        Returns:
            文档条目，未找到返回 None
        """
        # 先检查缓存
        if dbc_name in self._cache:
            return self._cache[dbc_name]

        self.load_index()
        md_file = self._index.get(dbc_name)
        if md_file is None:
            return None

        path = self.docs_dir / md_file
        if not path.exists():
            return None

        entry = self._parse_markdown(path)
        self._cache[dbc_name] = entry
        return entry

    def list_all(self) -> list[str]:
        """列出所有已文档化的 DBC.

        Returns:
            DBC 名称列表
        """
        self.load_index()
        return list(self._index.keys())

    def save(self, entry: DocEntry) -> None:
        """保存文档条目.

        Args:
            entry: 文档条目
        """
        self.docs_dir.mkdir(parents=True, exist_ok=True)

        # 生成 Markdown 文件
        md_file = f"{entry.name.replace('.dbc', '')}.md"
        path = self.docs_dir / md_file

        content = self._render_markdown(entry)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        # 更新索引
        self._index[entry.name] = md_file
        self.save_index()

        # 更新缓存
        self._cache[entry.name] = entry

    def _parse_markdown(self, path: Path) -> DocEntry:
        """解析 Markdown 文件为 DocEntry.

        Args:
            path: Markdown 文件路径

        Returns:
            文档条目
        """
        with open(path, encoding="utf-8") as f:
            content = f.read()

        # 提取标题
        name = path.stem + ".dbc"
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1) if title_match else name

        # 提取元数据（frontmatter 风格）
        source = ""
        version = "3.3.5a"
        last_sync = ""
        field_count = 0
        record_size = 0
        overview = ""
        examples: list[str] = []
        fields: list[dict[str, Any]] = []

        # 提取 source
        source_match = re.search(r">\s*来源:\s*(.+)", content)
        if source_match:
            source = source_match.group(1).strip()

        # 提取 version
        version_match = re.search(r">\s*版本:\s*(.+)", content)
        if version_match:
            version = version_match.group(1).strip()

        # 提取 last_sync
        sync_match = re.search(r">\s*最后同步:\s*(.+)", content)
        if sync_match:
            last_sync = sync_match.group(1).strip()

        # 提取概述
        overview_match = re.search(r"##\s+概述\s*\n\n(.+?)(?=\n##|\Z)", content, re.DOTALL)
        if overview_match:
            overview = overview_match.group(1).strip()

        # 提取文件头信息
        header_match = re.search(r"\|\s*field_count\s*\|\s*(\d+)\s*\|", content)
        if header_match:
            field_count = int(header_match.group(1))

        size_match = re.search(r"\|\s*record_size\s*\|\s*(\d+)\s*\|", content)
        if size_match:
            record_size = int(size_match.group(1))

        # 提取字段定义
        field_sections = re.findall(
            r"###\s+(\w+)\s*\n((?:-\s*\*\*.+?\*\*:\s*.+?\n)+)",
            content,
        )
        for field_name, field_body in field_sections:
            field_info: dict[str, Any] = {"name": field_name}

            # 提取偏移
            offset_match = re.search(r"-\s*\*\*偏移\*\*:\s*(\d+)", field_body)
            if offset_match:
                field_info["offset"] = int(offset_match.group(1))

            # 提取类型
            type_match = re.search(r"-\s*\*\*类型\*\*:\s*(\w+)", field_body)
            if type_match:
                field_info["type"] = type_match.group(1)

            # 提取说明
            desc_match = re.search(r"-\s*\*\*说明\*\*:\s*(.+)", field_body)
            if desc_match:
                field_info["description"] = desc_match.group(1).strip()

            # 提取示例
            example_match = re.search(r"-\s*\*\*示例\*\*:\s*(.+)", field_body)
            if example_match:
                field_info["examples"] = [example_match.group(1).strip()]

            fields.append(field_info)

        # 提取常见用法示例
        examples_match = re.search(r"##\s+常见用法\s*\n\n```bash\n(.+?)```", content, re.DOTALL)
        if examples_match:
            examples_text = examples_match.group(1).strip()
            examples = [line.strip() for line in examples_text.split("\n") if line.strip()]

        return DocEntry(
            name=name,
            title=title,
            source=source,
            version=version,
            last_sync=last_sync,
            field_count=field_count or len(fields),
            record_size=record_size,
            fields=fields,
            overview=overview,
            examples=examples,
        )

    def _render_markdown(self, entry: DocEntry) -> str:
        """渲染 DocEntry 为 Markdown.

        Args:
            entry: 文档条目

        Returns:
            Markdown 文本
        """
        lines: list[str] = []

        # 标题
        lines.append(f"# {entry.title or entry.name}")
        lines.append("")

        # 元数据
        if entry.source:
            lines.append(f"> 来源: {entry.source}")
        lines.append(f"> 版本: {entry.version}")
        if entry.last_sync:
            lines.append(f"> 最后同步: {entry.last_sync}")
        lines.append("")

        # 概述
        if entry.overview:
            lines.append("## 概述")
            lines.append("")
            lines.append(entry.overview)
            lines.append("")

        # 文件头信息
        if entry.field_count or entry.record_size:
            lines.append("## 文件头信息")
            lines.append("")
            lines.append("| 属性 | 值 |")
            lines.append("|------|-----|")
            if entry.field_count:
                lines.append(f"| field_count | {entry.field_count} |")
            if entry.record_size:
                lines.append(f"| record_size | {entry.record_size} |")
            lines.append("")

        # 字段定义
        if entry.fields:
            lines.append("## 字段定义")
            lines.append("")
            for field in entry.fields:
                name = field.get("name", "Unknown")
                lines.append(f"### {name}")
                if "offset" in field:
                    lines.append(f"- **偏移**: {field['offset']}")
                if "type" in field:
                    lines.append(f"- **类型**: {field['type']}")
                if "description" in field:
                    lines.append(f"- **说明**: {field['description']}")
                if "examples" in field and field["examples"]:
                    lines.append(f"- **示例**: {field['examples'][0]}")
                lines.append("")

        # 常见用法
        if entry.examples:
            lines.append("## 常见用法")
            lines.append("")
            lines.append("```bash")
            for ex in entry.examples:
                lines.append(ex)
            lines.append("```")
            lines.append("")

        return "\n".join(lines)

    def search_fields(self, query: str) -> list[dict[str, Any]]:
        """按字段名搜索所有文档.

        Args:
            query: 搜索关键词

        Returns:
            匹配结果列表
        """
        results = []
        query_lower = query.lower()

        for dbc_name in self.list_all():
            entry = self.get(dbc_name)
            if not entry:
                continue

            for field in entry.fields:
                field_name = field.get("name", "")
                if query_lower in field_name.lower():
                    results.append({
                        "dbc_name": dbc_name,
                        "field": field,
                    })

        return results
