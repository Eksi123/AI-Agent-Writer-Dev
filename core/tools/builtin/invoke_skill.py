"""
invoke_skill - 统一 Skill 调用入口

允许 Agent 通过 Skill 名称动态调用任何自定义 Skill。
- 纯 Markdown Skill：返回 SKILL.md 正文内容
- 带 scripts/ 的 Skill：懒加载脚本并执行对应工具函数
"""
from langchain_core.tools import tool
from core.agent_logger import logger


@tool
def invoke_skill(skill_name: str, args: str = "{}") -> str:
    """
    调用自定义 Skill。根据 Skill 名称动态决策并执行。
    
    Args:
        skill_name: 要调用的 Skill 名称（如 "sumeru-write", "word_count"）
        args: 工具参数，JSON 格式的字符串（如 '{"path": "test.txt"}'）
              对于纯 Markdown Skill，此参数会被忽略
    
    Returns:
        - 纯 Markdown Skill：返回 SKILL.md 正文内容
        - 带 scripts/ 的 Skill：返回工具执行结果
    
    示例:
        invoke_skill("sumeru-write", "{}")
        invoke_skill("word_count", '{"path": "chapter1.md"}')
    """
    import json
    from core.tools import get_skill_info, get_skill_content, load_skill_scripts, get_tool
    
    # 查找 Skill 注册信息
    skill_info = get_skill_info(skill_name)
    
    if skill_info is None:
        return f"错误：找不到 Skill '{skill_name}'。请检查 Skill 名称是否正确。"
    
    has_scripts = skill_info.get("has_scripts", False)
    
    # 纯 Markdown Skill：返回正文内容
    if not has_scripts:
        content = get_skill_content(skill_name)
        logger.info(f"调用纯 Markdown Skill: {skill_name}，返回 {len(content)} 字符")
        return content
    
    # 带 scripts/ 的 Skill：懒加载并执行工具
    # 先确保 scripts 已加载
    if not skill_info.get("scripts_loaded", False):
        logger.info(f"Skill {skill_name} 的 scripts 未加载，尝试懒加载...")
        loaded = load_skill_scripts(skill_name)
        if not loaded:
            return f"错误：Skill '{skill_name}' 的 scripts 加载失败。"
    
    # 解析参数
    try:
        parsed_args = json.loads(args) if args else {}
    except json.JSONDecodeError as e:
        return f"错误：参数 JSON 解析失败 - {e}"
    
    # 从参数中获取要调用的工具名称
    tool_name = parsed_args.pop("tool_name", None)
    
    if tool_name is None:
        # 如果没有指定 tool_name，尝试使用 skill_name 作为工具名
        tool_name = skill_name
    
    # 查找工具
    tool_instance = get_tool(tool_name)
    
    if tool_instance is None:
        return f"错误：Skill '{skill_name}' 中没有找到工具 '{tool_name}'。"
    
    # 调用工具
    try:
        logger.info(f"调用 Skill {skill_name} 的工具 {tool_name}，参数: {parsed_args}")
        result = tool_instance.invoke(parsed_args)
        return str(result)
    except Exception as e:
        logger.error(f"调用 Skill {skill_name} 的工具 {tool_name} 失败: {e}")
        return f"错误：工具执行失败 - {e}"
