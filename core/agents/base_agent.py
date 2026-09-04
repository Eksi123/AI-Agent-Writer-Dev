"""
Agent 基类模块

提供所有 Agent 的统一基类实现，封装 LLM 调用、工具绑定和对话历史管理。
具体 Agent（如小说写作 Agent、大纲优化 Agent）应继承此基类。
"""
from typing import List, Optional
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import BaseTool
from core.agent_graph import AgentGraph, create_agent_graph
from core.config_manager import config_manager
from core.agent_logger import logger
from core.tools import get_all_tools, get_skill_prompts_for_agent, get_custom_tools_info


class BaseAgent:
    """
    Agent 基类，封装 LLM 调用和工具绑定。
    
    所有具体 Agent 都应继承此类，并通过以下方式定制行为：
    - 传入不同的 system_prompt（系统提示词）
    - 绑定不同的 tools（工具列表）
    - 可选：继承并重写 chat() 方法添加自定义逻辑
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
            name: Agent 名称（用于日志标识）
            system_prompt: 系统提示词（定义 Agent 的角色和行为）
            tools: 工具列表（Agent 可调用的工具）
            temperature: 温度参数（控制生成文本的随机性，0-1 之间）
        """
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools
        self.temperature = temperature
        
        self.chat_history: List[dict] = []
        self._init_agent_graph()
    
    def _init_agent_graph(self) -> None:
        """初始化 Agent 图，从配置管理器读取 LLM 配置并创建 AgentGraph 实例。
        自动将匹配的 Skill 提示词追加到 system_prompt 末尾。
        """
        config = config_manager.get_llm_config()
        
        # 拼接 Skill 提示词到 system_prompt
        full_prompt = self._build_full_prompt()
        
        self.agent_graph: AgentGraph = create_agent_graph(
            base_url=config["api_url"],
            api_key=config["api_key"],
            model=config["model_name"],
            tools=self.tools,
            system_prompt=full_prompt,
            temperature=config["temperature"]
        )
        
        logger.debug(f"Agent 已初始化: {self.name}")
    
    def _build_full_prompt(self) -> str:
        """
        构建完整的 system_prompt：基础提示词 + 匹配的 Skill 提示词 + 自定义工具列表。
        Skill 提示词和自定义工具列表追加在末尾，LLM 天然更重视后面的指令。
        """
        parts = [self.system_prompt]
        
        # 拼接 Skill 提示词
        skill_prompts = get_skill_prompts_for_agent(self.name)
        if skill_prompts:
            separator = "\n\n---\n\n"
            parts.extend(skill_prompts)
            logger.info(f"[{self.name}] system_prompt 已注入 {len(skill_prompts)} 个 Skill 提示词")
        
        # 拼接自定义工具列表（通过 invoke_custom_tool 调用）
        custom_tools = get_custom_tools_info()
        if custom_tools:
            tool_list_text = "\n\n## 可用的自定义工具（通过 invoke_custom_tool 调用）\n"
            tool_list_text += "如需使用以下工具，请调用 invoke_custom_tool 工具，传入工具名称和参数。\n\n"
            for tool_info in custom_tools:
                tool_list_text += f"- **{tool_info['name']}**: {tool_info['description']}\n"
            parts.append(tool_list_text)
            logger.info(f"[{self.name}] system_prompt 已注入 {len(custom_tools)} 个自定义工具信息")
        
        separator = "\n\n---\n\n"
        return separator.join(parts)
    
    def reload_llm(self) -> None:
        """重新加载 LLM 配置，用于设置变更后刷新 Agent 的大模型连接。"""
        self._init_agent_graph()
        logger.info(f"Agent LLM 已重新加载: {self.name}")
    
    def chat(self, user_input: str, max_iterations: int = 30) -> dict:
        """
        与 Agent 对话
        
        Args:
            user_input: 用户输入
            max_iterations: 最大迭代次数
                           - 默认 30 次（子任务限制，防止无限循环）
                           - 传入 0 表示不限制（长任务场景）
        
        Returns:
            包含以下字段的字典：
            - response: AI 回复文本
            - thought_process: 思考过程记录（用于调试和前端展示）
            - error: 是否发生错误（仅在出错时存在）
        """
        self.chat_history.append({"role": "user", "content": user_input})
        
        try:
            result = self.agent_graph.invoke(self.chat_history, max_iterations=max_iterations)
            response = self.agent_graph.get_last_response(result)
            thought_process = result.get("thought_process", [])
            self.chat_history = result["messages"]
            
            logger.debug(f"[{self.name}] 用户: {user_input[:50]}...")
            logger.debug(f"[{self.name}] Agent: {response[:50]}...")
            
            return {
                "response": response,
                "thought_process": thought_process
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[{self.name}] LLM 调用失败: {error_msg}")
            
            hint = self._generate_error_hint(error_msg)
            
            return {
                "response": hint,
                "thought_process": [],
                "error": True
            }
    
    def _generate_error_hint(self, error_msg: str) -> str:
        """
        根据错误类型生成用户友好的提示信息
        
        Args:
            error_msg: 原始错误消息
        
        Returns:
            格式化的错误提示文本
        """
        error_lower = error_msg.lower()
        
        if 'authentication' in error_lower or 'api key' in error_lower or '401' in error_msg:
            return '❌ **API Key 无效或已过期**\n\n请检查设置中的 API Key 是否正确，或重新设置环境变量 LLM_API_KEY'
        elif 'connect' in error_lower or 'refused' in error_lower or 'timeout' in error_lower:
            return '❌ **无法连接到模型服务**\n\n请检查 API 地址是否正确；如使用 Ollama 请确认服务已启动'
        elif 'model' in error_lower or 'not found' in error_lower or '404' in error_msg:
            return '❌ **模型不可用**\n\n模型名称不正确或服务未提供该模型，请检查模型名称'
        elif 'rate limit' in error_lower or '429' in error_msg:
            return '❌ **请求频率超限**\n\n请稍后再试，或联系服务提供商提升限额'
        else:
            return f'❌ **模型调用失败**\n\n{error_msg[:300]}'
    
    def clear_history(self) -> None:
        """清空对话历史，重置对话上下文。"""
        self.chat_history = []
        logger.debug(f"[{self.name}] 对话历史已清空")
    
    def get_history_length(self) -> int:
        """获取对话历史中的消息数量。"""
        return len(self.chat_history)


if __name__ == '__main__':
    tools = get_all_tools()
    
    agent = BaseAgent(
        name="测试Agent",
        system_prompt="你是一个智能助手。",
        tools=tools
    )
    
    response = agent.chat("你好，请介绍一下自己")
    print(f"\nAgent: {response}")
