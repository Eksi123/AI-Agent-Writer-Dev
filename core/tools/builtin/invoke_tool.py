"""
invoke_custom_tool - 自定义工具调用桥接器

允许 Agent 通过工具名称和参数动态调用自定义 Skill 工具。
支持懒加载：首次调用时才加载对应的 scripts/ 目录。
"""
from langchain_core.tools import tool
from core.agent_logger import logger


@tool
def invoke_custom_tool(tool_name: str, args: str = "{}") -> str:
    """
    调用自定义工具。当你需要使用自定义 Skill 提供的工具时，调用此函数。
    
    Args:
        tool_name: 要调用的工具名称（如 "word_count", "file_info"）
        args: 工具参数，JSON 格式的字符串（如 '{"path": "test.txt"}'）
    
    Returns:
        工具执行结果
    
    示例:
        invoke_custom_tool("word_count", '{"path": "chapter1.md"}')
    """
    import json
    from core.tools import get_tool, _load_custom_tool_lazy
    
    # 尝试获取工具，如果未加载则懒加载
    tool_instance = get_tool(tool_name)
    
    if tool_instance is None:
        # 尝试懒加载
        logger.info(f"工具 {tool_name} 未加载，尝试懒加载...")
        loaded = _load_custom_tool_lazy(tool_name)
        
        if not loaded:
            return f"错误：找不到自定义工具 '{tool_name}'。请检查工具名称是否正确。"
        
        tool_instance = get_tool(tool_name)
        
        if tool_instance is None:
            return f"错误：工具 '{tool_name}' 加载失败。"
    
    # 解析参数
    try:
        parsed_args = json.loads(args) if args else {}
    except json.JSONDecodeError as e:
        return f"错误：参数 JSON 解析失败 - {e}"
    
    # 调用工具
    try:
        logger.info(f"调用自定义工具: {tool_name}，参数: {parsed_args}")
        result = tool_instance.invoke(parsed_args)
        return str(result)
    except Exception as e:
        logger.error(f"调用自定义工具 {tool_name} 失败: {e}")
        return f"错误：工具执行失败 - {e}"
