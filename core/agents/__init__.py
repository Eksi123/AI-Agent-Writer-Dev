"""
Agents 包
包含所有 Agent 的定义
"""
from core.agents.base_agent import BaseAgent
from core.agents.chat_agent import ChatAgent
from core.agents.novel_writer import NovelWriter
from core.agents.outline_polisher import OutlinePolisher
from core.agents.content_polisher import ContentPolisher
from core.agents.summary_generator import SummaryGenerator
from core.agents.info_query import InfoQuery

__all__ = [
    'BaseAgent',
    'ChatAgent',
    'NovelWriter',
    'OutlinePolisher',
    'ContentPolisher',
    'SummaryGenerator',
    'InfoQuery'
]
