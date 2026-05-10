"""WDBC 文件读取器."""

from __future__ import annotations

from pathlib import Path

from wow_dbc_tool.core.exceptions import DBCFormatError
from wow_dbc_tool.parser.header import DBCHeader


class DBCReader:
    """WDBC 文件读取器.

    解析 WDBC 格式文件，提取文件头、记录区和字符串块。

    Attributes:
        path: 文件路径
        header: 解析后的文件头
        records: 原始记录字节列表
        string_block: 字符串块字节数据
    """

    def __init__(self, path: str | Path):
        """初始化读取器.

        Args:
            path: DBC 文件路径
        """
        self.path = Path(path)
        self.header: DBCHeader | None = None
        self.records: list[bytes] = []
        self.string_block: bytes = b""

    def read(self) -> None:
        """解析整个 DBC 文件.

        Raises:
            DBCFormatError: 文件格式错误
            FileNotFoundError: 文件不存在
        """
        if not self.path.exists():
            raise FileNotFoundError(f"DBC 文件不存在: {self.path}")

        with open(self.path, "rb") as f:
            # 1. 读取并验证文件头
            header_data = f.read(DBCHeader.SIZE)
            self.header = DBCHeader.from_bytes(header_data)

            # 2. 读取所有记录
            records_data = f.read(self.header.data_size)
            if len(records_data) < self.header.data_size:
                raise DBCFormatError(
                    f"记录区数据不足: 需要 {self.header.data_size}, " f"实际 {len(records_data)}"
                )

            self.records = [
                records_data[i : i + self.header.record_size]
                for i in range(0, self.header.data_size, self.header.record_size)
            ]

            # 3. 读取字符串块
            self.string_block = f.read(self.header.string_block_size)
            if len(self.string_block) < self.header.string_block_size:
                raise DBCFormatError(
                    f"字符串块数据不足: 需要 {self.header.string_block_size}, "
                    f"实际 {len(self.string_block)}"
                )

    def get_string(self, offset: int) -> str:
        """从字符串块获取字符串.

        从指定偏移量开始读取，直到遇到空字节 \\0。

        Args:
            offset: 字符串在字符串块中的偏移量

        Returns:
            解码后的字符串

        Raises:
            DBCFormatError: 偏移量超出范围或找不到终止符
        """
        if offset < 0 or offset >= len(self.string_block):
            raise DBCFormatError(
                f"字符串偏移量越界: offset={offset}, " f"string_block_size={len(self.string_block)}"
            )

        # 从 offset 开始找到 \\0
        end = self.string_block.find(b"\x00", offset)
        if end == -1:
            raise DBCFormatError(f"字符串块中找不到终止符: offset={offset}")

        raw = self.string_block[offset:end]
        # DBC 字符串通常使用 UTF-8，但可能有 Latin-1 编码
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("latin-1")

    def __repr__(self) -> str:
        if self.header is None:
            return f"DBCReader({self.path}, not loaded)"
        return (
            f"DBCReader({self.path}, "
            f"records={len(self.records)}, "
            f"string_block={len(self.string_block)})"
        )
