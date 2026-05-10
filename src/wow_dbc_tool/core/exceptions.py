"""自定义异常体系."""


class DBCError(Exception):
    """DBC 操作基类异常."""

    pass


class DBCFormatError(DBCError):
    """文件格式错误（Magic 不对、尺寸不匹配等）."""

    pass


class DBCSchemaError(DBCError):
    """字段定义错误（找不到定义、类型不匹配等）."""

    pass


class DBCQueryError(DBCError):
    """查询错误（字段不存在、操作符不支持等）."""

    pass


class DBCDiffError(DBCError):
    """Diff 错误（key_field 不存在等）."""

    pass


class DBCNotLoadedError(DBCError):
    """文件尚未加载."""

    pass
