"""WDBC 文件头结构."""

import struct
from dataclasses import dataclass

from wow_dbc_tool.core.exceptions import DBCFormatError


@dataclass
class DBCHeader:
    """WDBC 文件头（20 bytes）.

    Attributes:
        magic: 文件魔数，应为 'WDBC'
        record_count: 记录数量
        field_count: 字段数量
        record_size: 每条记录字节数
        string_block_size: 字符串块大小
    """

    magic: str
    record_count: int
    field_count: int
    record_size: int
    string_block_size: int

    # 文件头固定大小
    SIZE: int = 20

    @classmethod
    def from_bytes(cls, data: bytes) -> "DBCHeader":
        """从字节解析文件头.

        Args:
            data: 至少 20 bytes 的字节数据

        Returns:
            DBCHeader 实例

        Raises:
            DBCFormatError: 魔数不正确或数据不足
        """
        if len(data) < cls.SIZE:
            raise DBCFormatError(f"文件头数据不足: 需要 {cls.SIZE} bytes, 实际 {len(data)} bytes")

        magic = data[:4].decode("ascii", errors="replace")
        if magic != "WDBC":
            raise DBCFormatError(f"Invalid WDBC magic: expected 'WDBC', got {magic!r}")

        record_count, field_count, record_size, string_block_size = struct.unpack("<4I", data[4:20])

        # 注意：某些 DBC 文件（如 CharBaseInfo.dbc）的 record_size 不等于 field_count * 4
        # 这是正常的，我们信任文件头声明的尺寸

        return cls(
            magic=magic,
            record_count=record_count,
            field_count=field_count,
            record_size=record_size,
            string_block_size=string_block_size,
        )

    def to_bytes(self) -> bytes:
        """转为字节写入文件.

        Returns:
            20 bytes 的文件头数据
        """
        return b"WDBC" + struct.pack(
            "<4I",
            self.record_count,
            self.field_count,
            self.record_size,
            self.string_block_size,
        )

    def to_dict(self) -> dict:
        """转为字典（JSON 输出）.

        Returns:
            包含文件头信息的字典
        """
        return {
            "magic": self.magic,
            "record_count": self.record_count,
            "field_count": self.field_count,
            "record_size": self.record_size,
            "string_block_size": self.string_block_size,
        }

    @property
    def data_size(self) -> int:
        """记录区总字节数.

        Returns:
            record_count * record_size
        """
        return self.record_count * self.record_size

    @property
    def total_file_size(self) -> int:
        """文件总大小（预估）.

        Returns:
            文件头 + 记录区 + 字符串块
        """
        return self.SIZE + self.data_size + self.string_block_size

    def __repr__(self) -> str:
        return (
            f"DBCHeader(magic='{self.magic}', "
            f"records={self.record_count}, "
            f"fields={self.field_count}, "
            f"record_size={self.record_size}, "
            f"string_block={self.string_block_size})"
        )
