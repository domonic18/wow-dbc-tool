"""Wowdev Wiki 爬虫 - DBC 字段定义同步.

从 https://wowdev.wiki/ 下载 DBC 字段定义。
可选模块，不导入时不影响核心功能。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from wow_dbc_tool.utils.doc_store import DocEntry, DocStore


class WowdevWikiCrawler:
    """Wowdev Wiki 爬虫.

    从 wowdev.wiki 下载 DBC 字段定义。
    可选模块，需要 requests 和 beautifulsoup4。
    """

    BASE_URL = "https://wowdev.wiki"

    # 常见 DBC 文件列表（3.3.5a）
    COMMON_DBCS = [
        "Achievement.dbc",
        "Achievement_Category.dbc",
        "AreaTable.dbc",
        "CharTitles.dbc",
        "Faction.dbc",
        "Item.dbc",
        "ItemDisplayInfo.dbc",
        "Map.dbc",
        "QuestInfo.dbc",
        "SkillLine.dbc",
        "Spell.dbc",
        "SpellIcon.dbc",
        "Talent.dbc",
    ]

    def __init__(self, output_dir: str | Path | None = None) -> None:
        """初始化爬虫.

        Args:
            output_dir: 输出目录，None 使用默认 docs/definitions/
        """
        self.output_dir = Path(output_dir) if output_dir else self._default_output_dir()
        self._store: DocStore | None = None

    def _default_output_dir(self) -> Path:
        """获取默认输出目录."""
        try:
            import wow_dbc_tool
            pkg_dir = Path(wow_dbc_tool.__file__).parent
            project_root = pkg_dir.parent.parent
            return project_root / "docs" / "definitions"
        except ImportError:
            return Path.cwd() / "docs" / "definitions"

    def _get_store(self) -> DocStore:
        """获取 DocStore 实例."""
        if self._store is None:
            self._store = DocStore(self.output_dir)
        return self._store

    def fetch_dbc_page(self, dbc_name: str) -> str | None:
        """获取 DBC 页面 HTML.

        Args:
            dbc_name: DBC 文件名（如 "Spell.dbc"）

        Returns:
            HTML 内容，失败返回 None
        """
        try:
            import requests
            url = f"{self.BASE_URL}/{dbc_name}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception:
            return None

    def parse_dbc_fields(self, html: str) -> list[dict[str, Any]]:
        """解析 HTML 提取字段定义.

        Args:
            html: 页面 HTML

        Returns:
            字段定义列表
        """
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            fields = []
            # Wiki 页面通常有表格定义字段
            tables = soup.find_all("table", class_="wikitable")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows[1:]:  # 跳过表头
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 3:
                        field: dict[str, Any] = {
                            "name": cells[0].get_text(strip=True),
                            "type": cells[1].get_text(strip=True),
                            "offset": cells[2].get_text(strip=True),
                        }
                        if len(cells) > 3:
                            field["description"] = cells[3].get_text(strip=True)
                        if len(cells) > 4:
                            field["notes"] = cells[4].get_text(strip=True)
                        fields.append(field)

            return fields
        except Exception:
            return []

    def sync_dbc(self, dbc_name: str) -> DocEntry | None:
        """同步单个 DBC 定义.

        Args:
            dbc_name: DBC 文件名

        Returns:
            同步后的文档条目，失败返回 None
        """
        html = self.fetch_dbc_page(dbc_name)
        if html is None:
            return None

        fields = self.parse_dbc_fields(html)
        if not fields:
            return None

        # 尝试解析偏移量为整数
        for field in fields:
            offset = field.get("offset", "")
            if isinstance(offset, str) and offset.isdigit():
                field["offset"] = int(offset)

        # 计算 record_size（假设所有字段 4 字节，简化处理）
        record_size = len(fields) * 4

        entry = DocEntry(
            name=dbc_name,
            title=f"{dbc_name} - DBC 定义",
            source=f"{self.BASE_URL}/{dbc_name}",
            version="3.3.5a",
            last_sync=datetime.now().isoformat(),
            field_count=len(fields),
            record_size=record_size,
            fields=fields,
            overview=f"{dbc_name} 的字段定义，从 Wowdev Wiki 同步。",
            examples=[
                f"wow-dbc-tool query {dbc_name} --filter ID=1 --json",
                f"wow-dbc-tool read {dbc_name} --limit 10 --json",
            ],
        )

        return entry

    def sync_all(self, dbc_names: list[str] | None = None) -> dict[str, DocEntry | None]:
        """同步多个 DBC 定义.

        Args:
            dbc_names: DBC 名称列表，None 同步常见 DBC

        Returns:
            同步结果: {dbc_name: DocEntry | None}
        """
        if dbc_names is None:
            dbc_names = self.COMMON_DBCS

        results: dict[str, DocEntry | None] = {}
        for name in dbc_names:
            results[name] = self.sync_dbc(name)

        return results

    def save_to_store(self, results: dict[str, DocEntry | None]) -> dict[str, bool]:
        """保存同步结果到 DocStore.

        Args:
            results: sync_all 返回的结果

        Returns:
            保存结果: {dbc_name: success}
        """
        store = self._get_store()
        saved: dict[str, bool] = {}

        for name, entry in results.items():
            if entry:
                store.save(entry)
                saved[name] = True
            else:
                saved[name] = False

        return saved

    def sync_and_save(self, dbc_names: list[str] | None = None) -> dict[str, bool]:
        """同步并保存到本地.

        Args:
            dbc_names: DBC 名称列表，None 同步常见 DBC

        Returns:
            保存结果: {dbc_name: success}
        """
        results = self.sync_all(dbc_names)
        return self.save_to_store(results)
