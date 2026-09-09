"""
提示词模板模块
职责：
- 加载 Markdown 格式的提示词模板
- 提供提示词访问接口
"""
import os
from typing import Dict
from core.agent_logger import logger


# 提示词目录
PROMPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def load_prompt(filename: str) -> str:
    """
    加载提示词文件
    
    Args:
        filename: 提示词文件名（不含扩展名）
    
    Returns:
        提示词内容
    """
    filepath = os.path.join(PROMPTS_DIR, f"{filename}.md")
    
    if not os.path.exists(filepath):
        logger.error(f"提示词文件不存在: {filepath}")
        return ""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    logger.debug(f"已加载提示词: {filename}")
    return content


# 提示词缓存（避免重复读取文件）
_prompt_cache: Dict[str, str] = {}


def get_prompt(name: str) -> str:
    """
    获取提示词（带缓存）
    
    Args:
        name: 提示词名称
    
    Returns:
        提示词内容
    """
    if name not in _prompt_cache:
        _prompt_cache[name] = load_prompt(name)
    
    return _prompt_cache[name]


# 预定义的提示词名称
WRITER_PROMPT = "being_writer"
PRE_WRITING_PROMPT = "pre_writing"
POST_WRITING_PROMPT = "post_writing"
OUTLINE_POLISHER_PROMPT = "outline_polisher"
CONTENT_POLISHER_PROMPT = "content_polisher"
CHAT_AGENT_PROMPT = "chat_agent"
INFO_QUERY_PROMPT = "info_query"
SUMMARY_GENERATOR_PROMPT = "summary_generator"
