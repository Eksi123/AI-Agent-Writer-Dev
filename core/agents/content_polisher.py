"""
ContentPolisher Agent
职责：
- 章节内容润色
- 文笔优化
- 修辞增强
"""
from typing import Optional
from core.agents.base_agent import BaseAgent
from core.tools import get_tools_by_names
from core.project_manager import ProjectManager, NovelProject
from core.config import config_manager
from core.prompts import get_prompt, CONTENT_POLISHER_PROMPT
from core.agent_logger import logger


class ContentPolisher(BaseAgent):
    """
    小说润色 Agent
    负责章节内容润色和文笔优化
    """
    
    def __init__(self):
        """初始化小说润色 Agent"""
        # 获取章节编辑所需的工具
        tools = get_tools_by_names([
            'read_file',
            'write_file',
            'edit_file',
            'glob_search',
            'list_directory',
            'ask_user'
        ])
        
        super().__init__(
            name="ContentPolisher",
            system_prompt=get_prompt(CONTENT_POLISHER_PROMPT),
            tools=tools
        )
        
        # 项目管理器
        self.project_manager = ProjectManager(config_manager.get_output_dir())
        
        # 当前项目
        self.current_project: Optional[NovelProject] = None
        
        logger.info("小说润色 Agent 已初始化")
    
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
    
    def get_chapter_content(self, volume: int, chapter: int) -> str:
        """获取章节内容"""
        if not self.current_project:
            return "错误: 未选择项目"
        
        return self.current_project.read_chapter(volume, chapter)
    
    def update_chapter(self, volume: int, chapter: int, content: str, 
                      chapter_name: str = "") -> str:
        """更新章节内容"""
        if not self.current_project:
            return "错误: 未选择项目"
        
        self.current_project.write_chapter(volume, chapter, content, chapter_name)
        return "章节已更新"


if __name__ == '__main__':
    # 测试代码
    polisher = ContentPolisher()
    
    response = polisher.chat("你好，请介绍一下你能做什么")
    print(f"\nAgent: {response}")
