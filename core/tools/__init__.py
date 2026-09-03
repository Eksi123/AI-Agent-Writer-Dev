"""
工具注册表模块

管理 Agent 可用的工具，包括自动注册内置工具、热加载用户自定义工具、提供工具查询接口。
工具注册表是一个全局字典，存储工具名称到 BaseTool 实例的映射。

自定义 Skill 机制：
- 纯 Markdown 的 SKILL.md 会被解析 frontmatter，根据 applyTo 字段注入到对应 Agent 的 system_prompt
- 带 scripts/ 的 Skill 会被注册为可调用工具，自动绑定到所有 Agent
"""
import os
import re
import importlib
import importlib.util
from typing import List, Dict, Any, Optional
from langchain_core.tools import BaseTool
from core.agent_logger import logger


# 全局工具注册表，存储工具名称到 BaseTool 实例的映射
_tool_registry: Dict[str, BaseTool] = {}

# Skill 提示词注册表，存储 skill_name -> {"content": str, "apply_to": List[str]}
_skill_prompts: Dict[str, Dict[str, Any]] = {}


def register_tool(tool: BaseTool) -> None:
    """注册单个工具到全局注册表，已存在的工具会被覆盖"""
    tool_name = tool.name
    if tool_name in _tool_registry:
        logger.warning(f"工具 {tool_name} 已存在，将被覆盖")
    
    _tool_registry[tool_name] = tool
    logger.debug(f"工具已注册: {tool_name}")


def register_tools(tools: List[BaseTool]) -> None:
    """批量注册多个工具"""
    for tool in tools:
        register_tool(tool)


def get_tool(tool_name: str) -> Optional[BaseTool]:
    """根据名称获取工具，不存在时返回 None"""
    return _tool_registry.get(tool_name)


def get_all_tools() -> List[BaseTool]:
    """获取所有已注册的工具"""
    return list(_tool_registry.values())


def _get_custom_tool_names() -> List[str]:
    """获取所有自定义工具的名称（非内置工具）"""
    return [
        name for name in _tool_registry.keys()
        if not name.startswith("builtin_")
    ]


def _parse_skill_frontmatter(skill_content: str) -> Dict[str, Any]:
    """
    解析 SKILL.md 的 YAML frontmatter。
    
    格式示例：
    ---
    name: sumeru-write
    description: 须弥写作技能
    applyTo: writer, outline_polisher
    ---
    
    Returns:
        解析后的字典，包含 name, description, applyTo 等字段。
        如果无 frontmatter 则返回空字典。
    """
    frontmatter_pattern = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
    match = frontmatter_pattern.match(skill_content)
    
    if not match:
        return {}
    
    frontmatter_str = match.group(1)
    result = {}
    
    for line in frontmatter_str.strip().split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            
            # 处理逗号分隔的列表值（如 applyTo: writer, outline_polisher）
            if ',' in value:
                result[key] = [v.strip() for v in value.split(',')]
            else:
                result[key] = value
    
    return result


def get_skill_prompts_for_agent(agent_name: str) -> List[str]:
    """
    获取应该注入到指定 Agent 的 system_prompt 的 Skill 提示词列表。
    
    匹配规则：
    - Skill 的 applyTo 字段包含 agent_name（不区分大小写）
    - Skill 的 applyTo 字段包含 "all"（不区分大小写）
    - Skill 没有 applyTo 字段时，默认注入到所有 Agent
    
    Args:
        agent_name: Agent 名称（如 "NovelWriter", "ContentPolisher"）
    
    Returns:
        匹配的 Skill 提示词内容列表
    """
    agent_lower = agent_name.lower()
    prompts = []
    
    for skill_name, skill_info in _skill_prompts.items():
        apply_to = skill_info.get("apply_to", [])
        
        # 没有 applyTo 字段时，默认注入到所有 Agent
        if not apply_to:
            prompts.append(skill_info["content"])
            logger.debug(f"Skill {skill_name} 无 applyTo，默认注入到 {agent_name}")
            continue
        
        # 检查是否匹配
        for target in apply_to:
            target_lower = target.lower()
            if target_lower == "all" or target_lower == agent_lower:
                prompts.append(skill_info["content"])
                logger.debug(f"Skill {skill_name} 匹配 {agent_name}（applyTo: {target}）")
                break
    
    return prompts


def get_custom_tools_info() -> List[Dict[str, str]]:
    """
    获取所有自定义工具（带 scripts/ 的 Skill）的名称和描述信息。
    
    用于注入到 Agent 的 system_prompt，让 Agent 根据 description 动态决策是否调用。
    
    Returns:
        包含 {"name": str, "description": str} 的字典列表
    """
    custom_names = _get_custom_tool_names()
    return [
        {
            "name": name,
            "description": _tool_registry[name].description
        }
        for name in custom_names
        if name in _tool_registry
    ]


def get_tools_by_names(tool_names: List[str]) -> List[BaseTool]:
    """
    根据名称列表获取工具，不存在的名称会被忽略。
    仅返回指定的内置工具，不再自动追加自定义工具。
    """
    return [
        _tool_registry[name] 
        for name in tool_names 
        if name in _tool_registry
    ]


def list_tool_names() -> List[str]:
    """列出所有已注册工具的名称"""
    return list(_tool_registry.keys())


def _load_builtin_tools() -> None:
    """
    自动扫描 builtin/ 目录下的所有 .py 文件，动态导入并注册 BaseTool 实例。
    
    加载流程：
    1. 遍历 builtin/ 目录下的所有 Python 文件（排除以 _ 开头的文件）
    2. 动态导入每个模块
    3. 扫描模块中的属性，查找 BaseTool 实例或 @tool 装饰的函数
    4. 将找到的工具注册到全局注册表
    """
    builtin_dir = os.path.join(os.path.dirname(__file__), "builtin")
    
    if not os.path.exists(builtin_dir):
        logger.warning(f"内置工具目录不存在: {builtin_dir}")
        return
    
    for filename in os.listdir(builtin_dir):
        if filename.endswith(".py") and not filename.startswith("_"):
            module_name = filename[:-3]
            
            try:
                full_module_name = f"core.tools.builtin.{module_name}"
                module = importlib.import_module(full_module_name)
                
                # 扫描模块属性，查找 BaseTool 实例或 @tool 装饰的函数
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, BaseTool):
                        register_tool(attr)
                    elif hasattr(attr, "__wrapped__") and isinstance(getattr(attr, "__wrapped__", None), BaseTool):
                        register_tool(attr)
                
                logger.debug(f"内置工具模块已加载: {module_name}")
                
            except Exception as e:
                logger.error(f"加载内置工具模块 {module_name} 失败: {e}")


def _load_custom_tools() -> None:
    """
    加载用户自定义工具（Skill 格式）。
    
    每个 Skill 必须是 custom/ 下的独立文件夹，包含：
    - SKILL.md：工具说明书（必须）
    - scripts/：Python 脚本目录（可选）
    
    支持热加载：每次调用都会重新扫描目录。
    """
    custom_dir = os.path.join(os.path.dirname(__file__), "custom")
    
    if not os.path.exists(custom_dir):
        logger.debug(f"自定义工具目录不存在: {custom_dir}")
        return
    
    for skill_name in os.listdir(custom_dir):
        skill_dir = os.path.join(custom_dir, skill_name)
        
        if not os.path.isdir(skill_dir) or skill_name.startswith("_"):
            continue
        
        skill_md_path = os.path.join(skill_dir, "SKILL.md")
        if not os.path.exists(skill_md_path):
            logger.warning(f"Skill {skill_name} 缺少 SKILL.md，跳过")
            continue
        
        try:
            _load_skill(skill_name, skill_dir, skill_md_path)
            logger.debug(f"自定义 Skill 已加载: {skill_name}")
            
        except Exception as e:
            logger.error(f"加载自定义 Skill {skill_name} 失败: {e}")


def _strip_frontmatter(skill_content: str) -> str:
    """
    去掉 SKILL.md 的 YAML frontmatter 部分，返回纯正文内容。
    """
    frontmatter_pattern = re.compile(r'^---\s*\n.*?\n---\s*\n', re.DOTALL)
    return frontmatter_pattern.sub('', skill_content, count=1).strip()


def _load_skill(skill_name: str, skill_dir: str, skill_md_path: str) -> None:
    """
    加载单个 Skill：
    1. 读取 SKILL.md，解析 frontmatter 获取 applyTo 字段
    2. 将 Skill 正文（去掉 frontmatter）存入 _skill_prompts 供 Agent 注入
    3. 动态加载 scripts/ 目录下的 Python 模块注册为可调用工具
    """
    with open(skill_md_path, 'r', encoding='utf-8') as f:
        skill_content = f.read()
    
    # 解析 frontmatter
    frontmatter = _parse_skill_frontmatter(skill_content)
    body = _strip_frontmatter(skill_content)
    
    # 提取 applyTo 字段，转为小写列表
    apply_to_raw = frontmatter.get("applyTo", "")
    if isinstance(apply_to_raw, list):
        apply_to = [t.strip().lower() for t in apply_to_raw]
    elif isinstance(apply_to_raw, str) and apply_to_raw:
        apply_to = [t.strip().lower() for t in apply_to_raw.split(',')]
    else:
        apply_to = []
    
    # 存储 Skill 提示词（正文部分）
    _skill_prompts[skill_name] = {
        "content": body,
        "apply_to": apply_to,
    }
    logger.debug(f"Skill {skill_name} 提示词已存储（applyTo={apply_to or 'all'}, {len(body)} 字符）")
    
    # 查找并加载 scripts/ 目录下的所有 Python 文件
    scripts_dir = os.path.join(skill_dir, "scripts")
    
    if os.path.exists(scripts_dir):
        for filename in os.listdir(scripts_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                module_name = filename[:-3]
                file_path = os.path.join(scripts_dir, filename)
                
                try:
                    # 使用 importlib.util 从文件路径动态加载模块
                    spec = importlib.util.spec_from_file_location(
                        f"core.tools.custom.{skill_name}.scripts.{module_name}",
                        file_path
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        # 扫描模块属性，查找并注册 BaseTool 实例
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if isinstance(attr, BaseTool):
                                register_tool(attr)
                            elif hasattr(attr, "__wrapped__") and isinstance(getattr(attr, "__wrapped__", None), BaseTool):
                                register_tool(attr)
                
                except Exception as e:
                    logger.error(f"加载 Skill {skill_name} 的脚本 {module_name} 失败: {e}")
    
    logger.debug(f"Skill {skill_name} 的 SKILL.md 已读取（{len(skill_content)} 字符）")


def reload_custom_tools() -> None:
    """
    重新加载所有自定义工具（热加载）。
    清空非内置工具和 Skill 提示词后重新扫描 custom/ 目录。
    """
    # 清空非内置工具，保留内置工具
    custom_tool_names = [
        name for name in _tool_registry.keys()
        if not name.startswith("builtin_")
    ]
    for name in custom_tool_names:
        del _tool_registry[name]
    
    # 清空 Skill 提示词注册表
    _skill_prompts.clear()
    
    _load_custom_tools()
    logger.info(f"自定义工具已重新加载，当前工具总数: {len(_tool_registry)}，Skill提示词: {len(_skill_prompts)} 个")


# 模块加载时自动注册内置工具和自定义工具
_load_builtin_tools()
_load_custom_tools()
logger.info(f"工具加载完成，共 {len(_tool_registry)} 个工具")


if __name__ == "__main__":
    print("已注册的工具:")
    for name in list_tool_names():
        tool = get_tool(name)
        print(f"  - {name}: {tool.description if tool else 'N/A'}")
