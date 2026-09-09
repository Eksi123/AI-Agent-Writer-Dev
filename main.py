"""
AI Agent Writer - 主入口

支持多 Agent 协作的写作智能体系统，提供命令行和 Web 两种启动模式。
启动流程：检查命令行参数 → 检查配置文件的 auto_open_browser → 命令行模式
"""
import sys
from typing import Optional
from core.agents import (
    ChatAgent, NovelWriter, OutlinePolisher,
    ContentPolisher, SummaryGenerator, InfoQuery
)
from core.workflow import WritingWorkflow
from core.project_manager import ProjectManager
from core.config_manager import config_manager
from core.agent_logger import logger
from web.app import run_web_server


class AgentWriter:
    """
    Agent Writer 主类，管理多个 Agent 并通过 @指令切换。
    
    支持的指令：
    - @写作：执行写作工作流（NovelWriter + WritingWorkflow）
    - @大纲润色：优化大纲（OutlinePolisher）
    - @小说润色：润色章节（ContentPolisher）
    - @汇总说明：生成汇总信息（SummaryGenerator）
    - @信息查询：查询信息（InfoQuery）
    - 无指令：自由对话（ChatAgent）
    """
    
    def __init__(self):
        """初始化所有 Agent、写作工作流和项目管理器"""
        self.agents = {
            'chat': ChatAgent(),
            'writer': NovelWriter(),
            'outline_polisher': OutlinePolisher(),
            'content_polisher': ContentPolisher(),
            'summary': SummaryGenerator(),
            'info_query': InfoQuery()
        }
        
        # 默认使用自由对话 Agent
        self.current_agent = self.agents['chat']
        
        self.writing_workflow = WritingWorkflow(self.agents['writer'])
        self.project_manager = ProjectManager(config_manager.get_output_dir())
        self.current_project = None
        
        logger.info("Agent Writer 已初始化")
    
    def parse_command(self, user_input: str) -> tuple:
        """
        解析用户输入，提取 @指令并映射到对应的 Agent。
        
        Returns:
            (agent_name, actual_input) - Agent 名称和实际输入内容
        """
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
        
        return 'chat', user_input
    
    def switch_agent(self, agent_name: str) -> None:
        """切换 Agent"""
        if agent_name in self.agents:
            self.current_agent = self.agents[agent_name]
            logger.info(f"已切换到 Agent: {agent_name}")
    
    def set_project(self, project_name: str) -> bool:
        """设置当前项目，同步到所有需要项目上下文的 Agent，并清空历史对话"""
        project = self.project_manager.load_project(project_name)
        if project:
            self.current_project = project
            
            # 清空所有 Agent 的历史对话，避免不同项目上下文混淆
            for agent_name in self.agents:
                self.agents[agent_name].clear_history()
            logger.info("已清空所有 Agent 的历史对话")
            
            # 同步项目信息到需要项目上下文的 Agent
            for agent_name in ['writer', 'outline_polisher', 'content_polisher', 
                             'summary', 'info_query']:
                self.agents[agent_name].set_project(project_name)
            
            logger.info(f"已设置项目: {project_name}")
            return True
        return False
    
    def chat(self, user_input: str) -> str:
        """
        处理用户输入并返回 Agent 回复。
        
        流程：
        1. 解析 @指令，切换到对应 Agent
        2. 特殊处理：@写作 + 章节号 → 执行写作工作流
        3. 普通对话：调用当前 Agent 的 chat 方法
        """
        agent_name, actual_input = self.parse_command(user_input)
        self.switch_agent(agent_name)
        
        # 特殊处理：@写作 + 章节信息 → 执行写作工作流
        # 例如："@写作 第1卷 第1章" 或 "@写作 第1章"
        if agent_name == 'writer' and actual_input.startswith('第'):
            # 解析章节信息（简化版）
            # 例如："@写作 第1卷 第1章" 或 "@写作 第1章"
            try:
                # 解析章节信息：支持 "第X卷 第Y章" 和 "第Y章" 两种格式
                if '卷' in actual_input:
                    parts = actual_input.replace('第', '').replace('卷', ' ').replace('章', ' ').split()
                    volume = int(parts[0])
                    chapter = int(parts[1])
                else:
                    chapter = int(actual_input.replace('第', '').replace('章', ''))
                    volume = 1
                
                # 执行写作工作流
                result = self.writing_workflow.write_chapter(volume, chapter)
                
                if result['success']:
                    return f"✓ 第{volume}卷第{chapter}章写作完成\n\n{result['chapter_content'][:500]}..."
                else:
                    pre_feedback = result.get('pre_writing_review', {}).get('feedback', '无')
                    post_feedback = result.get('post_writing_review', {}).get('feedback', '无')
                    return f"✗ 写作失败\n\n写作前审查: {pre_feedback}\n\n写作后审查: {post_feedback}"
            except Exception as e:
                logger.error(f"写作工作流错误: {e}")
                return f"写作失败: {str(e)}"
        
        # 普通对话：调用当前 Agent
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
    """主函数，根据参数和配置决定启动模式"""
    # 命令行参数 --web 或 -w：强制启动 Web 模式
    if '--web' in sys.argv or '-w' in sys.argv:
        run_web_server(debug=True)
        return
    
    # 配置文件中的 auto_open_browser = true：自动启动 Web 服务
    server_config = config_manager.get_server_config()
    if server_config.get('auto_open_browser', False):
        print("\n检测到 auto_open_browser = true，正在启动 Web 服务...")
        run_web_server(debug=True)
        return
    
    # 命令行交互模式
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
    
    writer = AgentWriter()
    
    # 列出可用项目供用户选择
    projects = writer.project_manager.list_projects()
    if projects:
        print(f"可用项目: {', '.join(projects)}")
        print("提示：使用 /project <名称> 切换项目\n")
    
    while True:
        try:
            user_input = input("\n请输入: ").strip()
            
            if not user_input:
                continue
            
            # 退出命令
            if user_input.lower() in ('quit', 'exit', 'q', '/quit','拜拜','再见'):
                print("再见！")
                break
            
            # 切换项目命令
            if user_input.startswith('/project '):
                project_name = user_input[9:].strip()
                if writer.set_project(project_name):
                    print(f"✓ 已切换到项目: {project_name}")
                else:
                    print(f"✗ 项目不存在: {project_name}")
                continue
            
            # 清空历史命令
            if user_input == '/clear':
                writer.clear_history()
                print("✓ 对话历史已清空")
                continue
            
            # 普通对话
            result = writer.chat(user_input)
            print(f"\nAgent: {result}")
            
        except KeyboardInterrupt:
            print("\n再见！")
            break
        except Exception as e:
            logger.error(f"运行出错: {str(e)}")
            print(f"\n出错了: {str(e)}")


if __name__ == "__main__":
    main()
