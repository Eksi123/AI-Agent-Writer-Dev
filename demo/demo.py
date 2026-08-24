'''
AI Agent Demo - 原生实现

重点介绍 Agent-Loop、工具注册和调用等实现原理。
核心概念：
- Agent-Loop：思考 → 行动 → 反馈（循环直到完成）
- Tool Call：工具定义 → 注册 → 调用 → 执行

这是一个教学示例，展示如何用纯 OpenAI API 实现 Agent 模式。
'''

import os
import json
import openai

# 1. 大模型封装
class LLM:
    """
    OpenAI 兼容的 LLM 封装
    
    ChatCompletion 响应结构：
    - response.choices[0].message.content: 文本回复
    - response.choices[0].message.tool_calls: 工具调用列表
    """
    def __init__(self):
        api_key = os.environ.get("LLM_API_KEY")
        if not api_key:
            raise ValueError("环境变量 LLM_API_KEY 未设置，请先设置 API Key")
        
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            timeout=30
        )
        self.model = "qwen3.7-plus"

    def chat(self, messages, tools=None):
        """调用大模型，支持工具调用"""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 512,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message

llm = LLM()


# 2. 工具注册表：存储工具名称、描述、参数 Schema 和执行函数
tool_registry_list = {}

def register_tool(tool_name, description, parameters, func):
    """注册工具"""
    tool_registry_list[tool_name] = {
        "description": description,
        "parameters": parameters,
        "function": func
    }

def get_tools_schema():
    """获取工具的OpenAI格式schema"""
    return [
        {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": info["description"],
                "parameters": info["parameters"]
            }
        }
        for tool_name, info in tool_registry_list.items()
    ]


# 3. 自定义工具定义和注册
def get_weather(city: str) -> str:
    """Mock天气查询"""
    mock_data = {
        "北京": {"天气": "晴", "温度": "25°C", "湿度": "40%", "风力": "微风"},
        "上海": {"天气": "多云", "温度": "22°C", "湿度": "65%", "风力": "东南风3级"},
        "广州": {"天气": "小雨", "温度": "28°C", "湿度": "80%", "风力": "南风2级"},
        "深圳": {"天气": "阴", "温度": "26°C", "湿度": "70%", "风力": "东风2级"},
    }
    
    data = mock_data.get(city, {"天气": "未知", "温度": "N/A", "湿度": "N/A", "风力": "N/A"})
    result = {"城市": city, **data}
    return json.dumps(result, ensure_ascii=False)

# 注册工具到全局注册表
register_tool(  
    tool_name="get_weather",
    description="查询指定城市的天气信息",
    parameters={
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "城市名称，如：北京、上海"
            }
        },
        "required": ["city"]
    },
    func=get_weather
)


# 4. Agent-Loop简单实现
def execute_tool(tool_name: str, tool_args: dict) -> str:
    """执行调用的工具"""
    if tool_name not in tool_registry_list:
        return f"错误：工具 {tool_name} 不存在"
    
    tool_func = tool_registry_list[tool_name]["function"]
    return tool_func(**tool_args)

def agent_loop(user_input: str, max_iterations: int = 5):
    """Agent-Loop：思考 -> 行动 -> 观察"""
    
    messages = [
        {"role": "system", "content": "你是一个智能助手，可以使用工具来帮助用户完成任务。"},
        {"role": "user", "content": user_input}
    ]

    tools = get_tools_schema()
    
    for _ in range(max_iterations):
        # 1. LLM思考决策
        response = llm.chat(messages, tools=tools)
        
        # 2. 判断是否需要调用工具
        if response.tool_calls:
            messages.append({
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": response.tool_calls
            })
            
            # 3. 执行工具调用
            for tool_call in response.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                print(f"[调用工具] {tool_name}({tool_args})")
                tool_result = execute_tool(tool_name, tool_args)
                print(f"[工具结果] {tool_result}")
                
                # 4. 将工具结果反馈给LLM
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result
                })
        else:
            # 没有工具调用，返回最终回答
            return response.content
    
    return "抱歉，处理过程超出循环次数，请重新尝试。"


# Agent 启动   
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("AI Agent Demo演示")
    print("已注册工具: get_weather (Mock)")
    print("输入'exit'或'quit' 退出")
    print("=" * 50 + "\n")
    
    while True:
        try:
            # 输入完成后点击enter回车
            user_input = input("用户: ").strip()
            
            if user_input.lower() in ["quit", "exit", "q", "byebye", "拜拜", "再见"]:
                print("拜拜！祝您有美好的一天！")
                break
            
            if not user_input:
                print("请输入有效指令或问题。")
                continue
            
            response = agent_loop(user_input)
            print(f"\nAgent: {response}\n")
            
        except KeyboardInterrupt:
            print("\n再见！")
            break
        except Exception as e:
            print(f"\n发生错误: {e}\n")