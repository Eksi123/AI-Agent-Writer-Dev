"""
SummaryGenerator Agent

生成小说的各类汇总信息，包括人物、地点、剧情和字数统计。
"""
from typing import Optional
from core.agents.base_agent import BaseAgent
from core.tools import get_tools_by_names
from core.tools.builtin.write_tool import set_allowed_project_dir
from core.project_manager import ProjectManager, NovelProject
from core.config_manager import config_manager
from core.agent_logger import logger


# 系统提示词
SUMMARY_SYSTEM_PROMPT = """你是一个专业的小说信息汇总专家，擅长从小说内容中提取和整理各类信息。

## 默认操作规则（必须遵守）

- **你默认操作的路径就是当前小说项目目录**，无需向用户确认目录位置
- 当用户要求生成汇总时，直接使用系统注入的章节文件路径进行读取
- **禁止**反问用户"章节在哪个目录"、"请提供文件路径"等问题
- 系统已自动注入章节的绝对路径，直接使用即可

## 职责

1. **人物汇总**：提取小说中出现的所有角色，包括主角、配角、路人等
2. **地点汇总**：提取小说中出现的所有地点
3. **剧情汇总**：梳理小说的主要剧情线索
4. **字数统计**：统计各章节字数和总字数

## 输出格式

### 人物汇总

| 角色名 | 身份 | 性格特点 | 重要事件 |
|--------|------|----------|----------|
| ... | ... | ... | ... |

### 地点汇总

| 地点名 | 描述 | 出现章节 |
|--------|------|----------|
| ... | ... | ... |

### 剧情汇总

1. **主线剧情**：...
2. **支线剧情**：...

### 字数统计

- 第1章：XXXX 字
- 第2章：XXXX 字
- ...
- 总计：XXXX 字

## 注意事项

- 确保信息准确完整
- 按章节顺序整理
- 突出重要信息
"""


class SummaryGenerator(BaseAgent):
    """
    汇总说明 Agent，负责生成小说的人物、地点、剧情和字数汇总。
    
    绑定的工具：read_file、write_file、glob_search、list_directory、ask_user
    """
    
    def __init__(self):
        tools = get_tools_by_names([
            'read_file',
            'write_file',
            'glob_search',
            'list_directory',
            'ask_user'
        ])
        
        self._original_system_prompt = SUMMARY_SYSTEM_PROMPT
        
        super().__init__(
            name="SummaryGenerator",
            system_prompt=self._original_system_prompt,
            tools=tools
        )
        
        self.project_manager = ProjectManager(config_manager.get_output_dir())
        self.current_project: Optional[NovelProject] = None
        
        logger.info("汇总说明 Agent 已初始化")
    
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
    
    def get_all_chapters_content(self) -> str:
        """获取当前项目所有章节的内容，返回拼接后的完整文本"""
        if not self.current_project:
            return "错误: 未选择项目"
        
        chapters = self.current_project.list_chapters()
        contents = []
        
        for chapter_path in chapters:
            with open(chapter_path, 'r', encoding='utf-8') as f:
                content = f.read()
                contents.append(f"\n\n{'='*50}\n文件: {chapter_path}\n{'='*50}\n\n{content}")
        
        return '\n'.join(contents)


if __name__ == '__main__':
    generator = SummaryGenerator()
    response = generator.chat("你好，请介绍一下你能做什么")
    print(f"\nAgent: {response}")
