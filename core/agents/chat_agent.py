"""
自由对话 Agent

无 @指令时的默认 Agent，支持自由对话和创作建议，不支持编辑小说文件。
"""
from core.agents.base_agent import BaseAgent
from core.tools import get_tools_by_names
from core.prompts import get_prompt, CHAT_AGENT_PROMPT
from core.agent_logger import logger


class ChatAgent(BaseAgent):
    """默认 Agent，用于自由对话，仅绑定 ask_user 和 fetch_url 工具。"""
    
    def __init__(self):
        tools = get_tools_by_names(['ask_user', 'fetch_url', 'invoke_skill'])
        
        super().__init__(
            name="ChatAgent",
            system_prompt=get_prompt(CHAT_AGENT_PROMPT),
            tools=tools
        )
        
        logger.info("自由对话 Agent 已初始化")


if __name__ == '__main__':
    agent = ChatAgent()
    response = agent.chat("你好，你能做什么？")
    print(f"\nAgent: {response}")
