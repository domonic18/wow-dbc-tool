"""Schema 字段定义."""

from dataclasses import dataclass


@dataclass
class FieldDef:
    """DBC 字段定义.

    描述 DBC 文件中一个字段的名称、类型和偏移量。

    Attributes:
        name: 字段名（如 "ID", "Name"）
        type: 类型："uint32", "int32", "float", "string"
        offset: 在记录中的字节偏移（从 0 开始，4 字节对齐）
    """

    name: str
    type: str
    offset: int

    # 支持的类型
    VALID_TYPES = {"uint32", "int32", "float", "string"}

    def __post_init__(self) -> None:
        """验证字段定义."""
        if self.type not in self.VALID_TYPES:
            raise ValueError(f"不支持的字段类型: {self.type!r}, " f"支持的类型: {self.VALID_TYPES}")
        if self.offset < 0:
            raise ValueError(f"字段偏移量不能为负数: {self.offset}")
        if self.offset % 4 != 0:
            raise ValueError(f"字段偏移量必须是 4 的倍数: {self.offset}")

    def to_dict(self) -> dict:
        """转为字典（JSON 输出）.

        Returns:
            包含字段定义信息的字典
        """
        return {
            "name": self.name,
            "type": self.type,
            "offset": self.offset,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FieldDef":
        """从字典创建字段定义.

        Args:
            data: 包含 name, type, offset 的字典

        Returns:
            FieldDef 实例
        """
        return cls(
            name=data["name"],
            type=data["type"],
            offset=data["offset"],
        )

    def __repr__(self) -> str:
        return f"FieldDef(name='{self.name}', type='{self.type}', offset={self.offset})"
