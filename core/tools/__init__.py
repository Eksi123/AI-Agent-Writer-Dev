"""
工具注册表模块
职责：
- 自动注册内置工具
- 热加载用户自定义工具
- 提供工具查询接口
"""
import os
import importlib
import importlib.util
from typing import List, Dict, Any, Optional
from langchain_core.tools import BaseTool
from core.agent_logger import logger


# 工具注册表：存储所有可用工具
_tool_registry: Dict[str, BaseTool] = {}


def register_tool(tool: BaseTool) -> None:
    """
    注册单个工具到全局注册表
    
    Args:
        tool: LangChain BaseTool 实例
    """
    tool_name = tool.name
    if tool_name in _tool_registry:
        logger.warning(f"工具 {tool_name} 已存在，将被覆盖")
    
    _tool_registry[tool_name] = tool
    logger.debug(f"工具已注册: {tool_name}")


def register_tools(tools: List[BaseTool]) -> None:
    """
    批量注册工具
    
    Args:
        tools: 工具列表
    """
    for tool in tools:
        register_tool(tool)


def get_tool(tool_name: str) -> Optional[BaseTool]:
    """
    获取指定名称的工具
    
    Args:
        tool_name: 工具名称
    
    Returns:
        工具实例，不存在则返回 None
    """
    return _tool_registry.get(tool_name)


def get_all_tools() -> List[BaseTool]:
    """
    获取所有已注册的工具
    
    Returns:
        工具列表
    """
    return list(_tool_registry.values())


def get_tools_by_names(tool_names: List[str]) -> List[BaseTool]:
    """
    根据工具名称列表获取工具
    
    Args:
        tool_names: 工具名称列表
    
    Returns:
        匹配的工具列表（不存在的会被忽略）
    """
    return [
        _tool_registry[name] 
        for name in tool_names 
        if name in _tool_registry
    ]


def list_tool_names() -> List[str]:
    """
    列出所有已注册工具的名称
    
    Returns:
        工具名称列表
    """
    return list(_tool_registry.keys())


def _load_builtin_tools() -> None:
    """
    加载内置工具
    自动扫描 builtin/ 目录下的所有工具模块并注册
    """
    builtin_dir = os.path.join(os.path.dirname(__file__), "builtin")
    
    if not os.path.exists(builtin_dir):
        logger.warning(f"内置工具目录不存在: {builtin_dir}")
        return
    
    # 遍历 builtin 目录下的所有 .py 文件
    for filename in os.listdir(builtin_dir):
        if filename.endswith(".py") and not filename.startswith("_"):
            module_name = filename[:-3]  # 去掉 .py 后缀
            
            try:
                # 动态导入模块
                full_module_name = f"core.tools.builtin.{module_name}"
                module = importlib.import_module(full_module_name)
                
                # 查找模块中的工具（约定：模块中导出的 BaseTool 实例或 @tool 装饰的函数）
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, BaseTool):
                        register_tool(attr)
                    elif hasattr(attr, "__wrapped__") and isinstance(getattr(attr, "__wrapped__", None), BaseTool):
                        # @tool 装饰器包装的函数
                        register_tool(attr)
                
                logger.debug(f"内置工具模块已加载: {module_name}")
                
            except Exception as e:
                logger.error(f"加载内置工具模块 {module_name} 失败: {e}")


def _load_custom_tools() -> None:
    """
    加载用户自定义工具（Skill 格式）
    扫描 custom/ 目录下的所有 skill 文件夹并注册
    每个 skill 必须包含 SKILL.md 说明书
    支持热加载：每次调用都会重新扫描
    """
    custom_dir = os.path.join(os.path.dirname(__file__), "custom")
    
    if not os.path.exists(custom_dir):
        logger.debug(f"自定义工具目录不存在: {custom_dir}")
        return
    
    # 遍历 custom 目录下的所有子目录（skill 文件夹）
    for skill_name in os.listdir(custom_dir):
        skill_dir = os.path.join(custom_dir, skill_name)
        
        # 必须是目录且不以 _ 开头
        if not os.path.isdir(skill_dir) or skill_name.startswith("_"):
            continue
        
        # 检查是否存在 SKILL.md
        skill_md_path = os.path.join(skill_dir, "SKILL.md")
        if not os.path.exists(skill_md_path):
            logger.warning(f"Skill {skill_name} 缺少 SKILL.md，跳过")
            continue
        
        try:
            # 加载 skill
            _load_skill(skill_name, skill_dir, skill_md_path)
            logger.debug(f"自定义 Skill 已加载: {skill_name}")
            
        except Exception as e:
            logger.error(f"加载自定义 Skill {skill_name} 失败: {e}")


def _load_skill(skill_name: str, skill_dir: str, skill_md_path: str) -> None:
    """
    加载单个 skill
    
    Args:
        skill_name: skill 名称（文件夹名）
        skill_dir: skill 目录路径
        skill_md_path: SKILL.md 文件路径
    """
    # 读取 SKILL.md 内容
    with open(skill_md_path, 'r', encoding='utf-8') as f:
        skill_content = f.read()
    
    # 解析 SKILL.md 提取工具定义
    # 这里简化处理：查找 scripts/ 目录下的 Python 文件并加载
    scripts_dir = os.path.join(skill_dir, "scripts")
    
    if os.path.exists(scripts_dir):
        # 加载 scripts 目录下的所有 .py 文件
        for filename in os.listdir(scripts_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                module_name = filename[:-3]
                file_path = os.path.join(scripts_dir, filename)
                
                try:
                    # 动态导入模块
                    spec = importlib.util.spec_from_file_location(
                        f"core.tools.custom.{skill_name}.scripts.{module_name}",
                        file_path
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        # 查找并注册工具
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if isinstance(attr, BaseTool):
                                register_tool(attr)
                            elif hasattr(attr, "__wrapped__") and isinstance(getattr(attr, "__wrapped__", None), BaseTool):
                                register_tool(attr)
                
                except Exception as e:
                    logger.error(f"加载 Skill {skill_name} 的脚本 {module_name} 失败: {e}")
    
    # 将 SKILL.md 内容存储到元数据中（供后续使用）
    logger.debug(f"Skill {skill_name} 的 SKILL.md 已读取（{len(skill_content)} 字符）")


def reload_custom_tools() -> None:
    """
    重新加载所有自定义工具
    用于热加载场景：用户修改自定义工具后调用此方法
    """
    # 清空自定义工具（保留内置工具）
    custom_tool_names = [
        name for name in _tool_registry.keys()
        if not name.startswith("builtin_")
    ]
    for name in custom_tool_names:
        del _tool_registry[name]
    
    # 重新加载
    _load_custom_tools()
    logger.info(f"自定义工具已重新加载，当前工具总数: {len(_tool_registry)}")


# 模块加载时自动注册内置工具
_load_builtin_tools()
logger.info(f"内置工具加载完成，共 {len(_tool_registry)} 个工具")

# 初次加载自定义工具
_load_custom_tools()
logger.info(f"所有工具加载完成，共 {len(_tool_registry)} 个工具")


if __name__ == "__main__":
    # 测试代码
    print("已注册的工具:")
    for name in list_tool_names():
        tool = get_tool(name)
        print(f"  - {name}: {tool.description if tool else 'N/A'}")
