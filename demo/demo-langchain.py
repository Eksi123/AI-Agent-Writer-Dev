"""
AI Agent Demo - LangChain版本
使用LangChain实现Agent-Loop：思考 -> 行动 -> 反馈
"""

import json
from configparser import ConfigParser
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain.agents import create_agent

# 1. 读取配置
import os
config = ConfigParser()
config.read('config.ini')
api_key = os.environ.get("LLM_API_KEY")
if not api_key:
    raise ValueError("环境变量 LLM_API_KEY 未设置，请先设置 API Key")
base_url = config.get('llm_api_aliyun', 'base_url')
model = config.get('llm_api_aliyun', 'model')

# 2. 创建LLM实例
llm = ChatOpenAI(
    api_key=api_key,
    base_url=base_url,
    model=model,
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

# 4. 创建Agent
tools = [get_weather]
chat_history = []

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt="你是一个智能助手，可以使用工具来帮助用户完成任务。"
)

# 5. 运行交互循环
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("AI Agent Demo - LangChain版本（支持多轮对话）")
    print("已注册工具: get_weather")
    print("输入'exit'或'quit'退出，'clear'清空对话历史")
    print("=" * 50 + "\n")
    
    while True:
        try:
            user_input = input("用户: ").strip()
            
            if user_input.lower() in ["quit", "exit", "q", "byebye", "拜拜", "再见"]:
                print("拜拜！祝您有美好的一天！")
                break
            
            if not user_input:
                print("请输入有效指令或问题。")
                continue
            
            # 将用户输入加入历史
            chat_history.append(HumanMessage(content=user_input))

            # 调用Agent，传入对话历史
            response = agent.invoke(
                {"messages": chat_history},
                # recursion_limit 控制最大迭代次数
                config={"recursion_limit": 10}
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
