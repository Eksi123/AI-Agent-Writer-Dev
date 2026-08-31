"""
AI Agent Demo - LangGraph 版本

使用 LangGraph 的 StateGraph（状态图）实现 Agent-Loop。
核心概念：
- 节点（Node）：LLM 思考节点和工具执行节点
- 边（Edge）：节点之间的连接和条件路由
- 状态（State）：通过 messages 列表在节点间传递
"""

import os
import json
from typing import Annotated, TypedDict, Literal
from configparser import ConfigParser

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode


# 1. 读取配置文件
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_file = os.path.join(BASE_PATH, "config.ini")

config = ConfigParser()
config.read(config_file, encoding='utf-8')
api_key = os.environ.get("LLM_API_KEY")
if not api_key:
    raise ValueError("环境变量 LLM_API_KEY 未设置，请先设置 API Key")
base_url = config.get('LLM', 'api_url')
model_name = config.get('LLM', 'model_name')


# 2. 创建 LLM 实例
llm = ChatOpenAI(
    api_key=api_key,
    base_url=base_url,
    model=model_name,
    temperature=0,
    max_tokens=512
)


# 3. 定义工具（@tool 装饰器）
@tool
def get_weather(city: str) -> str:
    """查询指定城市的天气信息"""
    mock_data = {
        "北京": {"天气": "晴", "温度": "25°C", "湿度": "40%", "风力": "微风"},
        "上海": {"天气": "多云", "温度": "22°C", "湿度": "65%", "风力": "东南风3级"},
        "广州": {"天气": "小雨", "温度": "28°C", "湿度": "80%", "风力": "南风2级"},
        "深圳": {"天气": "阴", "温度": "26°C", "湿度": "70%", "风力": "东风2级"},
    }

    data = mock_data.get(city, {"天气": "未知", "温度": "N/A", "湿度": "N/A", "风力": "N/A"})
    result = {"城市": city, **data}
    return json.dumps(result, ensure_ascii=False)


tools = [get_weather]


# 4. 定义 Agent 状态图

# 4.1 定义状态类型（所有节点共享 messages 列表，此时AgentState类似状态图的共享笔记本）
class AgentState(TypedDict):
    """
    AgentState 定义了图中每个节点共享的状态数据。
    messages 字段使用 add_messages 注解，表示新消息会追加到列表中
    """
    messages: Annotated[list, add_messages]


# 4.2 定义图的节点
# 将工具绑定到 LLM 实例，使其具备 tool_call（函数调用）能力。
# 绑定后，LLM 在推理时可以生成 tool_calls 字段来请求调用工具，
llm_with_tools = llm.bind_tools(tools)

def llm_node(state: AgentState) -> dict:
    """
    Agent 节点（思考节点）：调用 LLM 进行推理决策。

    这是状态图中最核心的节点，负责：
      1. 接收当前完整的消息历史（state["messages"]）
      2. 将系统提示 + 消息历史发送给 LLM
      3. LLM 返回的响应可能包含：
         - tool_calls：请求调用工具（此时需要路由到工具节点）
         - content：直接给出最终回答（此时可以结束循环）

    注意：返回的 dict 中的 messages 列表会被 add_messages reducer 自动合并
    到 state["messages"] 中，而不是覆盖。
    """
    system_prompt = SystemMessage(content="你是一个智能助手，可以使用工具来帮助用户完成任务。")
    # 将系统提示放在消息列表最前面，确保 LLM 始终能看到角色设定
    response = llm_with_tools.invoke([system_prompt] + state["messages"])
    # 返回包含新 AI 消息的 dict，LangGraph 通过 add_messages reducer 自动追加到状态中
    return {"messages": [response]}

def tool_node(state: AgentState) -> dict:
    """
    工具执行节点：执行 LLM 请求的工具调用，并将结果反馈给 LLM。

    工作流程：
      1. 从消息历史中取出最后一条 AI 消息（包含 tool_calls）
      2. 遍历所有 tool_calls，逐一查找并执行对应的工具函数
      3. 将每个工具的执行结果封装为 ToolMessage
      4. 返回所有 ToolMessage，它们会被追加到 state["messages"] 中

    关键：ToolMessage 必须携带 tool_call_id，这样 LLM 才能将结果
    与对应的工具调用关联起来，理解每个调用的返回值。
    """
    last_message = state["messages"][-1]
    # tool_calls 是 LLM 响应中自动生成的工具调用请求列表，
    # 每个元素包含 name（工具名）、args（参数）、id（调用标识）
    tool_calls = last_message.tool_calls

    # 预构建工具名 → 工具实例的映射表，便于快速查找
    tool_map = {t.name: t for t in tools}

    results = []
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        print(f"  [调用工具] {tool_name}({tool_args})")

        # 根据工具名查找对应工具实例并执行
        tool_result = tool_map[tool_name].invoke(tool_args)

        print(f"  [工具结果] {tool_result}")

        # 构造 ToolMessage，tool_call_id 是关键字段，
        # LLM 通过它来匹配「哪个 tool_call 得到了哪个结果」
        results.append(ToolMessage(
            content=tool_result,
            tool_call_id=tool_call["id"],
            name=tool_name,
        ))

    return {"messages": results}


# 4.3 定义图的条件边（Conditional Edge）
def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """
    条件路由：根据 LLM 的响应决定下一步走向。
    - 如果响应中包含 tool_calls → 路由到 "tools" 节点执行工具
    - 否则 → 路由到 END，结束循环
    """
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "end"


# 4.4 基于 LangGraph 构建 Agent 状态图（StateGraph）
#
# 整体架构如下（Agent-Loop 循环）：
#
#   START ──→ [llm 节点] ──→ should_continue ──┬──→ [tools 节点] ──→ (回到 llm)
#                          (条件路由)          │
#                                              └──→ END（结束循环）
#
# 核心思想：LLM 思考 → 判断是否需要工具 → 执行工具 → 再回到 LLM 思考，
# 直到 LLM 不再请求工具调用，给出最终回答为止。

def build_graph():
    """
    构建并编译 Agent 状态图。

    StateGraph 是 LangGraph 的核心类，用于定义一个有向图：
      - 节点（Node）：执行具体逻辑的函数（llm_node、tool_node）
      - 边（Edge）：定义节点之间的流转关系
      - 条件边（Conditional Edge）：根据运行时状态动态决定下一个节点

    编译（compile）后会返回一个可执行的 Runnable，
    支持 invoke（同步执行）、stream（流式输出）等方法。
    """
    # 创建状态图，传入 AgentState 作为所有节点共享的状态类型定义
    graph = StateGraph(AgentState)

    # ---- 添加节点 ----
    # 每个节点是一个函数，接收 state 作为参数，返回要更新的字段
    graph.add_node("llm", llm_node)      # 思考节点：调用 LLM 进行推理
    graph.add_node("tools", tool_node)    # 工具节点：执行 LLM 请求的工具

    # ---- 添加边 ----
    # 固定边：从 START 入口直接连接到 llm 节点
    # START 是 LangGraph 提供的特殊标记，表示图的起始入口
    graph.add_edge(START, "llm")

    # 条件边：从 llm 节点出发，根据 should_continue 函数的返回值
    # 动态决定下一步走向。
    # 第三个参数是映射表：should_continue 的返回值 → 目标节点名
    #   - 返回 "tools" → 进入 tools 节点执行工具
    #   - 返回 "end"   → 进入 END 结束图执行
    graph.add_conditional_edges(
        "llm",              # 源节点
        should_continue,    # 路由判断函数
        {"tools": "tools", "end": END}  # 返回值到目标节点的映射
    )

    # 固定边：工具执行完毕后回到 llm 节点，形成 Agent-Loop 循环
    # 这是 ReAct 模式的关键 —— 工具结果需要反馈给 LLM 继续推理
    graph.add_edge("tools", "llm")

    # compile() 编译状态图，验证图的完整性（所有节点是否可达等），
    # 返回一个 CompiledGraph 实例，可以直接 invoke 执行
    return graph.compile()


# 构建并编译 Agent 状态图
agent_graph = build_graph()


# 5. 运行交互循环
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("AI Agent Demo - LangGraph版本（支持多轮对话）")
    print("已注册工具: get_weather")
    print("输入'exit'或'quit'退出，'clear'清空对话历史")
    print("=" * 50 + "\n")

    chat_history = []  # 维护跨多轮对话的完整消息历史

    while True:
        try:
            user_input = input("用户: ").strip()

            if user_input.lower() in ["quit", "exit", "q", "byebye", "拜拜", "再见"]:
                print("拜拜！祝您有美好的一天！")
                break

            if not user_input:
                print("请输入有效指令或问题。\n")
                continue

            # 将用户输入作为 HumanMessage 追加到对话历史
            chat_history.append(HumanMessage(content=user_input))

            # 执行 Agent 状态图（核心调用）
            # invoke 会从 START 开始执行整个图，按照边和条件边的定义
            # 在 llm → tools → llm 之间循环，直到 LLM 不再请求工具调用
            response = agent_graph.invoke(
                {"messages": chat_history},
                # recursion_limit 限制图的最大迭代步数，
                # 防止 Agent 陷入无限循环（例如工具反复调用）
                config={"recursion_limit": 10}
            )

            # 获取最终的 AI 回复
            ai_message = response["messages"][-1]

            # 更新对话历史（保留完整的消息列表）
            chat_history = response["messages"]

            print(f"\nAgent: {ai_message.content}\n")

        except KeyboardInterrupt:
            print("\n再见！")
            break
        except Exception as e:
            print(f"\n发生错误: {e}\n")

