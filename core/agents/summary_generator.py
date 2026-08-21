"""
SummaryGenerator Agent
职责：
- 生成人物汇总
- 生成地点汇总
- 生成剧情经历汇总
- 生成章节字数汇总
"""
from typing import Optional
from core.agents.base_agent import BaseAgent
from core.tools import get_tools_by_names
from core.project_manager import ProjectManager, NovelProject
from core.config import config_manager
from core.agent_logger import logger


# 系统提示词
SUMMARY_SYSTEM_PROMPT = """你是一个专业的小说信息汇总专家，擅长从小说内容中提取和整理各类信息。

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
    汇总说明 Agent
    负责生成小说各类信息汇总
    """
    
    def __init__(self):
        """初始化汇总说明 Agent"""
        # 获取读取所需的工具
        tools = get_tools_by_names([
            'read_file',
            'write_file',
            'glob_search',
            'list_directory',
            'ask_user'
        ])
        
        super().__init__(
            name="SummaryGenerator",
            system_prompt=SUMMARY_SYSTEM_PROMPT,
            tools=tools
        )
        
        # 项目管理器
        self.project_manager = ProjectManager(config_manager.get_output_dir())
        
        # 当前项目
        self.current_project: Optional[NovelProject] = None
        
        logger.info("汇总说明 Agent 已初始化")
    
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
    
    def get_all_chapters_content(self) -> str:
        """获取所有章节内容"""
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
    # 测试代码
    generator = SummaryGenerator()
    
    response = generator.chat("你好，请介绍一下你能做什么")
    print(f"\nAgent: {response}")
