"""
文件写入工具

提供安全的文件写入功能，通过全局变量控制允许写入的项目目录。
"""
import os
from langchain_core.tools import tool
from typing import Optional


# 全局变量：当前允许写入的项目目录（由 NovelWriter 等 Agent 设置）
_allowed_project_dir: Optional[str] = None


def set_allowed_project_dir(project_dir: str):
    """设置当前允许写入的项目目录"""
    global _allowed_project_dir
    _allowed_project_dir = os.path.abspath(project_dir)


def get_allowed_project_dir() -> Optional[str]:
    """获取当前允许的项目目录"""
    return _allowed_project_dir


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
        abs_path = os.path.abspath(file_path)
        
        # 安全检查：确保路径在允许的项目目录内
        allowed_dir = get_allowed_project_dir()
        if allowed_dir:
            if not abs_path.startswith(allowed_dir + os.sep) and abs_path != allowed_dir:
                return f"错误: 不允许写入项目目录外的文件。允许目录: {allowed_dir}，尝试写入: {abs_path}"
        
        # 自动创建目录
        dir_path = os.path.dirname(abs_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        
        # 根据 overwrite 参数选择写入模式：'w' 覆盖，'a' 追加
        mode = 'w' if overwrite else 'a'
        action = "覆盖写入" if overwrite else "追加写入"
        
        with open(abs_path, mode, encoding='utf-8') as f:
            f.write(content)
        
        # 统计写入的行数和字符数
        line_count = content.count('\n') + (1 if content and not content.endswith('\n') else 0)
        char_count = len(content)
        
        return f"成功: {action}到文件 {abs_path}\n写入 {line_count} 行，{char_count} 字符"
        
    except Exception as e:
        return f"错误: 写入文件失败 - {str(e)}"
