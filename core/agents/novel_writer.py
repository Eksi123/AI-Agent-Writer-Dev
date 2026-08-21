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
        
        # 保存原始 system prompt（用于后续更新）
        self._original_system_prompt = get_prompt(WRITER_PROMPT)
        
        super().__init__(
            name="NovelWriter",
            system_prompt=self._original_system_prompt,
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
            # 设置允许写入的项目目录
            from core.tools.builtin.write_tool import set_allowed_project_dir
            set_allowed_project_dir(project.base_dir)
            
            # 在 system prompt 中注入项目路径信息（每次都更新）
            outline_path = project.outline_path
            chapters_dir = project.chapters_dir
            self.system_prompt = f"""## 当前项目信息

**项目目录**：`{project.base_dir}`
**大纲文件**：`{outline_path}`
**章节目录**：`{chapters_dir}`

## 文件操作规则（必须严格遵守）

1. **只能查询、操作、更新当前小说目录下的文件**
2. 大纲文件路径：`{outline_path}`
3. 章节文件路径：`{chapters_dir}/...`
4. **禁止**在项目目录外创建或修改任何文件
5. 使用工具时必须使用上述绝对路径

{self._original_system_prompt}"""
            logger.info(f"已注入项目路径信息到 {self.name}: {project.base_dir}")
            
            # 重新初始化 AgentGraph，使新的 system_prompt 生效
            self._init_agent_graph()
            
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
