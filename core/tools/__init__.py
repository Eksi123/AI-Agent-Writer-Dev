"""
工具注册表模块

管理 Agent 可用的工具，包括自动注册内置工具、热加载用户自定义工具、提供工具查询接口。
工具注册表是一个全局字典，存储工具名称到 BaseTool 实例的映射。

自定义 Skill 机制：
- 所有 Skill 统一通过 invoke_skill 工具按 name + description 动态决策调用
- 纯 Markdown Skill：调用时返回 SKILL.md 正文内容
- 带 scripts/ 的 Skill：调用时懒加载并执行对应工具函数
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

# 统一 Skill 注册表，存储 skill_name -> {
#   "name": str,           # Skill 名称（来自 frontmatter）
#   "description": str,    # Skill 描述（来自 frontmatter）
#   "content": str,        # SKILL.md 正文（去掉 frontmatter）
#   "has_scripts": bool,   # 是否有 scripts/ 目录
#   "scripts_dir": str,    # scripts/ 目录路径
#   "skill_dir": str,      # Skill 根目录路径
#   "scripts_loaded": bool # scripts 是否已懒加载
# }
_skill_registry: Dict[str, Dict[str, Any]] = {}


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


def get_all_skills_info() -> List[Dict[str, str]]:
    """
    获取所有已注册 Skill 的名称和描述信息。
    
    用于注入到所有 Agent 的 system_prompt，让 Agent 根据 description 动态决策是否调用。
    
    Returns:
        包含 {"name": str, "description": str} 的字典列表
    """
    result = []
    for skill_name, skill_info in _skill_registry.items():
        result.append({
            "name": skill_info["name"],
            "description": skill_info["description"]
        })
    return result


def get_skill_content(skill_name: str) -> Optional[str]:
    """
    获取指定 Skill 的 SKILL.md 正文内容（去掉 frontmatter）。
    
    Args:
        skill_name: Skill 名称
    
    Returns:
        Skill 正文内容，不存在时返回 None
    """
    if skill_name not in _skill_registry:
        return None
    return _skill_registry[skill_name].get("content", "")


def get_skill_info(skill_name: str) -> Optional[Dict[str, Any]]:
    """
    获取指定 Skill 的完整注册信息。
    
    Args:
        skill_name: Skill 名称
    
    Returns:
        Skill 注册信息字典，不存在时返回 None
    """
    return _skill_registry.get(skill_name)


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
    加载单个 Skill 到统一注册表：
    1. 读取 SKILL.md，解析 frontmatter 获取 name 和 description
    2. 将完整信息存入 _skill_registry
    3. 如果存在 scripts/ 目录，记录路径信息但不立即加载
    """
    with open(skill_md_path, 'r', encoding='utf-8') as f:
        skill_content = f.read()
    
    # 解析 frontmatter
    frontmatter = _parse_skill_frontmatter(skill_content)
    body = _strip_frontmatter(skill_content)
    
    # 从 frontmatter 获取 name 和 description
    skill_display_name = frontmatter.get("name", skill_name)
    skill_description = frontmatter.get("description", "")
    
    # 如果没有 frontmatter 中的 description，使用正文第一行
    if not skill_description:
        first_line = body.split('\n')[0].strip() if body else skill_name
        # 去掉 Markdown 标题前缀
        if first_line.startswith('#'):
            first_line = first_line.lstrip('#').strip()
        skill_description = first_line
    
    # 检查 scripts/ 目录
    scripts_dir = os.path.join(skill_dir, "scripts")
    has_scripts = os.path.exists(scripts_dir)
    
    # 存入统一注册表
    _skill_registry[skill_name] = {
        "name": skill_display_name,
        "description": skill_description,
        "content": body,
        "has_scripts": has_scripts,
        "scripts_dir": scripts_dir if has_scripts else "",
        "skill_dir": skill_dir,
        "scripts_loaded": False,
    }
    
    logger.debug(f"Skill {skill_name} 已注册（has_scripts={has_scripts}, {len(body)} 字符）")


def load_skill_scripts(skill_name: str) -> bool:
    """
    懒加载指定 Skill 的 scripts/ 目录中的所有工具。
    
    Args:
        skill_name: Skill 名称
    
    Returns:
        bool: 加载成功返回 True，失败返回 False
    """
    if skill_name not in _skill_registry:
        logger.warning(f"Skill {skill_name} 不在注册表中")
        return False
    
    skill_info = _skill_registry[skill_name]
    
    if not skill_info["has_scripts"]:
        logger.debug(f"Skill {skill_name} 没有 scripts/ 目录")
        return False
    
    if skill_info.get("scripts_loaded", False):
        logger.debug(f"Skill {skill_name} 的 scripts 已加载，跳过")
        return True
    
    scripts_dir = skill_info["scripts_dir"]
    loaded_count = 0
    
    try:
        for filename in os.listdir(scripts_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                module_name = filename[:-3]
                file_path = os.path.join(scripts_dir, filename)
                
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
                            loaded_count += 1
                        elif hasattr(attr, "__wrapped__") and isinstance(getattr(attr, "__wrapped__", None), BaseTool):
                            register_tool(attr)
                            loaded_count += 1
        
        # 标记为已加载
        _skill_registry[skill_name]["scripts_loaded"] = True
        logger.info(f"Skill {skill_name} 的 scripts 懒加载成功，注册了 {loaded_count} 个工具")
        return True
    
    except Exception as e:
        logger.error(f"懒加载 Skill {skill_name} 的 scripts 失败: {e}")
        return False


def reload_custom_tools() -> None:
    """
    重新加载所有自定义工具（热加载）。
    清空非内置工具和 Skill 注册表后重新扫描 custom/ 目录。
    """
    # 清空非内置工具，保留内置工具
    custom_tool_names = [
        name for name in _tool_registry.keys()
        if not name.startswith("builtin_")
    ]
    for name in custom_tool_names:
        del _tool_registry[name]
    
    # 清空 Skill 注册表
    _skill_registry.clear()
    
    _load_custom_tools()
    logger.info(f"自定义工具已重新加载，当前工具总数: {len(_tool_registry)}，Skill 数量: {len(_skill_registry)} 个")


# 模块加载时自动注册内置工具和自定义工具
_load_builtin_tools()
_load_custom_tools()
logger.info(f"工具加载完成，共 {len(_tool_registry)} 个工具")


if __name__ == "__main__":
    print("已注册的工具:")
    for name in list_tool_names():
        tool = get_tool(name)
        print(f"  - {name}: {tool.description if tool else 'N/A'}")
