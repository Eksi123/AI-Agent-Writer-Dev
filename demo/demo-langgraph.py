"""
AI Agent Demo - LangGraph版本
使用LangGraph的节点(Node)和边(Edge)实现Agent-Loop：思考 -> 行动 -> 观察
"""

import json
from typing import Annotated, TypedDict, Literal
from configparser import ConfigParser

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode


# 1. 读取配置
config = ConfigParser()
config.read('config.ini')
api_key = config.get('llm_api_aliyun', 'api_key')
base_url = config.get('llm_api_aliyun', 'base_url')
model_name = config.get('llm_api_aliyun', 'model')


# 2. 创建LLM实例
llm = ChatOpenAI(
    api_key=api_key,
    base_url=base_url,
    model=model_name,
    temperature=0,
    max_tokens=512
)


# 3. 定义工具（使用@tool装饰器）
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


# 4. Agent定义

# 4.1 定义Agent状态（State）
class AgentState(TypedDict):
    """
    AgentState 定义了图中每个节点共享的状态数据。
    messages 字段使用 add_messages 注解，表示新消息会追加到列表中
    """
    messages: Annotated[list, add_messages]


# 4.2 定义图的节点（Node）
llm_with_tools = llm.bind_tools(tools) # # 绑定工具到LLM，使其具备 tool_call 能力

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
    工具节点：负责"行动" —— 执行LLM决策中请求的工具调用。
    遍历最后一条AI消息中的 tool_calls，逐一执行工具，
    并将结果以 ToolMessage 形式返回，反馈给LLM。
    """
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls

    results = []
    for tool_call in tool_calls:
        # 查找对应工具并执行
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

    # 返回工具结果消息，追加到 state["messages"]
    return {"messages": results}


# 4.3 定义图的条件边（Conditional Edge）
def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """
    路由函数：决定Agent节点的下一步走向。
    - 如果LLM的响应中包含 tool_calls → 路由到 "tools" 节点执行工具
    - 否则 → 路由到 END，结束循环，输出最终回答
    这就是 Agent-Loop 中"思考 -> 行动 / 结束"的核心分支逻辑。
    """
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "end"


# 4.4 基于LangGraph构建Agent状态图（StateGraph）
def build_graph():
    """
    构建Agent的状态图，结构如下：

        START
          │
          ▼
       ┌──────┐
       │llm │◄─────────┐
       └──┬───┘          │
          │              │
     should_continue     │
        ╱       ╲        │
       ▼         ▼       │
    ┌───────┐   END      │
    │ tools │            │
    └───┬───┘            │
        │                │
        └────────────────┘
            (回到llm)

    节点：
      - llm：LLM思考决策
      - tools：工具执行
    边：
      - START → llm：入口
      - llm → should_continue：根据是否有tool_calls决定走向
      - tools → llm：工具执行完毕后回到llm继续思考
      - llm → END：无工具调用时结束
    """
    # 创建状态图，指定状态类型
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("llm", llm_node)
    graph.add_node("tools", tool_node)

    # 添加边
    graph.add_edge(START, "llm")                    # 入口：START → llm
    graph.add_conditional_edges(                       # 条件边：llm → tools | END
        "llm",
        should_continue,
        {"tools": "tools", "end": END}
    )
    graph.add_edge("tools", "llm")                   # 工具执行后回到llm

    # 编译图
    return graph.compile()


# 构建Agent图
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

            # 将用户输入加入历史
            chat_history.append(HumanMessage(content=user_input))

            # 调用Agent图
            response = agent_graph.invoke(
                {"messages": chat_history},
                config={"recursion_limit": 10}  # 控制最大迭代次数
            )

            # 获取最终AI回复
            ai_message = response["messages"][-1]

            # 更新对话历史（替换为完整的消息列表）
            chat_history = response["messages"]

            print(f"\nAgent: {ai_message.content}\n")

        except KeyboardInterrupt:
            print("\n再见！")
            break
        except Exception as e:
            print(f"\n发生错误: {e}\n")

