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

# 4.1 定义状态类型（所有节点共享 messages 列表）
class AgentState(TypedDict):
    """
    AgentState 定义了图中每个节点共享的状态数据。
    messages 字段使用 add_messages 注解，表示新消息会追加到列表中
    """
    messages: Annotated[list, add_messages]


# 4.2 定义图的节点
llm_with_tools = llm.bind_tools(tools)  # 绑定工具，使 LLM 具备 tool_call 能力

def llm_node(state: AgentState) -> dict:
    """
    Agent节点：负责"思考" —— 调用LLM进行推理决策。
    LLM会根据当前消息历史决定：
      - 是否需要调用工具（返回 tool_calls）
      - 还是直接给出最终回答（返回 content）
    """
    system_prompt = SystemMessage(content="你是一个智能助手，可以使用工具来帮助用户完成任务。")
    response = llm_with_tools.invoke([system_prompt] + state["messages"])
    # 返回新消息，LangGraph 会自动通过 add_messages 追加到 state["messages"]
    return {"messages": [response]}

def tool_node(state: AgentState) -> dict:
    """
    工具执行节点：执行 LLM 请求的工具调用。
    遍历最后一条 AI 消息中的 tool_calls，逐一执行工具，
    并将结果以 ToolMessage 形式返回，反馈给 LLM。
    """
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls

    results = []
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        print(f"  [调用工具] {tool_name}({tool_args})")

        # 在注册的工具中查找并执行
        tool_map = {t.name: t for t in tools}
        tool_result = tool_map[tool_name].invoke(tool_args)

        print(f"  [工具结果] {tool_result}")

        # 构造 ToolMessage，携带工具执行结果
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


# 4.4 基于LangGraph构建Agent状态图（StateGraph）
def build_graph():
    """
    构建 Agent 状态图：
    - 节点：llm（LLM 思考）、tools（工具执行）
    - 边：START → llm → should_continue → tools/end → llm（循环）
    """
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("llm", llm_node)
    graph.add_node("tools", tool_node)

    # 添加边：入口 → LLM
    graph.add_edge(START, "llm")
    
    # 添加条件边：LLM → tools（如果有工具调用）或 END（如果没有）
    graph.add_conditional_edges(
        "llm",
        should_continue,
        {"tools": "tools", "end": END}
    )
    
    # 添加边：tools → llm（工具执行完后回到 LLM 继续思考）
    graph.add_edge("tools", "llm")

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

    chat_history = []

    while True:
        try:
            user_input = input("用户: ").strip()

            if user_input.lower() in ["quit", "exit", "q", "byebye", "拜拜", "再见"]:
                print("拜拜！祝您有美好的一天！")
                break

            if not user_input:
                print("请输入有效指令或问题。\n")
                continue

            # 将用户输入加入对话历史
            chat_history.append(HumanMessage(content=user_input))

            # 执行 Agent 状态图
            response = agent_graph.invoke(
                {"messages": chat_history},
                config={"recursion_limit": 10}  # 控制最大迭代次数
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

