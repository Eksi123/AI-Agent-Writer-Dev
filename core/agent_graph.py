"""
LangGraph Agent 图模块
职责：
- 实现 Agent-Loop：思考 → 行动 → 观察
- 支持工具调用
- 支持多轮对话
- 提供工厂函数创建 Agent 图
"""
from typing import Annotated, TypedDict, Literal, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool
from langchain_core.messages import AIMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from core.agent_logger import logger


class AgentState(TypedDict):
    """
    Agent 状态定义
    messages 字段使用 add_messages 注解，新消息会自动追加到列表
    """
    messages: Annotated[list, add_messages]


class AgentGraph:
    """
    Agent 图类
    封装 LangGraph 的 StateGraph，提供统一的 Agent 运行接口
    """
    
    def __init__(self, llm: ChatOpenAI, tools: List[BaseTool], system_prompt: str):
        """
        初始化 Agent 图
        
        Args:
            llm: ChatOpenAI 实例
            tools: 工具列表
            system_prompt: 系统提示词
        """
        self.llm = llm
        self.tools = tools
        self.system_prompt = system_prompt
        
        # 绑定工具到 LLM
        self.llm_with_tools = llm.bind_tools(tools) if tools else llm
        
        # 构建工具映射表（用于快速查找）
        self.tool_map = {tool.name: tool for tool in tools}
        
        # 构建并编译图
        self.graph = self._build_graph()
    
    def _llm_node(self, state: AgentState) -> dict:
        """
        LLM 节点：负责"思考"
        调用 LLM 进行推理决策，决定是否需要调用工具
        """
        # 添加系统提示词
        system_msg = SystemMessage(content=self.system_prompt)
        messages = [system_msg] + state["messages"]
        
        # 调用 LLM
        response = self.llm_with_tools.invoke(messages)
        
        # 返回新消息（LangGraph 会自动追加到 state["messages"]）
        return {"messages": [response]}
    
    def _tool_node(self, state: AgentState) -> dict:
        """
        工具节点：负责"行动"
        执行 LLM 决策中的工具调用，并将结果反馈给 LLM
        """
        last_message = state["messages"][-1]
        tool_calls = last_message.tool_calls
        
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            logger.debug(f"调用工具: {tool_name}({tool_args})")
            
            # 查找并执行工具
            if tool_name in self.tool_map:
                tool_result = self.tool_map[tool_name].invoke(tool_args)
                logger.debug(f"工具结果: {tool_result[:100]}...")
            else:
                tool_result = f"错误: 工具 {tool_name} 不存在"
                logger.warning(f"工具不存在: {tool_name}")
            
            # 构造 ToolMessage
            results.append(ToolMessage(
                content=tool_result,
                tool_call_id=tool_call["id"],
                name=tool_name,
            ))
        
        # 返回工具结果消息
        return {"messages": results}
    
    def _should_continue(self, state: AgentState) -> Literal["tools", "end"]:
        """
        路由函数：决定 LLM 节点的下一步
        - 如果有 tool_calls → 路由到工具节点
        - 否则 → 路由到 END
        """
        last_message = state["messages"][-1]
        
        # 检查是否有工具调用
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "end"
    
    def _build_graph(self):
        """
        构建 Agent 状态图
        
        图结构：
            START → llm → (有工具调用?) → tools → llm (循环)
                         → (无工具调用?) → END
        """
        # 创建状态图
        graph = StateGraph(AgentState)
        
        # 添加节点
        graph.add_node("llm", self._llm_node)
        
        # 只有有工具时才添加工具节点
        if self.tools:
            graph.add_node("tools", self._tool_node)
            
            # 添加边
            graph.add_edge(START, "llm")
            graph.add_conditional_edges(
                "llm",
                self._should_continue,
                {"tools": "tools", "end": END}
            )
            graph.add_edge("tools", "llm")
        else:
            # 没有工具，直接 llm → END
            graph.add_edge(START, "llm")
            graph.add_edge("llm", END)
        
        # 编译图
        return graph.compile()
    
    def invoke(self, messages: List[dict], max_iterations: int = 10) -> dict:
        """
        运行 Agent 图
        
        Args:
            messages: 消息列表
            max_iterations: 最大迭代次数（防止无限循环）
        
        Returns:
            最终状态，包含 messages 列表
        """
        # 构造初始状态
        initial_state = {"messages": messages}
        
        # 运行图
        config = {"recursion_limit": max_iterations}
        final_state = self.graph.invoke(initial_state, config)
        
        return final_state
    
    def get_last_response(self, state: dict) -> str:
        """
        从状态中提取最后一条 AI 回复
        
        Args:
            state: Agent 状态
        
        Returns:
            AI 回复内容
        """
        messages = state["messages"]
        
        # 从后往前找最后一条 AIMessage
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                return msg.content
        
        return ""


def create_agent_graph(
    base_url: str,
    api_key: str,
    model: str,
    tools: List[BaseTool],
    system_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 4000
) -> AgentGraph:
    """
    工厂函数：创建 Agent 图实例
    
    Args:
        base_url: API URL
        api_key: API Key
        model: 模型名称
        tools: 工具列表
        system_prompt: 系统提示词
        temperature: 温度参数
        max_tokens: 最大输出长度
    
    Returns:
        AgentGraph 实例
    """
    # 创建 LLM 实例
    llm = ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens
    )
    
    # 创建并返回 Agent 图
    return AgentGraph(llm, tools, system_prompt)


if __name__ == '__main__':
    # 测试代码
    from core.config import config_manager
    from core.tools import get_all_tools
    
    # 获取配置
    config = config_manager.get_llm_config()
    
    # 获取所有工具
    tools = get_all_tools()
    
    # 创建 Agent 图
    agent = create_agent_graph(
        base_url=config["base_url"],
        api_key=config["api_key"],
        model=config["model"],
        tools=tools,
        system_prompt="你是一个智能助手，可以帮助用户完成任务。"
    )
    
    # 测试对话
    from langchain_core.messages import HumanMessage
    messages = [HumanMessage(content="你好")]
    
    result = agent.invoke(messages)
    response = agent.get_last_response(result)
    
    print(f"\nAgent: {response}")
