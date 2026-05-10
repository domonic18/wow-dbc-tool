"""测试 Wowdev Wiki 爬虫模块.

注意：这些测试使用 mock 避免实际网络请求。
"""

from unittest.mock import MagicMock, patch

import pytest

from wow_dbc_tool.doc_store import DocEntry
from wow_dbc_tool.wowdev_crawler import WowdevWikiCrawler


class TestWowdevWikiCrawler:
    """测试 WowdevWikiCrawler 类."""

    def test_init_default_dir(self):
        """测试默认目录初始化."""
        crawler = WowdevWikiCrawler()
        assert crawler.BASE_URL == "https://wowdev.wiki"
        assert crawler.output_dir is not None

    def test_init_custom_dir(self, tmp_path):
        """测试自定义目录初始化."""
        crawler = WowdevWikiCrawler(tmp_path)
        assert crawler.output_dir == tmp_path

    def test_common_dbcs_list(self):
        """测试常见 DBC 列表."""
        assert "Spell.dbc" in WowdevWikiCrawler.COMMON_DBCS
        assert "Item.dbc" in WowdevWikiCrawler.COMMON_DBCS
        assert len(WowdevWikiCrawler.COMMON_DBCS) >= 10

    def test_fetch_dbc_page_success(self):
        """测试成功获取页面."""
        pytest.importorskip("requests", reason="需要 requests")
        crawler = WowdevWikiCrawler()
        mock_html = "<html><body>Test</body></html>"

        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = mock_html
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            result = crawler.fetch_dbc_page("Spell.dbc")
            assert result == mock_html
            mock_get.assert_called_once_with(
                "https://wowdev.wiki/Spell.dbc", timeout=30
            )

    def test_fetch_dbc_page_failure(self):
        """测试获取页面失败."""
        pytest.importorskip("requests", reason="需要 requests")
        crawler = WowdevWikiCrawler()

        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            result = crawler.fetch_dbc_page("Spell.dbc")
            assert result is None

    def test_parse_dbc_fields_with_valid_html(self):
        """测试解析有效 HTML."""
        pytest.importorskip("bs4", reason="需要 beautifulsoup4")
        crawler = WowdevWikiCrawler()
        html = """
        <html>
        <body>
            <table class="wikitable">
                <tr><th>Name</th><th>Type</th><th>Offset</th><th>Description</th></tr>
                <tr><td>ID</td><td>uint32</td><td>0</td><td>唯一标识</td></tr>
                <tr><td>Name</td><td>string</td><td>4</td><td>名称</td></tr>
            </table>
        </body>
        </html>
        """

        fields = crawler.parse_dbc_fields(html)
        assert len(fields) == 2
        assert fields[0]["name"] == "ID"
        assert fields[0]["type"] == "uint32"
        assert fields[0]["offset"] == "0"
        assert fields[1]["name"] == "Name"

    def test_parse_dbc_fields_empty_html(self):
        """测试解析空 HTML."""
        pytest.importorskip("bs4", reason="需要 beautifulsoup4")
        crawler = WowdevWikiCrawler()
        fields = crawler.parse_dbc_fields("<html></html>")
        assert fields == []

    def test_sync_dbc_success(self):
        """测试同步单个 DBC."""
        pytest.importorskip("requests", reason="需要 requests")
        pytest.importorskip("bs4", reason="需要 beautifulsoup4")
        crawler = WowdevWikiCrawler()
        html = """
        <html>
        <body>
            <table class="wikitable">
                <tr><th>Name</th><th>Type</th><th>Offset</th></tr>
                <tr><td>ID</td><td>uint32</td><td>0</td></tr>
            </table>
        </body>
        </html>
        """

        with patch.object(crawler, "fetch_dbc_page", return_value=html):
            entry = crawler.sync_dbc("Test.dbc")
            assert entry is not None
            assert entry.name == "Test.dbc"
            assert entry.field_count == 1
            assert len(entry.fields) == 1
            assert entry.fields[0]["name"] == "ID"

    def test_sync_dbc_fetch_failure(self):
        """测试同步失败（获取失败）."""
        crawler = WowdevWikiCrawler()

        with patch.object(crawler, "fetch_dbc_page", return_value=None):
            entry = crawler.sync_dbc("Test.dbc")
            assert entry is None

    def test_sync_dbc_parse_failure(self):
        """测试同步失败（解析失败）."""
        pytest.importorskip("bs4", reason="需要 beautifulsoup4")
        crawler = WowdevWikiCrawler()

        with patch.object(crawler, "fetch_dbc_page", return_value="<html></html>"):
            entry = crawler.sync_dbc("Test.dbc")
            assert entry is None

    def test_sync_all(self):
        """测试同步多个 DBC."""
        pytest.importorskip("requests", reason="需要 requests")
        pytest.importorskip("bs4", reason="需要 beautifulsoup4")
        crawler = WowdevWikiCrawler()
        html = """
        <html>
        <body>
            <table class="wikitable">
                <tr><th>Name</th><th>Type</th><th>Offset</th></tr>
                <tr><td>ID</td><td>uint32</td><td>0</td></tr>
            </table>
        </body>
        </html>
        """

        with patch.object(crawler, "fetch_dbc_page", return_value=html):
            results = crawler.sync_all(["A.dbc", "B.dbc"])
            assert len(results) == 2
            assert results["A.dbc"] is not None
            assert results["B.dbc"] is not None

    def test_sync_all_empty_list(self):
        """测试同步默认列表."""
        crawler = WowdevWikiCrawler()

        with patch.object(crawler, "fetch_dbc_page", return_value=None):
            results = crawler.sync_all()
            # 默认列表有多个 DBC，但都会失败（mock 返回 None）
            assert len(results) == len(WowdevWikiCrawler.COMMON_DBCS)
            for entry in results.values():
                assert entry is None

    def test_save_to_store(self, tmp_path):
        """测试保存到 DocStore."""
        crawler = WowdevWikiCrawler(tmp_path)
        entry = DocEntry(name="Test.dbc", title="Test")
        results = {"Test.dbc": entry}

        saved = crawler.save_to_store(results)
        assert saved["Test.dbc"] is True
        assert (tmp_path / "Test.md").exists()

    def test_sync_and_save(self, tmp_path):
        """测试同步并保存."""
        pytest.importorskip("requests", reason="需要 requests")
        pytest.importorskip("bs4", reason="需要 beautifulsoup4")
        crawler = WowdevWikiCrawler(tmp_path)
        html = """
        <html>
        <body>
            <table class="wikitable">
                <tr><th>Name</th><th>Type</th><th>Offset</th></tr>
                <tr><td>ID</td><td>uint32</td><td>0</td></tr>
            </table>
        </body>
        </html>
        """

        with patch.object(crawler, "fetch_dbc_page", return_value=html):
            results = crawler.sync_and_save(["Test.dbc"])
            assert results["Test.dbc"] is True
            assert (tmp_path / "Test.md").exists()
