"""
InfoQuery Agent

查询小说内部的各种细节信息，支持情节、角色、地点等内容检索。
"""
from typing import Optional
from core.agents.base_agent import BaseAgent
from core.tools import get_tools_by_names
from core.tools.builtin.write_tool import set_allowed_project_dir
from core.project_manager import ProjectManager, NovelProject
from core.config_manager import config_manager
from core.agent_logger import logger


# 系统提示词
INFO_QUERY_SYSTEM_PROMPT = """你是一个专业的信息查询助手，擅长查询小说内部的各种细节信息。

## 默认操作规则（必须遵守）

- **你默认操作的路径就是当前小说项目目录**，无需向用户确认目录位置
- 当用户要求查询小说信息时，直接使用系统注入的章节文件路径进行读取
- **禁止**反问用户"章节在哪个目录"、"请提供文件路径"等问题
- 系统已自动注入章节的绝对路径，直接使用即可

## 职责

1. **小说内信息查询**：
   - 查询特定情节出现在哪些章节
   - 查询角色的出场记录
   - 查询特定地点的描述
   - 查询时间线信息

2. **设定信息检索**：
   - 查询世界观设定
   - 查询角色关系
   - 查询势力/组织信息
   - 查询物品/技能等设定

## 工作方式

1. 理解用户的查询需求
2. 在小说项目目录中检索相关文件
3. 使用相应工具进行查询
4. 整理并呈现查询结果

## 注意事项

- 确保查询结果准确
- 注明来源（小说第X卷第X章）
- 对于不确定的信息，明确说明
"""


class InfoQuery(BaseAgent):
    """
    信息查询 Agent，负责查询小说内部的各种细节信息。
    
    绑定的工具：read_file、glob_search、list_directory、ask_user
    """
    
    def __init__(self):
        tools = get_tools_by_names([
            'read_file',
            'glob_search',
            'list_directory',
            'ask_user',
            'invoke_custom_tool'
        ])
        
        self._original_system_prompt = INFO_QUERY_SYSTEM_PROMPT
        
        super().__init__(
            name="InfoQuery",
            system_prompt=self._original_system_prompt,
            tools=tools
        )
        
        self.project_manager = ProjectManager(config_manager.get_output_dir())
        self.current_project: Optional[NovelProject] = None
        
        logger.info("信息查询 Agent 已初始化")
    
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


if __name__ == '__main__':
    query_agent = InfoQuery()
    response = query_agent.chat("你好，请介绍一下你能做什么")
    print(f"\nAgent: {response}")
