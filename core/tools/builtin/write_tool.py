"""
文件写入工具
"""
import os
from langchain_core.tools import tool


@tool
def write_file(file_path: str, content: str, overwrite: bool = False) -> str:
    """
    将内容写入指定文件
    
    Args:
        file_path: 文件的绝对路径或相对路径
        content: 要写入的内容
        overwrite: 是否覆盖已存在的文件，默认为 False（追加模式）
    
    Returns:
        操作结果信息
    """
    try:
        # 规范化路径
        abs_path = os.path.abspath(file_path)
        
        # 确保目录存在
        dir_path = os.path.dirname(abs_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        
        # 写入模式
        mode = 'w' if overwrite else 'a'
        action = "覆盖写入" if overwrite else "追加写入"
        
        with open(abs_path, mode, encoding='utf-8') as f:
            f.write(content)
        
        # 统计信息
        line_count = content.count('\n') + (1 if content and not content.endswith('\n') else 0)
        char_count = len(content)
        
        return f"成功: {action}到文件 {abs_path}\n写入 {line_count} 行，{char_count} 字符"
        
    except Exception as e:
        return f"错误: 写入文件失败 - {str(e)}"
