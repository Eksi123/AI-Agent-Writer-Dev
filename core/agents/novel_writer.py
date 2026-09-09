"""
NovelWriter Agent

执行完整的写作工作流：大纲审查 → 逐章写作 → 逻辑审查。
管理小说项目的创建、大纲和章节的读写操作。
"""
from typing import Optional
from core.agents.base_agent import BaseAgent
from core.tools import get_tools_by_names
from core.tools.builtin.write_tool import set_allowed_project_dir
from core.project_manager import ProjectManager, NovelProject
from core.config_manager import config_manager
from core.prompts import get_prompt, WRITER_PROMPT
from core.agent_logger import logger


class NovelWriter(BaseAgent):
    """
    写作 Agent，负责执行完整的写作工作流。
    
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
            'ask_user',
            'invoke_skill'
        ])
        
        self._original_system_prompt = get_prompt(WRITER_PROMPT)
        
        super().__init__(
            name="NovelWriter",
            system_prompt=self._original_system_prompt,
            tools=tools
        )
        
        self.project_manager = ProjectManager(config_manager.get_output_dir())
        self.current_project: Optional[NovelProject] = None
        
        logger.info("写作 Agent 已初始化")
    
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
