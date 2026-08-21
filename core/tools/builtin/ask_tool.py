"""
向用户提问工具
"""
from langchain_core.tools import tool


@tool
def ask_user(question: str, options: str = "") -> str:
    """
    向用户提问以澄清需求或获取更多信息
    
    Args:
        question: 要问用户的问题
        options: 可选的选项列表，用逗号分隔（如 "选项1,选项2,选项3"）
    
    Returns:
        提示用户回答的信息
    """
    # 构建提示信息
    prompt_lines = [f"问题: {question}"]
    
    if options:
        option_list = [opt.strip() for opt in options.split(',') if opt.strip()]
        if option_list:
            prompt_lines.append("\n可选选项:")
            for i, opt in enumerate(option_list, 1):
                prompt_lines.append(f"  {i}. {opt}")
    
    prompt_lines.append("\n请在对话中回复您的答案。")
    
    return '\n'.join(prompt_lines)
