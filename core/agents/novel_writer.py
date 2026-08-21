"""
NovelWriter Agent
职责：
- 执行写作工作流（大纲审查 → 逐章写作 → 逻辑审查）
- 管理小说项目
- 协调写作流程
"""
from typing import Optional
from core.agents.base_agent import BaseAgent
from core.tools import get_tools_by_names
from core.project_manager import ProjectManager, NovelProject
from core.config import config_manager
from core.prompts import get_prompt, WRITER_PROMPT
from core.agent_logger import logger


class NovelWriter(BaseAgent):
    """
    写作 Agent
    负责执行写作工作流
    """
    
    def __init__(self):
        """初始化写作 Agent"""
        # 获取写作所需的工具
        tools = get_tools_by_names([
            'read_file',
            'write_file',
            'edit_file',
            'glob_search',
            'list_directory',
            'ask_user'
        ])
        
        super().__init__(
            name="NovelWriter",
            system_prompt=get_prompt(WRITER_PROMPT),
            tools=tools
        )
        
        # 项目管理器
        self.project_manager = ProjectManager(config_manager.get_output_dir())
        
        # 当前项目
        self.current_project: Optional[NovelProject] = None
        
        logger.info("写作 Agent 已初始化")
    
    def set_project(self, project_name: str) -> bool:
        """
        设置当前项目
        
        Args:
            project_name: 项目名称
        
        Returns:
            是否成功
        """
        project = self.project_manager.load_project(project_name)
        
        if project:
            self.current_project = project
            logger.info(f"已切换到项目: {project_name}")
            return True
        else:
            logger.warning(f"项目不存在: {project_name}")
            return False
    
    def create_project(self, project_name: str) -> NovelProject:
        """
        创建新项目
        
        Args:
            project_name: 项目名称
        
        Returns:
            NovelProject 实例
        """
        project = self.project_manager.create_project(project_name)
        self.current_project = project
        logger.info(f"项目已创建: {project_name}")
        return project
    
    def get_outline(self) -> str:
        """获取当前项目的大纲"""
        if not self.current_project:
            return "错误: 未选择项目"
        
        return self.current_project.read_outline()
    
    def get_chapter_content(self, volume: int, chapter: int) -> str:
        """获取章节内容"""
        if not self.current_project:
            return "错误: 未选择项目"
        
        return self.current_project.read_chapter(volume, chapter)
    
    def save_chapter(self, volume: int, chapter: int, content: str, 
                    chapter_name: str = "") -> str:
        """保存章节"""
        if not self.current_project:
            return "错误: 未选择项目"
        
        return self.current_project.write_chapter(volume, chapter, content, chapter_name)
    
    def list_chapters(self) -> list:
        """列出所有章节"""
        if not self.current_project:
            return []
        
        return self.current_project.list_chapters()


if __name__ == '__main__':
    # 测试代码
    writer = NovelWriter()
    
    # 创建测试项目
    project = writer.create_project("测试小说")
    
    # 写入大纲
    project.write_outline("# 测试小说\n\n这是一个测试大纲。")
    
    # 获取大纲
    outline = writer.get_outline()
    print(f"大纲:\n{outline}")
