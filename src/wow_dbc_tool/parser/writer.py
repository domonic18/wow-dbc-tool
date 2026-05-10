"""WDBC 文件写入器."""

from pathlib import Path
from typing import Union

from wow_dbc_tool.parser.header import DBCHeader


class DBCWriter:
    """WDBC 文件写入器.

    构建 WDBC 格式文件，支持记录和字符串块的写入。
    保存时自动重建字符串块并去重。

    Attributes:
        path: 输出文件路径
        header: 文件头模板
        records: 原始记录字节列表
        string_block: 字符串块字节数据
        string_offsets: 字符串到偏移量的映射（去重用）
    """

    def __init__(
        self,
        path: Union[str, Path],
        header: DBCHeader,
    ):
        """初始化写入器.

        Args:
            path: 输出文件路径
            header: 文件头模板（record_count 和 string_block_size 会在写入时更新）
        """
        self.path = Path(path)
        self._header_template = header
        self.records: list[bytes] = []
        self._string_block: bytearray = bytearray()
        self._string_offsets: dict[str, int] = {}

    def add_record(self, raw_bytes: bytes) -> None:
        """添加原始记录.

        Args:
            raw_bytes: 记录的原始字节数据

        Raises:
            ValueError: 记录大小与 header 不匹配
        """
        if len(raw_bytes) != self._header_template.record_size:
            raise ValueError(
                f"记录大小不匹配: 预期 {self._header_template.record_size}, "
                f"实际 {len(raw_bytes)}"
            )
        self.records.append(raw_bytes)

    def add_string(self, s: str) -> int:
        """添加字符串到字符串块，返回偏移量.

        自动去重：如果字符串已存在，返回已有偏移量。

        Args:
            s: 要添加的字符串

        Returns:
            字符串在字符串块中的偏移量
        """
        if s in self._string_offsets:
            return self._string_offsets[s]

        offset = len(self._string_block)
        encoded = s.encode("utf-8") + b"\x00"
        self._string_block.extend(encoded)
        self._string_offsets[s] = offset
        return offset

    def write(self) -> None:
        """写入完整 DBC 文件.

        更新 header 中的 record_count 和 string_block_size，
        然后按顺序写入文件头、记录区、字符串块。
        """
        # 更新 header
        header = DBCHeader(
            magic="WDBC",
            record_count=len(self.records),
            field_count=self._header_template.field_count,
            record_size=self._header_template.record_size,
            string_block_size=len(self._string_block),
        )

        with open(self.path, "wb") as f:
            # 1. 写入文件头
            f.write(header.to_bytes())

            # 2. 写入记录区
            for record in self.records:
                f.write(record)

            # 3. 写入字符串块
            f.write(self._string_block)

    @property
    def string_block(self) -> bytes:
        """获取当前字符串块内容.

        Returns:
            字符串块字节数据
        """
        return bytes(self._string_block)

    def __repr__(self) -> str:
        return (
            f"DBCWriter({self.path}, "
            f"records={len(self.records)}, "
            f"strings={len(self._string_offsets)})"
        )
