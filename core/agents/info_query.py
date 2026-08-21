"""
InfoQuery Agent
职责：
- 查询小说内各种细节信息
- 查询网络上信息
"""
from typing import Optional
from core.agents.base_agent import BaseAgent
from core.tools import get_tools_by_names
from core.project_manager import ProjectManager, NovelProject
from core.config import config_manager
from core.agent_logger import logger


# 系统提示词
INFO_QUERY_SYSTEM_PROMPT = """你是一个专业的信息查询助手，擅长查询小说内外的各种信息。

## 职责

1. **小说内信息查询**：
   - 查询特定情节出现在哪些章节
   - 查询角色的出场记录
   - 查询特定地点的描述
   - 查询时间线信息

2. **网络信息查询**：
   - 查询历史背景资料
   - 查询地理信息
   - 查询文化知识
   - 查询其他参考资料

## 工作方式

1. 理解用户的查询需求
2. 确定查询来源（小说内容 or 网络）
3. 使用相应工具进行查询
4. 整理并呈现查询结果

## 注意事项

- 确保查询结果准确
- 注明来源（小说第X章 or 网络链接）
- 对于不确定的信息，明确说明
"""


class InfoQuery(BaseAgent):
    """
    信息查询 Agent
    负责查询小说内外的各种信息
    """
    
    def __init__(self):
        """初始化信息查询 Agent"""
        # 获取查询所需的工具
        tools = get_tools_by_names([
            'read_file',
            'glob_search',
            'list_directory',
            'fetch_url',
            'ask_user'
        ])
        
        super().__init__(
            name="InfoQuery",
            system_prompt=INFO_QUERY_SYSTEM_PROMPT,
            tools=tools
        )
        
        # 项目管理器
        self.project_manager = ProjectManager(config_manager.get_output_dir())
        
        # 当前项目
        self.current_project: Optional[NovelProject] = None
        
        logger.info("信息查询 Agent 已初始化")
    
    def set_project(self, project_name: str) -> bool:
        """设置当前项目"""
        project = self.project_manager.load_project(project_name)
        
        if project:
            self.current_project = project
            logger.info(f"已切换到项目: {project_name}")
            return True
        else:
            logger.warning(f"项目不存在: {project_name}")
            return False


if __name__ == '__main__':
    # 测试代码
    query_agent = InfoQuery()
    
    response = query_agent.chat("你好，请介绍一下你能做什么")
    print(f"\nAgent: {response}")
