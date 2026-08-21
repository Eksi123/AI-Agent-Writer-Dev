"""
文件信息查询工具
"""
import os
from datetime import datetime
from langchain_core.tools import tool


@tool
def file_info(file_path: str) -> str:
    """
    获取文件的详细信息（大小、创建时间、修改时间等）
    
    Args:
        file_path: 文件的绝对路径或相对路径
    
    Returns:
        文件详细信息
    """
    try:
        abs_path = os.path.abspath(file_path)
        
        if not os.path.exists(abs_path):
            return f"错误: 文件不存在 - {abs_path}"
        
        stat = os.stat(abs_path)
        file_type = "文件" if os.path.isfile(abs_path) else "目录" if os.path.isdir(abs_path) else "其他"
        
        size = stat.st_size
        size_str = f"{size} B" if size < 1024 else f"{size / 1024:.2f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.2f} MB"
        
        create_time = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
        modify_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        
        result = (
            f"文件信息:\n"
            f"  - 路径: {abs_path}\n"
            f"  - 类型: {file_type}\n"
            f"  - 大小: {size_str} ({size} 字节)\n"
            f"  - 创建时间: {create_time}\n"
            f"  - 修改时间: {modify_time}"
        )
        
        if os.path.isfile(abs_path):
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    line_count = sum(1 for _ in f)
                result += f"\n  - 行数: {line_count}"
            except:
                result += "\n  - 行数: 无法读取"
        
        return result
    except Exception as e:
        return f"获取文件信息失败: {str(e)}"
