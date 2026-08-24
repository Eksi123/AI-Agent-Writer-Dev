"""
Web 应用主入口

提供 Flask Web 服务和 REST API，管理项目、章节、对话和设置。
前端通过 /api/* 接口与 AgentWriter 交互。
"""
import os
import json
import shutil
import zipfile
import tempfile
import webbrowser
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from langchain_openai import ChatOpenAI
from core.agents import (
    ChatAgent, NovelWriter, OutlinePolisher,
    ContentPolisher, SummaryGenerator, InfoQuery
)
from core.workflow import WritingWorkflow
from core.project_manager import ProjectManager
from core.config_manager import config_manager
from core.agent_logger import logger


app = Flask(__name__, 
            template_folder=os.path.dirname(os.path.abspath(__file__)),
            static_folder=os.path.dirname(os.path.abspath(__file__)))
CORS(app)


class AgentWriter:
    """
    Agent Writer 主类（Web 版本）
    
    与 main.py 中的 AgentWriter 功能相同，但增加了自动加载项目和
    返回结构化数据供前端渲染。
    """
    
    def __init__(self):
        """初始化所有 Agent、写作工作流和项目管理器，并自动加载第一个项目"""
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
        self.current_agent_name = 'chat'
        
        self.writing_workflow = WritingWorkflow(self.agents['writer'])
        self.project_manager = ProjectManager(config_manager.get_output_dir())
        self.current_project = None
        self.current_project_name = None
        
        # Web 版特有：自动加载第一个存在的项目
        self._auto_load_project()
        
        logger.info("Web Agent Writer 已初始化")
    
    def _auto_load_project(self) -> None:
        """Web 版特有：自动加载第一个存在的项目，方便用户打开即用"""
        try:
            projects = self.project_manager.list_projects()
            if projects:
                self.set_project(projects[0])
                logger.info(f"已自动加载项目: {projects[0]}")
        except Exception as e:
            logger.warning(f"自动加载项目失败: {e}")
    
    def parse_command(self, user_input: str) -> tuple:
        """解析用户输入，提取 @指令并映射到对应的 Agent。
        
        Returns:
            (agent_name, actual_input) - Agent 名称和实际输入内容
        """
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
        """切换当前激活的 Agent"""
        if agent_name in self.agents:
            self.current_agent = self.agents[agent_name]
            self.current_agent_name = agent_name
            logger.info(f"已切换到 Agent: {agent_name}")
    
    def set_project(self, project_name: str) -> bool:
        """设置当前项目，同步到所有需要项目上下文的 Agent"""
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
        """
        处理用户输入并返回 Agent 回复。
        
        流程：
        1. 解析 @指令，切换到对应 Agent
        2. 特殊处理：@写作 + 章节号 → 执行写作工作流
        3. 普通对话：调用当前 Agent 的 chat 方法
        
        Returns:
            包含 response、agent、workflow、error 等字段的字典
        """
        agent_name, actual_input = self.parse_command(user_input)
        self.switch_agent(agent_name)
        
        # 特殊处理：@写作 + 章节信息 → 执行写作工作流
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
        
        # 普通对话：调用当前 Agent
        if actual_input:
            result = self.current_agent.chat(actual_input)
            response_data = {
                'response': result['response'],
                'thought_process': result['thought_process'],
                'agent': agent_name,
                'workflow': False
            }
            # 将错误标志传递给前端，用于 UI 错误提示
            if result.get('error'):
                response_data['error'] = True
            return response_data
        else:
            return {
                'response': f'已切换到 {agent_name} Agent，请输入具体内容。',
                'thought_process': [],
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
    """对话 API - 接收用户输入，返回 Agent 回复"""
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
        error_msg = str(e)
        logger.error(f"对话 API 错误: {error_msg}")
        
        # 根据错误类型生成友好的中文提示信息
        if 'authentication' in error_msg.lower() or 'api key' in error_msg.lower() or '401' in error_msg:
            hint = '❌ **API Key 无效或已过期**\n\n请检查设置中的 API Key 是否正确，或重新设置环境变量 LLM_API_KEY'
        elif 'connect' in error_msg.lower() or 'refused' in error_msg.lower() or 'timeout' in error_msg.lower():
            hint = '❌ **无法连接到模型服务**\n\n请检查 API 地址是否正确；如使用 Ollama 请确认服务已启动'
        elif 'model' in error_msg.lower() or 'not found' in error_msg.lower() or '404' in error_msg:
            hint = '❌ **模型不可用**\n\n模型名称不正确或服务未提供该模型，请检查模型名称'
        elif 'rate limit' in error_msg.lower() or '429' in error_msg:
            hint = '❌ **请求频率超限**\n\n请稍后再试，或联系服务提供商提升限额'
        else:
            hint = f'❌ **模型调用失败**\n\n{error_msg[:300]}'
        
        # 返回 200 状态码（而非 500），让前端正确解析 error 字段
        return jsonify({
            'success': False,
            'error': hint
        }), 200


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
    """创建新项目，自动用模板初始化大纲"""
    try:
        data = request.json
        project_name = data.get('name', '').strip()
        
        if not project_name:
            return jsonify({'error': '项目名称不能为空'}), 400
        
        project = agent_writer.project_manager.create_project(project_name)
        
        # 用模板初始化大纲（将模板中的"小说名称"替换为实际名称）
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'output', 'outline_template.md'
        )
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            # 将模板中的"小说名称"替换为实际的小说名
            template_content = template_content.replace('# 小说名称', f'# {project_name}')
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
    """导入项目 - 上传 .md 文件作为大纲"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '未找到上传文件'}), 400
        
        file = request.files['file']
        if file.filename == '' or not file.filename.endswith('.md'):
            return jsonify({'error': '请上传 .md 文件'}), 400
        
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


@app.route('/api/projects/<project_name>', methods=['DELETE'])
def api_delete_project(project_name):
    """删除项目"""
    try:
        project_dir = os.path.join(agent_writer.project_manager.base_dir, project_name)
        
        if not os.path.exists(project_dir):
            return jsonify({'error': f'项目不存在: {project_name}'}), 404
        
        # 删除整个项目目录
        shutil.rmtree(project_dir)
        
        logger.info(f"已删除项目: {project_name}")
        
        return jsonify({
            'success': True,
            'data': {
                'message': f'项目 {project_name} 已删除'
            }
        })
    
    except Exception as e:
        logger.error(f"删除项目错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<project_name>/export', methods=['GET'])
def api_export_project(project_name):
    """导出整个项目目录为ZIP"""
    try:
        project = agent_writer.project_manager.load_project(project_name)
        if not project:
            return jsonify({'error': f'项目不存在: {project_name}'}), 404
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        temp_file.close()
        
        # 打包整个项目目录为 ZIP
        with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(project.base_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, project.base_dir)
                    zipf.write(file_path, arcname)
        
        # 返回ZIP文件
        return send_file(
            temp_file.name,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{project_name}.zip'
        )
    
    except Exception as e:
        logger.error(f"导出项目错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<project_name>/outline', methods=['GET'])
def api_get_outline(project_name):
    """获取项目大纲内容"""
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
    """获取章节目录树，按卷分组，包含每个章节的前100字预览"""
    try:
        project = agent_writer.project_manager.load_project(project_name)
        if not project:
            return jsonify({'error': f'项目不存在: {project_name}'}), 404
        
        # 使用新的 get_chapter_tree 方法
        tree = project.get_chapter_tree()
        
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


@app.route('/api/projects/<project_name>/volume', methods=['POST'])
def api_create_volume(project_name):
    """创建新卷（支持自定义卷序号）"""
    try:
        data = request.json
        vol_name = data.get('name', '').strip()
        volume = data.get('volume')
        if volume is not None:
            volume = int(volume)
        
        project = agent_writer.project_manager.load_project(project_name)
        if not project:
            return jsonify({'error': f'项目不存在: {project_name}'}), 404
        
        vol_num = project.create_volume(vol_name, volume)
        
        return jsonify({
            'success': True,
            'data': {
                'volume': vol_num,
                'message': f'卷 {vol_num} 已创建'
            }
        })
    except ValueError as e:
        # 命名规则校验失败
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"创建卷错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<project_name>/volume/<int:volume>', methods=['DELETE'])
def api_delete_volume(project_name, volume):
    """删除指定卷及其所有章节"""
    try:
        project = agent_writer.project_manager.load_project(project_name)
        if not project:
            return jsonify({'error': f'项目不存在: {project_name}'}), 404
        
        if project.delete_volume(volume):
            return jsonify({
                'success': True,
                'data': {'message': f'卷 {volume} 已删除'}
            })
        else:
            return jsonify({'error': f'卷 {volume} 不存在'}), 404
    except Exception as e:
        logger.error(f"删除卷错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<project_name>/volume/<int:volume>', methods=['PUT'])
def api_rename_volume(project_name, volume):
    """重命名卷"""
    try:
        data = request.json
        new_name = data.get('name', '').strip()
        
        if not new_name:
            return jsonify({'error': '卷名不能为空'}), 400
        
        project = agent_writer.project_manager.load_project(project_name)
        if not project:
            return jsonify({'error': f'项目不存在: {project_name}'}), 404
        
        if project.rename_volume(volume, new_name):
            return jsonify({
                'success': True,
                'data': {'message': f'卷 {volume} 已重命名为 {new_name}'}
            })
        else:
            return jsonify({'error': f'卷 {volume} 不存在'}), 404
    except ValueError as e:
        # 命名规则校验失败
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"重命名卷错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<project_name>/chapter/create', methods=['POST'])
def api_create_chapter(project_name):
    """创建新章节（支持自定义章节序号）"""
    try:
        data = request.json
        volume = data.get('volume')
        chapter_name = data.get('name', '').strip()
        chapter = data.get('chapter')
        if chapter is not None:
            chapter = int(chapter)
        
        if volume is None:
            return jsonify({'error': '缺少 volume 参数'}), 400
        
        project = agent_writer.project_manager.load_project(project_name)
        if not project:
            return jsonify({'error': f'项目不存在: {project_name}'}), 404
        
        ch_num = project.create_chapter(volume, chapter_name, chapter)
        
        return jsonify({
            'success': True,
            'data': {
                'volume': volume,
                'chapter': ch_num,
                'message': f'章节 {volume}_{ch_num} 已创建'
            }
        })
    except ValueError as e:
        # 命名规则校验失败
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"创建章节错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<project_name>/chapter/<int:volume>/<int:chapter>', methods=['DELETE'])
def api_delete_chapter(project_name, volume, chapter):
    """删除指定章节"""
    try:
        project = agent_writer.project_manager.load_project(project_name)
        if not project:
            return jsonify({'error': f'项目不存在: {project_name}'}), 404
        
        if project.delete_chapter(volume, chapter):
            return jsonify({
                'success': True,
                'data': {'message': f'章节 {volume}_{chapter} 已删除'}
            })
        else:
            return jsonify({'error': f'章节 {volume}_{chapter} 不存在'}), 404
    except Exception as e:
        logger.error(f"删除章节错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<project_name>/chapter/<int:volume>/<int:chapter>', methods=['PUT'])
def api_rename_chapter(project_name, volume, chapter):
    """重命名章节"""
    try:
        data = request.json
        new_name = data.get('name', '').strip()
        
        if not new_name:
            return jsonify({'error': '章节名不能为空'}), 400
        
        project = agent_writer.project_manager.load_project(project_name)
        if not project:
            return jsonify({'error': f'项目不存在: {project_name}'}), 404
        
        if project.rename_chapter(volume, chapter, new_name):
            return jsonify({
                'success': True,
                'data': {'message': f'章节 {volume}_{chapter} 已重命名为 {new_name}'}
            })
        else:
            return jsonify({'error': f'章节 {volume}_{chapter} 不存在'}), 404
    except ValueError as e:
        # 命名规则校验失败
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"重命名章节错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    """获取当前 LLM 配置（API Key 中间部分掩码处理）"""
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
                'api_url': cfg.get('api_url', ''),
                'model_name': cfg.get('model_name', ''),
                'provider': cfg.get('provider', 'openai_compatible'),
                'api_key_masked': masked_key,
                'temperature': cfg.get('temperature', 0.7),
                'top_p': cfg.get('top_p', 0.9)
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
        api_url = data.get('api_url')
        model_name = data.get('model_name')
        provider = data.get('provider')
        temperature = data.get('temperature')
        top_p = data.get('top_p')
        api_key = data.get('api_key')
        
        # 更新配置文件中的字段
        config_manager.update_llm_config(
            api_url=api_url,
            model_name=model_name,
            provider=provider,
            temperature=temperature,
            top_p=top_p
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


@app.route('/api/llm/ollama/models', methods=['GET'])
def api_get_ollama_models():
    """获取 Ollama 本地可用模型列表（通过 localhost:11434 查询）"""
    try:
        import requests as http_requests
        response = http_requests.get('http://localhost:11434/api/tags', timeout=5)
        if response.ok:
            models = response.json().get('models', [])
            return jsonify({
                'success': True,
                'data': {
                    'models': [m['name'] for m in models]
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Ollama 服务未运行'
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'无法连接 Ollama: {str(e)}'
        }), 200


@app.route('/api/settings/test', methods=['POST'])
def api_test_connection():
    """
    测试 LLM 连接
    
    根据前端表单当前填写的值进行测试：
    - 本地模型 (Ollama)：不需要 API Key
    - 在线模型：需要 API Key
      - 如果用户修改了 Key（前端会标记 use_input_key=true），直接使用输入框的值
      - 如果用户未修改 Key（前端传来掩码值），回退到环境变量中的真实 Key
    """
    try:
        data = request.json
        api_url = data.get('api_url', '')
        model_name = data.get('model_name', '')
        api_key = data.get('api_key', '')
        provider = data.get('provider', '')
        use_input_key = data.get('use_input_key', False)  # 前端标记：用户是否修改了Key

        is_local = (provider == 'ollama')

        if is_local:
            # Ollama 不需要真实 API Key，ChatOpenAI 要求非空，用占位符
            api_key = 'ollama'
        else:
            if use_input_key:
                # 用户修改了 API Key，直接使用输入框的值（即使是掩码也会用它测试，会报错）
                pass
            else:
                # 用户未修改 Key，回退到环境变量中的真实 Key
                api_key = os.environ.get('LLM_API_KEY', '')
            
            if not api_key:
                return jsonify({
                    'success': False,
                    'error': 'API Key 不能为空。请在输入框中填写新的 API Key（先点击"保存设置"使其生效），或设置环境变量 LLM_API_KEY'
                }), 200

        llm = ChatOpenAI(
            base_url=api_url,
            model=model_name,
            api_key=api_key,
            temperature=0.1,
            timeout=15
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
        error_msg = str(e)
        logger.error(f"测试连接错误: {error_msg}")
        # 根据错误类型提供更详细的提示信息
        if 'authentication' in error_msg.lower() or 'api key' in error_msg.lower() or '401' in error_msg:
            hint = 'API Key 无效或未设置。请检查密钥是否正确，或设置环境变量 LLM_API_KEY'
        elif 'connect' in error_msg.lower() or 'refused' in error_msg.lower() or 'timeout' in error_msg.lower():
            hint = '无法连接到服务器。请检查 API 地址是否正确；如使用 Ollama 请确认服务已启动'
        elif 'model' in error_msg.lower() or 'not found' in error_msg.lower() or '404' in error_msg:
            hint = '模型名称不正确或不可用，请检查模型名称'
        else:
            hint = f'连接失败: {error_msg[:200]}'
        return jsonify({
            'success': False,
            'error': hint
        }), 200


# ==================== 启动 ====================

def run_web_server(host='127.0.0.1', port=None, debug=False):
    """
    启动 Web 服务器
    
    流程：
    1. 从配置文件读取端口和 auto_open_browser 设置
    2. 如果 auto_open_browser=true，自动打开浏览器
    3. 启动 Flask 应用
    """
    server_config = config_manager.get_server_config()
    if port is None:
        port = server_config.get('port', 8000)
    auto_open_browser = server_config.get('auto_open_browser', True)
    
    logger.info(f"启动 Web 服务器: http://{host}:{port}")
    
    if auto_open_browser:
        webbrowser.open(f'http://{host}:{port}')
    
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_web_server(debug=True)
