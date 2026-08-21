"""
LLM客户端模块，支持多轮对话、工具调用、流式输出
"""
import os
import json
from typing import List, Dict, Any, Optional
from configparser import ConfigParser
from openai import OpenAI
from core.agent_logger import logger

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_PATH, "config")


class LLMClient:
    """
    大模型客户端
    职责：
    - 调用大模型 API
    - 管理对话历史
    - 解析响应（包括工具调用）
    - 支持流式输出
    """

    def __init__(self, base_url: str, api_key: str, model: str):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=60
        )
        self.model = model
        self.messages: List[Dict[str, Any]] = []

    def set_system_prompt(self, prompt: str) -> None:
        """设置系统提示词"""
        self.messages = [{"role": "system", "content": prompt}]

    def add_message(self, role: str, content: str, **kwargs) -> None:
        """添加消息到对话历史"""
        msg = {"role": role, "content": content}
        msg.update(kwargs)
        self.messages.append(msg)

    def clear_messages(self) -> None:
        """清空对话历史"""
        self.messages = []

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        调用大模型
        Args:
            messages: 对话消息列表
            tools: 工具定义列表（可选）
            max_tokens: 最大输出长度
            temperature: 温度参数
            stream: 是否流式输出
        Returns:
            {
                "content": str,           # 模型回复内容
                "tool_calls": List[Dict], # 工具调用列表
                "finish_reason": str      # 结束原因
            }
        """
        try:
            request_params: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            # 添加工具
            if tools:
                request_params["tools"] = tools
                request_params["tool_choice"] = "auto"

            # 发送请求
            if stream:
                return self._stream_chat(request_params)
            else:
                response = self.client.chat.completions.create(**request_params)
                return self._parse_response(response)

        except Exception as error:
            self._handle_error(error)
            return {"content": "", "tool_calls": [], "finish_reason": "error"}

    def _parse_response(self, response) -> Dict[str, Any]:
        """解析响应"""
        message = response.choices[0].message

        # 解析工具调用
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments)
                })

        return {
            "content": message.content or "",
            "tool_calls": tool_calls,
            "finish_reason": response.choices[0].finish_reason
        }

    def _stream_chat(self, request_params: Dict[str, Any]) -> Dict[str, Any]:
        """流式对话"""
        request_params["stream"] = True
        stream = self.client.chat.completions.create(**request_params)

        content = ""
        for chunk in stream:
            if chunk.choices[0].delta.content:
                content += chunk.choices[0].delta.content
                print(chunk.choices[0].delta.content, end="", flush=True)
        print()

        return {
            "content": content,
            "tool_calls": [],
            "finish_reason": "stop"
        }

    def _handle_error(self, error: Exception) -> None:
        """错误处理"""
        from openai import (
            APITimeoutError, APIConnectionError, AuthenticationError
        )

        if isinstance(error, APITimeoutError):
            logger.error("大模型请求超时")
        elif isinstance(error, APIConnectionError):
            logger.error("大模型连接失败")
        elif isinstance(error, AuthenticationError):
            logger.error("大模型api_key错误")
        else:
            logger.error(f"大模型请求失败: {str(error)}")


def create_llm_client() -> LLMClient:
    """创建LLM客户端实例"""
    config = ConfigParser()
    config.read(os.path.join(CONFIG_PATH, "setting.ini"), encoding="UTF-8")
    
    # 从环境变量读取 API Key
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        raise ValueError("环境变量 LLM_API_KEY 未设置，请先设置 API Key")
    
    return LLMClient(
        base_url=config['llm_api_aliyun']['base_url'],
        api_key=api_key,
        model=config['llm_api_aliyun']['model']
    )


if __name__ == '__main__':
    # 测试代码
    llm = create_llm_client()
    
    # 设置系统提示词
    llm.set_system_prompt("你是一个智能车辆助手。")
    
    # 添加用户消息
    llm.add_message("user", "你好")
    
    # 调用大模型
    response = llm.chat(llm.messages)
    print(f"回复: {response['content']}")
