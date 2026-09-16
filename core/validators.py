"""
公共校验模块

提供输入参数校验、配置值校验等通用校验函数。
所有校验函数返回 (is_valid, error_message) 元组，与 project_manager.validate_name() 风格一致。
"""


def validate_volume_chapter(volume: int, chapter: int) -> tuple:
    """
    校验卷号和章节号是否为正整数且在合理范围（1-999）

    Args:
        volume: 卷号
        chapter: 章节号

    Returns:
        (is_valid, error_message): 校验是否通过，以及错误信息
    """
    if not isinstance(volume, int) or volume < 1 or volume > 999:
        return False, f"卷号必须为 1-999 的整数，当前值: {volume}"
    if not isinstance(chapter, int) or chapter < 1 or chapter > 999:
        return False, f"章节号必须为 1-999 的整数，当前值: {chapter}"
    return True, ""


def validate_user_request(text: str, max_length: int = 10000) -> tuple:
    """
    校验用户输入是否合法

    Args:
        text: 用户输入文本
        max_length: 最大允许长度

    Returns:
        (is_valid, error_message): 校验是否通过，以及错误信息
    """
    if not text or not text.strip():
        return False, "输入内容不能为空"
    if len(text) > max_length:
        return False, f"输入内容过长（{len(text)}/{max_length} 字符）"
    return True, ""


def validate_temperature(value: float) -> float:
    """
    将温度值限制在 [0, 2] 范围内

    Args:
        value: 原始温度值

    Returns:
        修正后的温度值
    """
    return max(0.0, min(2.0, float(value)))


def validate_top_p(value: float) -> float:
    """
    将 top_p 值限制在 [0, 1] 范围内

    Args:
        value: 原始 top_p 值

    Returns:
        修正后的 top_p 值
    """
    return max(0.0, min(1.0, float(value)))


def validate_port(value: int) -> tuple:
    """
    校验端口号是否在合法范围（1-65535）

    Args:
        value: 端口号

    Returns:
        (is_valid, error_message): 校验是否通过，以及错误信息
    """
    if not isinstance(value, int) or value < 1 or value > 65535:
        return False, f"端口号必须为 1-65535 的整数，当前值: {value}"
    return True, ""
