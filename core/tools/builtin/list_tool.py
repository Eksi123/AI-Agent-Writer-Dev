"""
列出目录内容工具

显示指定目录下的文件和文件夹，支持隐藏文件显示。
"""
import os
from langchain_core.tools import tool
from core.tools.builtin.write_tool import get_allowed_project_dir


@tool
def list_directory(dir_path: str = ".", show_hidden: bool = False) -> str:
    """
    列出指定目录下的文件和文件夹
    
    Args:
        dir_path: 目录路径，默认为当前目录
        show_hidden: 是否显示隐藏文件（以 . 开头），默认为 False
    
    Returns:
        目录内容列表，文件夹以 / 结尾
    """
    try:
        abs_path = os.path.abspath(dir_path)
        
        # 安全检查：确保目录在允许的项目目录内
        allowed_dir = get_allowed_project_dir()
        if allowed_dir:
            norm_path = os.path.normpath(abs_path)
            norm_allowed = os.path.normpath(allowed_dir)
            if not norm_path.startswith(norm_allowed + os.sep) and norm_path != norm_allowed:
                return f"错误: 不允许列出项目目录外的文件。允许目录: {allowed_dir}，尝试列出: {abs_path}"
        
        if not os.path.exists(abs_path):
            return f"错误: 目录不存在 - {abs_path}"
        
        if not os.path.isdir(abs_path):
            return f"错误: 路径不是目录 - {abs_path}"
        
        items = os.listdir(abs_path)
        
        # 过滤隐藏文件（以 . 开头的文件）
        if not show_hidden:
            items = [item for item in items if not item.startswith('.')]
        
        # 分类：文件夹和文件分别排序
        dirs = []
        files = []
        
        for item in items:
            item_path = os.path.join(abs_path, item)
            if os.path.isdir(item_path):
                dirs.append(item + '/')
            else:
                files.append(item)
        
        dirs.sort()
        files.sort()
        
        # 格式化输出
        result_lines = [f"目录: {abs_path}", ""]
        
        if dirs:
            result_lines.append(f"文件夹 ({len(dirs)}):")
            result_lines.extend([f"  {d}" for d in dirs])
            result_lines.append("")
        
        if files:
            result_lines.append(f"文件 ({len(files)}):")
            result_lines.extend([f"  {f}" for f in files])
        
        return '\n'.join(result_lines)
        
    except Exception as e:
        return f"错误: 列出目录失败 - {str(e)}"
