"""
LLM 客户端模块
封装大语言模型的调用逻辑，支持多配置、错误处理、LangChain 适配
"""
import os
import configparser
from typing import List, Optional, Dict, Any

import openai
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.outputs import ChatGeneration, ChatResult

from core.logger import Logger


# 初始化日志
_logger = Logger("agent_llm")

# 项目根目录
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_config(config_name: str = "llm_api_aliyun") -> dict:
    """
    从 config.ini 加载指定配置段
    
    Args:
        config_name: 配置段名称，如 "llm_api_aliyun"
    
    Returns:
        包含 base_url, api_key, model 的字典
    """
    config = configparser.ConfigParser()
    config_path = os.path.join(BASE_PATH, "config.ini")
    config.read(config_path, encoding="utf-8-sig")
    
    return {
        "base_url": config.get(config_name, "base_url"),
        "api_key": config.get(config_name, "api_key"),
        "model": config.get(config_name, "model"),
    }


class AgentLLM:
    """
    自定义大模型客户端（原生 OpenAI 接口封装）
    
    功能：
    - 支持多轮对话
    - 支持工具调用（Function Calling）
    - 统一的错误处理
    - 可配置超时和重试
    """
    
    def __init__(self, base_url: str, api_key: str, model: str, timeout: int = 60):
        """
        初始化 LLM 客户端
        
        Args:
            base_url: API 基础 URL
            api_key: API 密钥
            model: 模型名称
            timeout: 请求超时时间（秒）
        """
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )
        self.model = model
        self.timeout = timeout
        _logger.info(f"AgentLLM 初始化完成，模型: {model}")
    
    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """
        单轮对话（简单调用）
        
        Args:
            prompt: 用户输入
            system_prompt: 系统提示词
            max_tokens: 最大输出 token 数
            temperature: 温度参数（0~2，越高越随机）
        
        Returns:
            模型回复文本
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return self._call_api(messages, max_tokens, temperature)
    
    def chat_messages(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        tools: Optional[List[Dict]] = None,
    ) -> dict:
        """
        多轮对话（完整消息列表）
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            max_tokens: 最大输出 token 数
            temperature: 温度参数
            tools: 工具定义列表（Function Calling）
        
        Returns:
            包含 content 和 tool_calls 的字典
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        
        try:
            response = self.client.chat.completions.create(**kwargs)
            message = response.choices[0].message
            result = {
                "content": message.content,
                "tool_calls": message.tool_calls if hasattr(message, "tool_calls") else None,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            }
            _logger.debug(f"LLM 调用成功，消耗 token: {result['usage']['total_tokens']}")
            return result
        except Exception as error:
            self._handle_error(error)
            return {"content": "", "tool_calls": None, "usage": {}}
    
    def _call_api(self, messages: List[Dict], max_tokens: int, temperature: float) -> str:
        """调用 API 并处理错误"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            content = response.choices[0].message.content
            _logger.debug(f"LLM 调用成功，回复长度: {len(content) if content else 0}")
            return content
        except Exception as error:
            self._handle_error(error)
            return ""
    
    def _handle_error(self, error: Exception):
        """统一错误处理"""
        if isinstance(error, openai.APITimeoutError):
            _logger.error(f"LLM 请求超时（{self.timeout}s）")
        elif isinstance(error, openai.APIConnectionError):
            _logger.error("LLM 连接失败，请检查网络")
        elif isinstance(error, openai.AuthenticationError):
            _logger.error("LLM API Key 认证失败")
        elif isinstance(error, openai.RateLimitError):
            _logger.error("LLM 请求频率超限")
        else:
            _logger.error(f"LLM 调用异常: {error}")


class LangChainChatModel(BaseChatModel):
    """
    将 AgentLLM 适配为 LangChain 的 BaseChatModel
    
    用于在 LangChain 的 Chain/Agent 中使用自定义 LLM
    """
    
    client: Any  # openai.OpenAI 实例
    model_name: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    
    class Config:
        arbitrary_types_allowed = True
    
    @property
    def _llm_type(self) -> str:
        return "custom-chat-model"
    
    @property
    def _identifying_params(self) -> dict:
        return {
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs,
    ) -> ChatResult:
        """
        LangChain 标准生成方法
        
        将 LangChain 消息格式转为 OpenAI 格式后调用
        """
        # 转换消息格式
        openai_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                openai_messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                openai_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                openai_messages.append({"role": "assistant", "content": msg.content})
            else:
                openai_messages.append({"role": "user", "content": msg.content})
        
        # 构建请求参数
        request_kwargs = {
            "model": self.model_name,
            "messages": openai_messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        
        if stop:
            request_kwargs["stop"] = stop
        
        # 合并额外参数
        request_kwargs.update(kwargs)
        
        try:
            response = self.client.chat.completions.create(**request_kwargs)
            content = response.choices[0].message.content or ""
            
            generation = ChatGeneration(
                message=AIMessage(content=content),
                generation_info={
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    }
                } if response.usage else None,
            )
            return ChatResult(generations=[generation])
            
        except Exception as error:
            _logger.error(f"LangChain LLM 调用异常: {error}")
            raise


def create_langchain_llm(
    config_name: str = "llm_api_aliyun",
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> LangChainChatModel:
    """
    工厂函数：创建 LangChain 兼容的 LLM 实例
    
    Args:
        config_name: 配置段名称
        max_tokens: 最大输出 token 数
        temperature: 温度参数
    
    Returns:
        LangChainChatModel 实例
    """
    cfg = load_config(config_name)
    
    client = openai.OpenAI(
        api_key=cfg["api_key"],
        base_url=cfg["base_url"],
        timeout=60,
    )
    
    return LangChainChatModel(
        client=client,
        model_name=cfg["model"],
        max_tokens=max_tokens,
        temperature=temperature,
    )


def create_agent_llm(config_name: str = "llm_api_aliyun") -> AgentLLM:
    """
    工厂函数：创建 AgentLLM 实例
    
    Args:
        config_name: 配置段名称
    
    Returns:
        AgentLLM 实例
    """
    cfg = load_config(config_name)
    return AgentLLM(
        base_url=cfg["base_url"],
        api_key=cfg["api_key"],
        model=cfg["model"],
    )


# ============ 便捷实例（供其他模块直接导入）============
agent_llm = create_agent_llm()


if __name__ == '__main__':
    # 测试原生调用
    print("=== 测试 AgentLLM ===")
    response = agent_llm.chat("用一句话介绍你自己")
    print(f"回复: {response}")
    
    # 测试 LangChain 适配
    print("\n=== 测试 LangChain 适配 ===")
    lc_llm = create_langchain_llm()
    result = lc_llm.invoke([HumanMessage(content="用一句话介绍你自己")])
    print(f"回复: {result.content}")
