"""
文件读取工具

支持按行范围读取文件内容，用于 Agent 查看文件。
"""
import os
from langchain_core.tools import tool
from core.tools.builtin.write_tool import get_allowed_project_dir


@tool
def read_file(file_path: str, start_line: int = 1, end_line: int = -1) -> str:
    """
    读取指定文件的内容
    
    Args:
        file_path: 文件的绝对路径或相对路径
        start_line: 起始行号（1-based），默认为 1
        end_line: 结束行号（1-based，包含），默认为 -1 表示读取到文件末尾
    
    Returns:
        文件内容字符串，如果文件不存在或读取失败则返回错误信息
    """
    try:
        abs_path = os.path.abspath(file_path)
        
        # 安全检查：确保路径在允许的项目目录内
        allowed_dir = get_allowed_project_dir()
        if allowed_dir:
            norm_path = os.path.normpath(abs_path)
            norm_allowed = os.path.normpath(allowed_dir)
            if not norm_path.startswith(norm_allowed + os.sep) and norm_path != norm_allowed:
                return f"错误: 不允许读取项目目录外的文件。允许目录: {allowed_dir}，尝试读取: {abs_path}"
        
        if not os.path.exists(abs_path):
            return f"错误: 文件不存在 - {abs_path}"
        
        if not os.path.isfile(abs_path):
            return f"错误: 路径不是文件 - {abs_path}"
        
        with open(abs_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 处理行号范围（1-based 转 0-based）
        total_lines = len(lines)
        
        if start_line < 1:
            start_line = 1
        
        if end_line == -1 or end_line > total_lines:
            end_line = total_lines
        
        if start_line > end_line:
            return f"错误: 起始行 {start_line} 大于结束行 {end_line}"
        
        # 提取指定行范围并格式化输出
        selected_lines = lines[start_line - 1:end_line]
        content = ''.join(selected_lines)
        
        return f"文件: {abs_path}\n行范围: {start_line}-{end_line} (共 {total_lines} 行)\n\n{content}"
        
    except UnicodeDecodeError:
        return f"错误: 文件编码不是 UTF-8 - {abs_path}"
    except Exception as e:
        return f"错误: 读取文件失败 - {str(e)}"
