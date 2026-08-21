"""
Web 应用主入口
职责：
- 提供 Web 服务
- 处理 API 请求
- 管理会话状态
"""
import os
import json
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from core.agents import (
    ChatAgent, NovelWriter, OutlinePolisher,
    ContentPolisher, SummaryGenerator, InfoQuery
)
from core.workflow import WritingWorkflow
from core.project_manager import ProjectManager
from core.config import config_manager
from core.agent_logger import logger


# 创建 Flask 应用
app = Flask(__name__, 
            template_folder=os.path.dirname(os.path.abspath(__file__)),
            static_folder=os.path.dirname(os.path.abspath(__file__)))
CORS(app)  # 允许跨域请求


# 全局 Agent Writer 实例
class AgentWriter:
    """Agent Writer 主类（Web 版本）"""
    
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
        self.current_agent_name = 'chat'
        
        # 写作工作流
        self.writing_workflow = WritingWorkflow(self.agents['writer'])
        
        # 项目管理器
        self.project_manager = ProjectManager(config_manager.get_output_dir())
        
        # 当前项目
        self.current_project = None
        self.current_project_name = None
        
        logger.info("Web Agent Writer 已初始化")
    
    def parse_command(self, user_input: str) -> tuple:
        """解析用户输入，提取 @指令"""
        if user_input.startswith('@'):
            parts = user_input.split(maxsplit=1)
            command = parts[0]
            actual_input = parts[1] if len(parts) > 1 else ""
            
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
            self.current_agent_name = agent_name
            logger.info(f"已切换到 Agent: {agent_name}")
    
    def set_project(self, project_name: str) -> bool:
        """设置当前项目"""
        project = self.project_manager.load_project(project_name)
        if project:
            self.current_project = project
            self.current_project_name = project_name
            # 同步到所有需要项目的 Agent
            for agent_name in ['writer', 'outline_polisher', 'content_polisher', 
                             'summary', 'info_query']:
                self.agents[agent_name].set_project(project_name)
            logger.info(f"已设置项目: {project_name}")
            return True
        return False
    
    def chat(self, user_input: str) -> dict:
        """处理用户输入并返回 Agent 回复"""
        # 解析指令
        agent_name, actual_input = self.parse_command(user_input)
        
        # 切换 Agent
        self.switch_agent(agent_name)
        
        # 特殊处理：写作工作流
        if agent_name == 'writer' and actual_input.startswith('第'):
            try:
                if '卷' in actual_input:
                    parts = actual_input.replace('第', '').replace('卷', ' ').replace('章', ' ').split()
                    volume = int(parts[0])
                    chapter = int(parts[1])
                else:
                    chapter = int(actual_input.replace('第', '').replace('章', ''))
                    volume = 1
                
                result = self.writing_workflow.write_chapter(volume, chapter)
                
                if result['success']:
                    return {
                        'response': f"✓ 第{volume}卷第{chapter}章写作完成\n\n{result['chapter_content'][:500]}...",
                        'agent': agent_name,
                        'workflow': True
                    }
                else:
                    return {
                        'response': f"✗ 写作失败\n\n大纲审查: {result['outline_review']['feedback']}\n\n逻辑审查: {result['logic_review']['feedback']}",
                        'agent': agent_name,
                        'workflow': True
                    }
            except Exception as e:
                logger.error(f"写作工作流错误: {e}")
                return {
                    'response': f"写作失败: {str(e)}",
                    'agent': agent_name,
                    'workflow': True
                }
        
        # 普通对话
        if actual_input:
            response = self.current_agent.chat(actual_input)
            return {
                'response': response,
                'agent': agent_name,
                'workflow': False
            }
        else:
            return {
                'response': f"已切换到 {agent_name} Agent，请输入具体内容。",
                'agent': agent_name,
                'workflow': False
            }


# 全局实例
agent_writer = AgentWriter()


# ==================== 路由 ====================

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """对话 API"""
    try:
        data = request.json
        user_input = data.get('message', '')
        
        if not user_input:
            return jsonify({'error': '消息不能为空'}), 400
        
        result = agent_writer.chat(user_input)
        
        return jsonify({
            'success': True,
            'data': result
        })
    
    except Exception as e:
        logger.error(f"对话 API 错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects', methods=['GET'])
def api_list_projects():
    """列出所有项目"""
    try:
        projects = agent_writer.project_manager.list_projects()
        return jsonify({
            'success': True,
            'data': {
                'projects': projects,
                'current': agent_writer.current_project_name
            }
        })
    except Exception as e:
        logger.error(f"列出项目错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects', methods=['POST'])
def api_create_project():
    """创建新项目（自动用模板初始化大纲）"""
    try:
        data = request.json
        project_name = data.get('name', '').strip()
        
        if not project_name:
            return jsonify({'error': '项目名称不能为空'}), 400
        
        # 创建项目
        project = agent_writer.project_manager.create_project(project_name)
        
        # 用模板初始化大纲
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'output', 'outline_template.md'
        )
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            project.write_outline(template_content)
        
        # 设置为当前项目
        agent_writer.set_project(project_name)
        
        return jsonify({
            'success': True,
            'data': {
                'name': project_name,
                'message': f'项目 {project_name} 已创建（大纲已用模板初始化）'
            }
        })
    
    except Exception as e:
        logger.error(f"创建项目错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/import', methods=['POST'])
def api_import_project():
    """导入项目（上传 .md 文件作为大纲）"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '未找到上传文件'}), 400
        
        file = request.files['file']
        if file.filename == '' or not file.filename.endswith('.md'):
            return jsonify({'error': '请上传 .md 文件'}), 400
        
        # 文件名（去掉扩展名）作为项目名
        project_name = os.path.splitext(file.filename)[0]
        
        # 创建项目
        project = agent_writer.project_manager.create_project(project_name)
        
        # 写入上传的文件内容作为大纲
        content = file.read().decode('utf-8')
        project.write_outline(content)
        
        # 设置为当前项目
        agent_writer.set_project(project_name)
        
        return jsonify({
            'success': True,
            'data': {
                'name': project_name,
                'message': f'项目 {project_name} 已导入'
            }
        })
    
    except Exception as e:
        logger.error(f"导入项目错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<project_name>/switch', methods=['POST'])
def api_switch_project(project_name):
    """切换项目"""
    try:
        if agent_writer.set_project(project_name):
            return jsonify({
                'success': True,
                'data': {
                    'name': project_name,
                    'message': f'已切换到项目: {project_name}'
                }
            })
        else:
            return jsonify({'error': f'项目不存在: {project_name}'}), 404
    
    except Exception as e:
        logger.error(f"切换项目错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<project_name>/outline', methods=['GET'])
def api_get_outline(project_name):
    """获取大纲内容"""
    try:
        project = agent_writer.project_manager.load_project(project_name)
        if not project:
            return jsonify({'error': f'项目不存在: {project_name}'}), 404
        
        outline = project.read_outline()
        
        return jsonify({
            'success': True,
            'data': {
                'outline': outline
            }
        })
    
    except Exception as e:
        logger.error(f"获取大纲错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<project_name>/outline', methods=['PUT'])
def api_save_outline(project_name):
    """保存大纲内容"""
    try:
        project = agent_writer.project_manager.load_project(project_name)
        if not project:
            return jsonify({'error': f'项目不存在: {project_name}'}), 404
        
        data = request.json
        content = data.get('content', '')
        
        # 写入大纲文件
        project.write_outline(content)
        
        logger.info(f"大纲已保存: {project_name}")
        
        return jsonify({
            'success': True,
            'data': {'message': '大纲已保存'}
        })
    
    except Exception as e:
        logger.error(f"保存大纲错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<project_name>/chapters', methods=['GET'])
def api_list_chapters(project_name):
    """列出所有章节"""
    try:
        project = agent_writer.project_manager.load_project(project_name)
        if not project:
            return jsonify({'error': f'项目不存在: {project_name}'}), 404
        
        chapters = project.list_chapters()
        
        return jsonify({
            'success': True,
            'data': {
                'chapters': chapters
            }
        })
    
    except Exception as e:
        logger.error(f"列出章节错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/agent/current', methods=['GET'])
def api_get_current_agent():
    """获取当前 Agent"""
    try:
        return jsonify({
            'success': True,
            'data': {
                'agent': agent_writer.current_agent_name
            }
        })
    except Exception as e:
        logger.error(f"获取当前 Agent 错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<project_name>/chapter-tree', methods=['GET'])
def api_chapter_tree(project_name):
    """获取章节目录树（按卷分组）"""
    try:
        project = agent_writer.project_manager.load_project(project_name)
        if not project:
            return jsonify({'error': f'项目不存在: {project_name}'}), 404
        
        chapters_dir = project.chapters_dir
        tree = []
        
        if os.path.exists(chapters_dir):
            for vol_dir in sorted(os.listdir(chapters_dir)):
                vol_path = os.path.join(chapters_dir, vol_dir)
                if os.path.isdir(vol_path) and vol_dir.startswith('vol'):
                    vol_name = vol_dir.replace('vol', '第') + '卷'
                    chapters = []
                    for ch_file in sorted(os.listdir(vol_path)):
                        if ch_file.endswith('.md'):
                            # 读取文件前100字作为预览
                            ch_path = os.path.join(vol_path, ch_file)
                            preview = ''
                            try:
                                with open(ch_path, 'r', encoding='utf-8') as f:
                                    preview = f.read(100)
                            except Exception:
                                pass
                            chapters.append({
                                'file': f"{vol_dir}/{ch_file}",
                                'name': ch_file.replace('.md', ''),
                                'preview': preview
                            })
                    tree.append({
                        'volume': vol_name,
                        'vol_dir': vol_dir,
                        'chapters': chapters
                    })
        
        return jsonify({
            'success': True,
            'data': {'tree': tree}
        })
    except Exception as e:
        logger.error(f"获取章节目录树错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<project_name>/chapter', methods=['GET'])
def api_read_chapter(project_name):
    """读取指定章节内容"""
    try:
        file_path = request.args.get('file', '')
        if not file_path:
            return jsonify({'error': '缺少 file 参数'}), 400
        
        project = agent_writer.project_manager.load_project(project_name)
        if not project:
            return jsonify({'error': f'项目不存在: {project_name}'}), 404
        
        full_path = os.path.join(project.chapters_dir, file_path)
        if not os.path.exists(full_path):
            return jsonify({'error': '章节文件不存在'}), 404
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'success': True,
            'data': {
                'file': file_path,
                'content': content
            }
        })
    except Exception as e:
        logger.error(f"读取章节错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<project_name>/chapter', methods=['PUT'])
def api_save_chapter(project_name):
    """保存章节内容"""
    try:
        data = request.json
        file_path = data.get('file', '')
        content = data.get('content', '')
        
        if not file_path:
            return jsonify({'error': '缺少 file 参数'}), 400
        
        project = agent_writer.project_manager.load_project(project_name)
        if not project:
            return jsonify({'error': f'项目不存在: {project_name}'}), 404
        
        full_path = os.path.join(project.chapters_dir, file_path)
        if not os.path.exists(full_path):
            return jsonify({'error': '章节文件不存在'}), 404
        
        # 写入章节文件
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"章节已保存: {project_name}/{file_path}")
        
        return jsonify({
            'success': True,
            'data': {'message': '章节已保存'}
        })
    except Exception as e:
        logger.error(f"保存章节错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    """获取当前 LLM 配置"""
    try:
        cfg = config_manager.get_llm_config()
        # 隐藏 API Key 中间部分
        api_key = cfg.get('api_key', '')
        if len(api_key) > 8:
            masked_key = api_key[:4] + '****' + api_key[-4:]
        else:
            masked_key = api_key
        
        return jsonify({
            'success': True,
            'data': {
                'base_url': cfg.get('base_url', ''),
                'model': cfg.get('model', ''),
                'api_key_masked': masked_key,
                'temperature': cfg.get('temperature', 0.7)
            }
        })
    except Exception as e:
        logger.error(f"获取设置错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings', methods=['POST'])
def api_update_settings():
    """更新 LLM 配置"""
    try:
        data = request.json
        base_url = data.get('base_url')
        model = data.get('model')
        temperature = data.get('temperature')
        api_key = data.get('api_key')
        
        # 更新配置文件中的字段
        config_manager.update_llm_config(
            base_url=base_url,
            model=model,
            temperature=temperature
        )
        
        # 如果提供了 API Key，设置环境变量
        if api_key:
            os.environ['LLM_API_KEY'] = api_key
        
        return jsonify({
            'success': True,
            'data': {'message': '设置已保存'}
        })
    except Exception as e:
        logger.error(f"更新设置错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/test', methods=['POST'])
def api_test_connection():
    """测试 LLM 连接"""
    try:
        data = request.json
        base_url = data.get('base_url', '')
        model = data.get('model', '')
        api_key = data.get('api_key', '')
        
        # 如果 api_key 是掩码值（包含 ****），从环境变量获取真实 key
        if '****' in api_key:
            api_key = os.environ.get('LLM_API_KEY', '')
        
        from langchain_openai import ChatOpenAI
        
        # 临时构建 LLM 测试连接
        llm = ChatOpenAI(
            base_url=base_url,
            model=model,
            api_key=api_key or 'test',
            temperature=0.1
        )
        response = llm.invoke('你好，请回复"连接成功"')
        
        return jsonify({
            'success': True,
            'data': {
                'message': '连接成功',
                'response': response.content[:100]
            }
        })
    except Exception as e:
        logger.error(f"测试连接错误: {e}")
        return jsonify({
            'success': False,
            'error': f'连接失败: {str(e)}'
        }), 200


# ==================== 启动 ====================

def run_web_server(host='127.0.0.1', port=5000, debug=False):
    """启动 Web 服务器"""
    logger.info(f"启动 Web 服务器: http://{host}:{port}")
    
    # 自动打开浏览器
    import webbrowser
    webbrowser.open(f'http://{host}:{port}')
    
    # 启动 Flask
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_web_server(debug=True)
