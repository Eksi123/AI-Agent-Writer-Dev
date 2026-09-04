"""
自由对话 Agent

无 @指令时的默认 Agent，支持自由对话和创作建议，不支持编辑小说文件。
"""
from core.agents.base_agent import BaseAgent
from core.tools import get_tools_by_names
from core.agent_logger import logger


# 系统提示词
CHAT_SYSTEM_PROMPT = """你是一个友好的 AI 助手，专门协助用户进行小说创作相关的工作。

## 职责

1. **自由对话**：与用户进行自然流畅的对话
2. **创作建议**：提供小说创作的建议和灵感
3. **问题解答**：回答用户关于写作的问题
4. **信息查询**：帮助用户查询相关信息

## 注意事项

- 当前模式下不能直接编辑小说文件
- 如需编辑小说，请使用相应的 @指令切换 Agent：
  - `@写作` - 执行写作工作流
  - `@大纲润色` - 优化大纲
  - `@小说润色` - 润色正文
  - `@汇总说明` - 生成汇总信息
  - `@信息查询` - 查询详细信息

## 可用工具

你可以使用以下工具：
- `ask_user` - 向用户提问
- `fetch_url` - 从互联网获取资料
"""


class ChatAgent(BaseAgent):
    """默认 Agent，用于自由对话，仅绑定 ask_user 和 fetch_url 工具。"""
    
    def __init__(self):
        tools = get_tools_by_names(['ask_user', 'fetch_url', 'invoke_custom_tool'])
        
        super().__init__(
            name="ChatAgent",
            system_prompt=CHAT_SYSTEM_PROMPT,
            tools=tools
        )
        
        logger.info("自由对话 Agent 已初始化")


if __name__ == '__main__':
    agent = ChatAgent()
    response = agent.chat("你好，你能做什么？")
    print(f"\nAgent: {response}")
