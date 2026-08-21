"""
文件查询工具（按模式匹配）
"""
import os
import glob
from langchain_core.tools import tool


@tool
def glob_search(pattern: str, root_dir: str = ".") -> str:
    """
    按照 glob 模式搜索文件
    
    Args:
        pattern: glob 模式，如 "**/*.py", "*.md", "src/**/*.txt"
        root_dir: 搜索的根目录，默认为当前目录
    
    Returns:
        匹配的文件路径列表，每行一个
    """
    try:
        # 规范化根目录
        abs_root = os.path.abspath(root_dir)
        
        if not os.path.exists(abs_root):
            return f"错误: 目录不存在 - {abs_root}"
        
        if not os.path.isdir(abs_root):
            return f"错误: 路径不是目录 - {abs_root}"
        
        # 执行 glob 搜索
        search_pattern = os.path.join(abs_root, pattern)
        matches = glob.glob(search_pattern, recursive=True)
        
        if not matches:
            return f"未找到匹配的文件\n模式: {pattern}\n目录: {abs_root}"
        
        # 转换为相对路径并排序
        rel_paths = [os.path.relpath(p, abs_root) for p in matches]
        rel_paths.sort()
        
        # 格式化输出
        result_lines = [f"找到 {len(rel_paths)} 个匹配文件:"]
        result_lines.extend(rel_paths)
        
        return '\n'.join(result_lines)
        
    except Exception as e:
        return f"错误: 搜索文件失败 - {str(e)}"
