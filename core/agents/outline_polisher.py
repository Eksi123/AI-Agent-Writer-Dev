"""
OutlinePolisher Agent
职责：
- 优化大纲结构
- 完善角色设定
- 优化世界观设定
- 调整剧情安排
"""
from typing import Optional
from core.agents.base_agent import BaseAgent
from core.tools import get_tools_by_names
from core.project_manager import ProjectManager, NovelProject
from core.config import config_manager
from core.prompts import get_prompt, OUTLINE_POLISHER_PROMPT
from core.agent_logger import logger


class OutlinePolisher(BaseAgent):
    """
    大纲润色 Agent
    负责优化大纲结构和设定
    """
    
    def __init__(self):
        """初始化大纲润色 Agent"""
        # 获取大纲编辑所需的工具
        tools = get_tools_by_names([
            'read_file',
            'write_file',
            'edit_file',
            'ask_user'
        ])
        
        super().__init__(
            name="OutlinePolisher",
            system_prompt=get_prompt(OUTLINE_POLISHER_PROMPT),
            tools=tools
        )
        
        # 项目管理器
        self.project_manager = ProjectManager(config_manager.get_output_dir())
        
        # 当前项目
        self.current_project: Optional[NovelProject] = None
        
        logger.info("大纲润色 Agent 已初始化")
    
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
    
    def get_outline(self) -> str:
        """获取当前项目的大纲"""
        if not self.current_project:
            return "错误: 未选择项目"
        
        return self.current_project.read_outline()
    
    def update_outline(self, content: str) -> str:
        """更新大纲"""
        if not self.current_project:
            return "错误: 未选择项目"
        
        self.current_project.write_outline(content)
        return "大纲已更新"


if __name__ == '__main__':
    # 测试代码
    polisher = OutlinePolisher()
    
    response = polisher.chat("你好，请介绍一下你能做什么")
    print(f"\nAgent: {response}")
