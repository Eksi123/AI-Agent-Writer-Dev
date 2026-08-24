"""
在线请求工具

从互联网获取网页内容，自动截断过长响应以避免 Token 溢出。
"""
import requests
from langchain_core.tools import tool


@tool
def fetch_url(url: str, timeout: int = 10) -> str:
    """
    从互联网请求获取指定 URL 的内容
    
    Args:
        url: 要请求的 URL 地址
        timeout: 请求超时时间（秒），默认为 10
    
    Returns:
        响应内容（文本或错误信息）
    """
    try:
        # 发送 GET 请求并自动检测编码
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        response.encoding = response.apparent_encoding or 'utf-8'
        
        # 截断过长内容，避免 Token 溢出
        max_length = 5000
        if len(content) > max_length:
            content = content[:max_length] + f"\n\n... (内容已截断，总长度: {len(response.text)} 字符)"
        
        return f"URL: {url}\n状态码: {response.status_code}\n\n{content}"
        
    except requests.exceptions.Timeout:
        return f"错误: 请求超时（{timeout}秒）- {url}"
    except requests.exceptions.ConnectionError:
        return f"错误: 连接失败 - {url}"
    except requests.exceptions.HTTPError as e:
        return f"错误: HTTP 错误 {e.response.status_code} - {url}"
    except Exception as e:
        return f"错误: 请求失败 - {str(e)}"
