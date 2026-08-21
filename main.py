"""
AI Agent Writer - 主入口
支持多 Agent 协作的写作智能体系统
"""
from typing import Optional
from core.agents import (
    ChatAgent, NovelWriter, OutlinePolisher,
    ContentPolisher, SummaryGenerator, InfoQuery
)
from core.workflow import WritingWorkflow
from core.project_manager import ProjectManager
from core.config import config_manager
from core.agent_logger import logger


class AgentWriter:
    """
    Agent Writer 主类
    管理多个 Agent，处理 @指令切换
    """
    
    def __init__(self):
        """初始化 Agent Writer"""
        # 创建所有 Agent
        self.agents = {
            'chat': ChatAgent(),
            'writer': NovelWriter(),
            'outline_polisher': OutlinePolisher(),
            'content_polisher': ContentPolisher(),
            'summary': SummaryGenerator(),
            'info_query': InfoQuery()
        }
        
        # 当前激活的 Agent
        self.current_agent = self.agents['chat']
        
        # 写作工作流（使用 NovelWriter）
        self.writing_workflow = WritingWorkflow(self.agents['writer'])
        
        # 项目管理器
        self.project_manager = ProjectManager(config_manager.get_output_dir())
        
        # 当前项目
        self.current_project = None
        
        logger.info("Agent Writer 已初始化")
    
    def parse_command(self, user_input: str) -> tuple:
        """
        解析用户输入，提取 @指令
        
        Returns:
            (agent_name, actual_input)
        """
        # 检查是否以 @ 开头
        if user_input.startswith('@'):
            parts = user_input.split(maxsplit=1)
            command = parts[0]
            actual_input = parts[1] if len(parts) > 1 else ""
            
            # 映射指令到 Agent
            command_map = {
                '@写作': 'writer',
                '@大纲润色': 'outline_polisher',
                '@小说润色': 'content_polisher',
                '@汇总说明': 'summary',
                '@信息查询': 'info_query'
            }
            
            if command in command_map:
                return command_map[command], actual_input
        
        # 默认使用 ChatAgent
        return 'chat', user_input
    
    def switch_agent(self, agent_name: str) -> None:
        """切换 Agent"""
        if agent_name in self.agents:
            self.current_agent = self.agents[agent_name]
            logger.info(f"已切换到 Agent: {agent_name}")
    
    def set_project(self, project_name: str) -> bool:
        """设置当前项目"""
        project = self.project_manager.load_project(project_name)
        if project:
            self.current_project = project
            # 同步到所有需要项目的 Agent
            for agent_name in ['writer', 'outline_polisher', 'content_polisher', 
                             'summary', 'info_query']:
                self.agents[agent_name].set_project(project_name)
            logger.info(f"已设置项目: {project_name}")
            return True
        return False
    
    def chat(self, user_input: str) -> str:
        """
        处理用户输入并返回 Agent 回复
        
        Args:
            user_input: 用户输入
        
        Returns:
            Agent 回复内容
        """
        # 解析指令
        agent_name, actual_input = self.parse_command(user_input)
        
        # 切换 Agent
        self.switch_agent(agent_name)
        
        # 特殊处理：写作工作流
        if agent_name == 'writer' and actual_input.startswith('第'):
            # 解析章节信息（简化版）
            # 例如："@写作 第1卷 第1章" 或 "@写作 第1章"
            try:
                # 这里简化处理，实际可以更复杂
                if '卷' in actual_input:
                    # 解析卷和章
                    parts = actual_input.replace('第', '').replace('卷', ' ').replace('章', ' ').split()
                    volume = int(parts[0])
                    chapter = int(parts[1])
                else:
                    # 只有章
                    chapter = int(actual_input.replace('第', '').replace('章', ''))
                    volume = 1
                
                # 执行写作工作流
                result = self.writing_workflow.write_chapter(volume, chapter)
                
                if result['success']:
                    return f"✓ 第{volume}卷第{chapter}章写作完成\n\n{result['chapter_content'][:500]}..."
                else:
                    return f"✗ 写作失败\n\n大纲审查: {result['outline_review']['feedback']}\n\n逻辑审查: {result['logic_review']['feedback']}"
            except Exception as e:
                logger.error(f"写作工作流错误: {e}")
                return f"写作失败: {str(e)}"
        
        # 普通对话
        if actual_input:
            result = self.current_agent.chat(actual_input)
            return result['response']
        else:
            return f"已切换到 {agent_name} Agent，请输入具体内容。"
    
    def clear_history(self) -> None:
        """清空当前 Agent 的对话历史"""
        self.current_agent.clear_history()
        logger.info("对话历史已清空")


def main():
    """主函数"""
    import sys
    
    # 检查是否启动 Web 模式
    if '--web' in sys.argv or '-w' in sys.argv:
        from web.app import run_web_server
        run_web_server(debug=True)
        return
    
    print("\n" + "=" * 60)
    print("欢迎使用 AI Agent Writer！")
    print("=" * 60)
    print("\n启动模式：")
    print("  python main.py        - 命令行模式")
    print("  python main.py --web  - Web 界面模式")
    print("\n可用指令：")
    print("  @写作      - 执行写作工作流（如：@写作 第1卷 第1章）")
    print("  @大纲润色  - 优化大纲结构和设定")
    print("  @小说润色  - 润色章节内容")
    print("  @汇总说明  - 生成人物、地点等汇总信息")
    print("  @信息查询  - 查询小说内外的信息")
    print("  无指令     - 自由对话（默认）")
    print("\n其他命令：")
    print("  /project <名称>  - 切换项目")
    print("  /clear           - 清空对话历史")
    print("  /quit            - 退出程序")
    print("=" * 60 + "\n")
    
    # 创建 Agent Writer
    writer = AgentWriter()
    
    # 列出可用项目
    projects = writer.project_manager.list_projects()
    if projects:
        print(f"可用项目: {', '.join(projects)}")
        print("提示：使用 /project <名称> 切换项目\n")
    
    while True:
        try:
            user_input = input("\n请输入: ").strip()
            
            if not user_input:
                continue
            
            # 处理特殊命令
            if user_input.lower() in ('quit', 'exit', 'q', '/quit','拜拜','再见'):
                print("再见！")
                break
            
            if user_input.startswith('/project '):
                project_name = user_input[9:].strip()
                if writer.set_project(project_name):
                    print(f"✓ 已切换到项目: {project_name}")
                else:
                    print(f"✗ 项目不存在: {project_name}")
                continue
            
            if user_input == '/clear':
                writer.clear_history()
                print("✓ 对话历史已清空")
                continue
            
            # 普通对话
            result = writer.chat(user_input)
            print(f"\nAgent: {result['response']}")
            
        except KeyboardInterrupt:
            print("\n再见！")
            break
        except Exception as e:
            logger.error(f"运行出错: {str(e)}")
            print(f"\n出错了: {str(e)}")


if __name__ == "__main__":
    main()
