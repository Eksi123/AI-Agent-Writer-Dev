"""
LangGraph Agent 图模块

核心概念：
- Agent-Loop（代理循环）：思考 → 行动 → 观察 的迭代过程
- 模型先思考是否需要调用工具，如果需要则调用工具，观察结果后继续思考
- 直到模型认为任务完成（不再需要工具），循环结束

本模块提供：
- AgentState：定义 Agent 运行时的状态结构
- AgentGraph：封装 LangGraph 的 StateGraph，实现 Agent-Loop
- create_agent_graph()：工厂函数，快速创建 Agent 图实例
"""
from typing import Annotated, TypedDict, Literal, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from core.agent_logger import logger
from core.config_manager import config_manager
from core.tools import get_all_tools


class AgentState(TypedDict):
    """
    Agent 运行状态定义
    
    messages 字段使用 add_messages 注解，这是 LangGraph 的特殊机制：
    - 当节点返回 {"messages": [新消息]} 时，新消息会自动追加到 state["messages"] 列表
    - 而不是覆盖整个列表
    - 这样可以累积多轮对话历史
    """
    messages: Annotated[list, add_messages]


class AgentGraph:
    """
    Agent 图类
    
    封装 LangGraph 的 StateGraph，实现 Agent-Loop：
    
    执行流程：
    START → llm_node → (有工具调用?) → tool_node → llm_node (循环)
                     → (无工具调用?) → END
    
    关键组件：
    - llm_node：调用大模型进行推理决策
    - tool_node：执行工具调用并返回结果
    - _should_continue：路由函数，决定下一步走向
    """
    
    def __init__(self, llm: ChatOpenAI, tools: List[BaseTool], system_prompt: str):
        """
        初始化 Agent 图
        
        Args:
            llm: ChatOpenAI 实例（已配置好模型参数）
            tools: 工具列表（可以为空列表）
            system_prompt: 系统提示词（定义 Agent 的角色和行为）
        """
        self.llm = llm
        self.tools = tools
        self.system_prompt = system_prompt
        
        # 绑定工具到 LLM，启用 Function Calling 能力
        self.llm_with_tools = llm.bind_tools(tools) if tools else llm
        
        # 构建工具名称 → 工具实例的映射表，用于快速查找
        self.tool_map = {tool.name: tool for tool in tools}
        
        # 思考过程记录（用于调试和展示给前端）
        self.thought_process = []
        
        # 构建并编译图
        self.graph = self._build_graph()
    
    def _llm_node(self, state: AgentState) -> dict:
        """
        LLM 节点：负责"思考"
        
        职责：
        1. 在消息列表前添加系统提示词
        2. 调用大模型进行推理
        3. 记录思考过程（用于调试和前端展示）
        4. 返回模型响应（LangGraph 会自动追加到 state["messages"]）
        
        模型可能会：
        - 直接返回文本回复（任务完成）
        - 返回工具调用请求（需要执行工具）
        """
        # 在消息列表前添加系统提示词，确保每次调用都包含角色定义
        system_msg = SystemMessage(content=self.system_prompt)
        messages = [system_msg] + state["messages"]
        
        # 调用 LLM 进行推理
        response = self.llm_with_tools.invoke(messages)
        
        # 记录思考过程（如果模型返回了文本内容）
        if response.content:
            self.thought_process.append({
                "type": "thinking",
                "content": response.content
            })
        
        # 返回新消息，LangGraph 的 add_messages 注解会自动追加到 state
        return {"messages": [response]}
    
    def _tool_node(self, state: AgentState) -> dict:
        """
        工具节点：负责"行动"
        
        职责：
        1. 从最后一条消息中提取工具调用请求
        2. 查找并执行对应的工具
        3. 将工具执行结果封装为 ToolMessage
        4. 记录工具调用过程和结果（用于调试和前端展示）
        
        工具调用流程：
        - LLM 返回 tool_calls（包含工具名和参数）
        - 本节点执行工具，获取结果
        - 将结果作为 ToolMessage 返回给 LLM，供下一轮思考使用
        """
        last_message = state["messages"][-1]
        tool_calls = last_message.tool_calls
        
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            logger.debug(f"调用工具: {tool_name}({tool_args})")
            
            # 记录工具调用请求
            self.thought_process.append({
                "type": "tool_call",
                "tool": tool_name,
                "args": tool_args
            })
            
            # 查找并执行工具
            if tool_name in self.tool_map:
                tool_result = self.tool_map[tool_name].invoke(tool_args)
                logger.debug(f"工具结果: {tool_result[:100]}...")
                
                # 记录工具结果（截断过长内容）
                self.thought_process.append({
                    "type": "tool_result",
                    "tool": tool_name,
                    "result": tool_result[:500] if len(tool_result) > 500 else tool_result
                })
            else:
                # 工具不存在，返回错误信息给 LLM
                tool_result = f"错误: 工具 {tool_name} 不存在"
                logger.warning(f"工具不存在: {tool_name}")
                
                self.thought_process.append({
                    "type": "tool_error",
                    "tool": tool_name,
                    "error": tool_result
                })
            
            # 构造 ToolMessage，tool_call_id 用于关联请求和响应
            results.append(ToolMessage(
                content=tool_result,
                tool_call_id=tool_call["id"],
                name=tool_name,
            ))
        
        # 返回工具结果消息，LangGraph 会自动追加到 state
        return {"messages": results}
    
    def _should_continue(self, state: AgentState) -> Literal["tools", "end"]:
        """
        路由函数：决定 LLM 节点的下一步走向
        
        判断逻辑：
        - 检查最后一条消息是否包含工具调用请求（tool_calls）
        - 如果有 → 返回 "tools"，路由到工具节点执行
        - 如果没有 → 返回 "end"，路由到 END，结束循环
        
        这是 Agent-Loop 的核心控制逻辑，决定了何时继续思考、何时结束任务
        """
        last_message = state["messages"][-1]
        
        # 检查是否有工具调用请求
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "end"
    
    def _build_graph(self):
        """
        构建 Agent 状态图
        
        图结构（有工具时）：
            START → llm → (有工具调用?) → tools → llm (循环)
                         → (无工具调用?) → END
        
        图结构（无工具时）：
            START → llm → END
        
        关键概念：
        - 节点（Node）：执行具体逻辑的函数（如 llm_node, tool_node）
        - 边（Edge）：节点之间的连接，定义执行顺序
        - 条件边（Conditional Edge）：根据状态动态决定下一个节点
        """
        # 创建状态图，使用 AgentState 作为状态类型
        graph = StateGraph(AgentState)
        
        # 添加 LLM 节点（必须）
        graph.add_node("llm", self._llm_node)
        
        # 只有有工具时才添加工具节点和复杂的边
        if self.tools:
            graph.add_node("tools", self._tool_node)
            
            # 添加从 START 到 llm 的边
            graph.add_edge(START, "llm")
            
            # 添加条件边：根据 _should_continue 的返回值决定走向
            graph.add_conditional_edges(
                "llm",                      # 从 llm 节点出发
                self._should_continue,      # 路由函数
                {"tools": "tools", "end": END}  # 返回值到节点的映射
            )
            
            # 添加从 tools 回到 llm 的边（形成循环）
            graph.add_edge("tools", "llm")
        else:
            # 没有工具时，简单流程：START → llm → END
            graph.add_edge(START, "llm")
            graph.add_edge("llm", END)
        
        # 编译图，生成可执行的 CompiledGraph 对象
        return graph.compile()
    
    def invoke(self, messages: List[dict], max_iterations: int = 30) -> dict:
        """
        运行 Agent 图，执行完整的 Agent-Loop
        
        参数说明：
        - messages: 对话历史消息列表，格式为 [{"role": "user/assistant", "content": "..."}]
        - max_iterations: 最大迭代次数限制，防止无限循环
          * 默认 30 次：适用于大多数任务
          * 传入 0：表示不限制（设置为 9999），用于长任务
        
        返回值：
        - 最终状态字典，包含：
          * messages: 完整的对话历史（包括所有中间消息）
          * thought_process: 思考过程记录（用于调试和前端展示）
        
        执行流程：
        1. 清空之前的思考过程记录
        2. 构造初始状态（包含输入消息）
        3. 调用编译后的图执行（LangGraph 会自动处理节点流转）
        4. 将思考过程添加到返回结果中
        """
        # 清空思考过程，准备记录本次执行
        self.thought_process = []
        
        # 构造初始状态，LangGraph 会从 START 节点开始执行
        initial_state = {"messages": messages}
        
        # 配置递归限制：max_iterations=0 表示不限制，设置为极大值
        recursion_limit = max_iterations if max_iterations > 0 else 9999
        config = {"recursion_limit": recursion_limit}
        
        # 执行图，LangGraph 会自动处理节点流转和状态更新
        final_state = self.graph.invoke(initial_state, config)
        
        # 将思考过程添加到返回结果中，供上层使用
        final_state["thought_process"] = self.thought_process
        
        return final_state
    
    def get_last_response(self, state: dict) -> str:
        """
        从最终状态中提取最后一条 AI 回复
        
        用途：
        - 从完整的对话历史中提取模型的最终回复
        - 忽略中间的工具调用消息，只返回 AI 的文本内容
        
        实现逻辑：
        - 从后往前遍历消息列表
        - 找到第一条 AIMessage（AI 回复消息）
        - 返回其 content 字段
        """
        messages = state["messages"]
        
        # 从后往前查找，找到最后一条 AIMessage
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
    max_tokens: int = 8192
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
    # 获取配置
    config = config_manager.get_llm_config()
    
    # 获取所有工具
    tools = get_all_tools()
    
    # 创建 Agent 图
    agent = create_agent_graph(
        base_url=config["api_url"],
        api_key=config["api_key"],
        model=config["model_name"],
        tools=tools,
        system_prompt="你是一个智能助手，可以帮助用户完成任务。"
    )
    
    # 测试对话
    messages = [HumanMessage(content="你好")]
    
    result = agent.invoke(messages)
    response = agent.get_last_response(result)
    
    print(f"\nAgent: {response}")
