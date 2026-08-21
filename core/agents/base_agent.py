"""
Agent 基类模块
职责：
- 定义 Agent 的统一接口
- 封装 LLM 调用和工具绑定
- 提供消息管理功能
"""
from typing import List, Optional
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import BaseTool
from core.agent_graph import AgentGraph, create_agent_graph
from core.config import config_manager
from core.agent_logger import logger


class BaseAgent:
    """
    Agent 基类
    所有具体 Agent 都应继承此类
    """
    
    def __init__(
        self,
        name: str,
        system_prompt: str,
        tools: List[BaseTool],
        temperature: float = 0.7
    ):
        """
        初始化 Agent
        
        Args:
            name: Agent 名称
            system_prompt: 系统提示词
            tools: 工具列表
            temperature: 温度参数
        """
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools
        self.temperature = temperature
        
        # 对话历史
        self.chat_history: List[dict] = []
        
        # 创建 Agent 图
        self._init_agent_graph()
    
    def _init_agent_graph(self) -> None:
        """初始化 Agent 图"""
        config = config_manager.get_llm_config()
        
        self.agent_graph: AgentGraph = create_agent_graph(
            base_url=config["base_url"],
            api_key=config["api_key"],
            model=config["model"],
            tools=self.tools,
            system_prompt=self.system_prompt,
            temperature=self.temperature
        )
        
        logger.debug(f"Agent 已初始化: {self.name}")
    
    def chat(self, user_input: str) -> str:
        """
        与 Agent 对话
        
        Args:
            user_input: 用户输入
        
        Returns:
            Agent 回复内容
        """
        # 添加用户消息到历史
        self.chat_history.append({"role": "user", "content": user_input})
        
        # 运行 Agent 图
        result = self.agent_graph.invoke(self.chat_history)
        
        # 提取最后一条 AI 回复
        response = self.agent_graph.get_last_response(result)
        
        # 更新对话历史
        self.chat_history = result["messages"]
        
        logger.debug(f"[{self.name}] 用户: {user_input[:50]}...")
        logger.debug(f"[{self.name}] Agent: {response[:50]}...")
        
        return response
    
    def clear_history(self) -> None:
        """清空对话历史"""
        self.chat_history = []
        logger.debug(f"[{self.name}] 对话历史已清空")
    
    def get_history_length(self) -> int:
        """获取对话历史长度"""
        return len(self.chat_history)


if __name__ == '__main__':
    # 测试代码
    from core.tools import get_all_tools
    
    # 创建一个简单的测试 Agent
    tools = get_all_tools()
    
    agent = BaseAgent(
        name="测试Agent",
        system_prompt="你是一个智能助手。",
        tools=tools
    )
    
    # 测试对话
    response = agent.chat("你好，请介绍一下自己")
    print(f"\nAgent: {response}")
