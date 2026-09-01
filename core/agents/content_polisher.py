"""
ContentPolisher Agent

对小说章节进行内容润色、文笔优化和修辞增强。
"""
from typing import Optional
from core.agents.base_agent import BaseAgent
from core.tools import get_tools_by_names
from core.tools.builtin.write_tool import set_allowed_project_dir
from core.project_manager import ProjectManager, NovelProject
from core.config_manager import config_manager
from core.prompts import get_prompt, CONTENT_POLISHER_PROMPT
from core.agent_logger import logger


class ContentPolisher(BaseAgent):
    """
    小说润色 Agent，负责章节内容润色和文笔优化。
    
    绑定的工具：read_file、write_file、edit_file、glob_search、list_directory、ask_user
    """
    
    def __init__(self):
        tools = get_tools_by_names([
            'read_file',
            'write_file',
            'edit_file',
            'glob_search',
            'list_directory',
            'fetch_url',
            'ask_user'
        ])
        
        self._original_system_prompt = get_prompt(CONTENT_POLISHER_PROMPT)
        
        super().__init__(
            name="ContentPolisher",
            system_prompt=self._original_system_prompt,
            tools=tools
        )
        
        self.project_manager = ProjectManager(config_manager.get_output_dir())
        self.current_project: Optional[NovelProject] = None
        
        logger.info("小说润色 Agent 已初始化")
    
    def set_project(self, project_name: str) -> bool:
        """
        设置当前项目
        
        流程：
        1. 加载项目信息
        2. 设置允许写入的项目目录（安全限制）
        3. 在 system prompt 中注入项目路径信息
        4. 重新初始化 AgentGraph 使新配置生效
        
        Args:
            project_name: 项目名称
        
        Returns:
            是否成功
        """
        project = self.project_manager.load_project(project_name)
        
        if project:
            self.current_project = project
            set_allowed_project_dir(project.base_dir)
            
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
            
            self._init_agent_graph()
            
            logger.info(f"已切换到项目: {project_name}")
            return True
        else:
            logger.warning(f"项目不存在: {project_name}")
            return False
    
    def get_chapter_content(self, volume: int, chapter: int) -> str:
        """获取指定章节的内容"""
        if not self.current_project:
            return "错误: 未选择项目"
        
        return self.current_project.read_chapter(volume, chapter)
    
    def update_chapter(self, volume: int, chapter: int, content: str, 
                      chapter_name: str = "") -> str:
        """更新章节内容并保存到文件"""
        if not self.current_project:
            return "错误: 未选择项目"
        
        self.current_project.write_chapter(volume, chapter, content, chapter_name)
        return "章节已更新"


if __name__ == '__main__':
    polisher = ContentPolisher()
    response = polisher.chat("你好，请介绍一下你能做什么")
    print(f"\nAgent: {response}")
