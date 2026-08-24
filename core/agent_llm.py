"""
LLM客户端模块
封装 OpenAI 兼容 API 的调用逻辑，支持：
- 多轮对话（通过 messages 列表管理上下文）
- 工具调用（Function Calling）
- 流式输出
- 错误处理与重试提示
"""
import os
import json
from typing import List, Dict, Any, Optional
from configparser import ConfigParser
from openai import OpenAI, APITimeoutError, APIConnectionError, AuthenticationError
from core.agent_logger import logger
from core.config_manager import config_manager

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_PATH, "config")


class LLMClient:
    """
    大模型客户端
    封装 OpenAI 兼容 API 的调用，统一管理对话历史和响应解析
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
        max_tokens: int = 8192,
        temperature: float = 0.7,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        调用大模型
        
        工作流程：
        1. 构建请求参数（model, messages, temperature 等）
        2. 如果提供 tools，启用 Function Calling 模式
        3. 根据 stream 参数选择同步或流式调用
        4. 解析响应，提取文本内容和工具调用
        5. 异常时返回友好的错误信息
        
        Args:
            messages: 对话消息列表，格式：[{"role": "user", "content": "..."}]
            tools: 工具定义列表（可选），用于 Function Calling
            max_tokens: 最大输出长度
            temperature: 温度参数（0-1，越高越随机）
            stream: 是否流式输出（逐步显示生成内容）
        
        Returns:
            {
                "content": str,           # 模型回复的文本内容
                "tool_calls": List[Dict], # 工具调用列表（如果有）
                "finish_reason": str      # 结束原因："stop" 或 "tool_calls"
            }
        """
        try:
            # 构建基础请求参数
            request_params: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            # 如果提供了工具，启用 Function Calling
            # 模型会在需要时返回 tool_calls，而不是直接回复文本
            if tools:
                request_params["tools"] = tools
                request_params["tool_choice"] = "auto"

            # 根据 stream 参数选择调用方式
            if stream:
                return self._stream_chat(request_params)
            else:
                response = self.client.chat.completions.create(**request_params)
                return self._parse_response(response)

        except Exception as error:
            self._handle_error(error)
            return {"content": "", "tool_calls": [], "finish_reason": "error"}

    def _parse_response(self, response) -> Dict[str, Any]:
        """
        解析模型响应，提取文本内容和工具调用
        
        模型响应可能包含：
        - 纯文本回复（content）
        - 工具调用请求（tool_calls），此时 content 可能为空
        - 两者兼有（部分模型会同时返回文本和工具调用）
        """
        message = response.choices[0].message

        # 提取工具调用：将 arguments 从 JSON 字符串解析为 dict
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
        """
        流式对话：逐块接收模型输出并实时打印到终端
        适用于长文本生成场景，用户可以边生成边看到内容
        注意：流式模式下不支持工具调用
        """
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
        """根据异常类型输出对应的错误日志"""
        if isinstance(error, APITimeoutError):
            logger.error("大模型请求超时")
        elif isinstance(error, APIConnectionError):
            logger.error("大模型连接失败")
        elif isinstance(error, AuthenticationError):
            logger.error("大模型api_key错误")
        else:
            logger.error(f"大模型请求失败: {str(error)}")


def create_llm_client() -> LLMClient:
    """
    工厂函数：根据当前配置创建 LLMClient 实例
    
    配置优先级：[Ollama] enabled=true 时使用本地模型，否则使用 [LLM] 云端配置
    API Key 来源：配置字典中自带（Ollama 占位符）或环境变量 LLM_API_KEY
    """
    config = config_manager.get_llm_config()
    api_key = config.get('api_key') or os.environ.get("LLM_API_KEY")
    if not api_key:
        raise ValueError("环境变量 LLM_API_KEY 未设置，请先设置 API Key")
    
    return LLMClient(
        base_url=config['api_url'],
        api_key=api_key,
        model=config['model_name']
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
