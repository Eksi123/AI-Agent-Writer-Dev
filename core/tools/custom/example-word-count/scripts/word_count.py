"""
字数统计工具
"""
from langchain_core.tools import tool


@tool
def word_count(text: str) -> str:
    """
    统计文本的字数和行数
    
    Args:
        text: 要统计的文本内容
    
    Returns:
        字数和行数统计结果
    """
    try:
        char_count = len(text.replace(' ', '').replace('\n', '').replace('\t', ''))
        total_char_count = len(text)
        line_count = text.count('\n') + 1 if text else 0
        word_count = len(text.split()) if text.strip() else 0
        
        return (
            f"字数统计结果:\n"
            f"  - 字符数（不含空格）: {char_count}\n"
            f"  - 字符数（含空格）: {total_char_count}\n"
            f"  - 词数: {word_count}\n"
            f"  - 行数: {line_count}"
        )
    except Exception as e:
        return f"统计失败: {str(e)}"
