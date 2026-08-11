"""
联网搜索工具
用于收集写作素材（历史、地理、专业知识等）
"""
from typing import Optional
from core.logger import Logger


_logger = Logger("web_search")


def web_search_tool(query: str, max_results: int = 5) -> str:
    """
    联网搜索工具函数
    
    Args:
        query: 搜索关键词
        max_results: 最大结果数
    
    Returns:
        搜索结果文本
    """
    _logger.info(f"联网搜索: {query}")
    
    # 这里可以接入真实的搜索 API
    # 目前返回提示信息
    return (
        f"【联网搜索】关键词: {query}\n"
        f"提示: 请配置搜索 API（如 Bing Search API、SerpAPI 等）以启用联网搜索功能。\n"
        f"当前为离线模式，Agent 将依赖内置知识进行写作。"
    )


def search_historical_facts(topic: str) -> str:
    """
    搜索历史事实
    
    Args:
        topic: 历史主题
    
    Returns:
        相关历史信息
    """
    _logger.info(f"搜索历史事实: {topic}")
    return f"【历史搜索】{topic}\n提示: 请配置搜索 API 以启用此功能。"


def search_geography(location: str) -> str:
    """
    搜索地理信息
    
    Args:
        location: 地点名称
    
    Returns:
        相关地理信息
    """
    _logger.info(f"搜索地理信息: {location}")
    return f"【地理搜索】{location}\n提示: 请配置搜索 API 以启用此功能。"


def search_professional_knowledge(domain: str, query: str) -> str:
    """
    搜索专业知识
    
    Args:
        domain: 领域（医学、法律、科技等）
        query: 具体问题
    
    Returns:
        相关专业知识
    """
    _logger.info(f"搜索专业知识: [{domain}] {query}")
    return f"【专业搜索】[{domain}] {query}\n提示: 请配置搜索 API 以启用此功能。"


if __name__ == '__main__':
    # 测试
    print(web_search_tool("唐代长安城布局"))
    print()
    print(search_historical_facts("宋朝科举制度"))
