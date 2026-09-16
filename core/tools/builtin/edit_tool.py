"""
文件编辑工具

提供文件内容替换功能，支持单处替换和全局替换。
与 write_tool 共享项目目录安全限制。
"""
import os
from langchain_core.tools import tool
from core.tools.builtin.write_tool import get_allowed_project_dir


@tool
def edit_file(file_path: str, old_text: str, new_text: str, replace_all: bool = False) -> str:
    """
    编辑文件：将文件中的 old_text 替换为 new_text
    
    Args:
        file_path: 文件的绝对路径或相对路径
        old_text: 要被替换的文本
        new_text: 替换后的新文本
        replace_all: 是否替换所有匹配项，默认为 False（只替换第一个）
    
    Returns:
        操作结果信息
    """
    try:
        abs_path = os.path.abspath(file_path)
        
        # 安全检查：确保路径在允许的项目目录内（使用 normpath 防止路径遍历攻击）
        allowed_dir = get_allowed_project_dir()
        if allowed_dir:
            norm_path = os.path.normpath(abs_path)
            norm_allowed = os.path.normpath(allowed_dir)
            if not norm_path.startswith(norm_allowed + os.sep) and norm_path != norm_allowed:
                return f"错误: 不允许编辑项目目录外的文件。允许目录: {allowed_dir}，尝试编辑: {abs_path}"
        
        if not os.path.exists(abs_path):
            return f"错误: 文件不存在 - {abs_path}"
        
        if not os.path.isfile(abs_path):
            return f"错误: 路径不是文件 - {abs_path}"
        
        # 读取文件
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查 old_text 是否存在
        if old_text not in content:
            return f"错误: 未找到要替换的文本\n文件: {abs_path}"
        
        # 执行替换：replace_all=True 时替换所有匹配，否则只替换第一个
        if replace_all:
            new_content = content.replace(old_text, new_text)
            replace_count = content.count(old_text)
        else:
            new_content = content.replace(old_text, new_text, 1)
            replace_count = 1
        
        # 写回文件
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return f"成功: 替换了 {replace_count} 处\n文件: {abs_path}"
        
    except Exception as e:
        return f"错误: 编辑文件失败 - {str(e)}"
