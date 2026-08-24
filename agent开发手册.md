# Agent-Writer 开发手册

> 面向具备 Python、LangChain、LangGraph、OpenAI、FastAPI 基础及简单 HTML 知识的新人开发者

---

## 目录

- [前言：你需要知道的一切](#前言你需要知道的一切)
- [第一部分：知识准备](#第一部分知识准备)
- [第二部分：项目架构总览](#第二部分项目架构总览)
- [第三部分：核心概念详解](#第三部分核心概念详解)
- [第四部分：分阶段开发计划](#第四部分分阶段开发计划)
- [第五部分：关键技术实现](#第五部分关键技术实现)
- [第六部分：调试与排错](#第六部分调试与排错)
- [第七部分：扩展开发指南](#第七部分扩展开发指南)

---

## 前言：你需要知道的一切

### 这个项目是什么？

Agent-Writer 是一个**AI 驱动的小说写作系统**。它不是简单的聊天机器人，而是一个能够：

1. **自主审查大纲** → 检查情节逻辑、角色行为是否合理
2. **逐章写作** → 基于大纲生成 3000-5000 字的章节正文
3. **逻辑审查** → 检查新章节与前面所有章节是否矛盾
4. **多 Agent 协作** → 不同 Agent 负责不同任务（写作、润色、查询等）

### 你已掌握的技术 vs 本项目使用的技术

| 你已掌握 | 本项目使用 | 差异说明 |
|---------|-----------|---------|
| ✅ Python | ✅ Python | 完全一致 |
| ✅ LangChain | ✅ LangChain | 完全一致，主要用于 `@tool` 装饰器 |
| ✅ LangGraph | ✅ LangGraph | **核心框架**，需要深入理解 `StateGraph` |
| ✅ OpenAI API | ✅ OpenAI API | 完全一致，但使用兼容接口支持多模型 |
| ⚠️ FastAPI | ❌ **Flask** | 本项目用 Flask，更轻量，学习成本低 |
| ✅ HTML 基础 | ✅ HTML/CSS/JS | 前端是单文件 SPA，需要了解基础 JS |

### 重要提示

**本项目不使用 FastAPI，而是使用 Flask。**

如果你熟悉 FastAPI，切换到 Flask 非常容易：

```python
# FastAPI 风格（你熟悉的）
from fastapi import FastAPI
app = FastAPI()

@app.get("/api/hello")
async def hello():
    return {"message": "Hello"}

# Flask 风格（本项目使用的）
from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({"message": "Hello"})
```

**主要区别**：
- Flask 默认同步，FastAPI 默认异步（但本项目不需要异步）
- Flask 用 `@app.route()`，FastAPI 用 `@app.get/post()`
- Flask 更简单，学习曲线更低

---

## 第一部分：知识准备

### 1.1 Flask 快速入门（预计 2-3 小时）

如果你只用过 FastAPI，需要掌握以下 Flask 基础：

#### 基础路由

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

# GET 请求
@app.route('/api/users', methods=['GET'])
def get_users():
    return jsonify({"users": ["Alice", "Bob"]})

# POST 请求
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json  # 获取 JSON 请求体
    message = data.get('message', '')
    return jsonify({"reply": f"你说的是：{message}"})
```

#### 跨域支持（CORS）

```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 允许所有来源的跨域请求
```

#### 静态文件服务

```python
@app.route('/')
def index():
    return render_template('index.html')  # 从 templates/ 目录加载
```

**学习资源**：
- Flask 官方快速入门：https://flask.palletsprojects.com/quickstart/
- 重点阅读：路由、请求对象、JSON 响应

### 1.2 LangGraph 深入理解（预计 3-4 小时）

你可能已经了解 LangGraph 的基础，但本项目需要深入理解以下概念：

#### AgentState 与 add_messages 注解

```python
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
```

**`add_messages` 的作用**：
- 当节点返回 `{"messages": [新消息]}` 时，新消息会**自动追加**到列表末尾
- 而不是覆盖整个列表
- 这样可以累积多轮对话历史

#### 条件边（Conditional Edge）

```python
graph.add_conditional_edges(
    "llm",                          # 从哪个节点出发
    self._should_continue,          # 路由函数
    {"tools": "tools", "end": END}  # 返回值 → 目标节点
)
```

**路由函数**：
```python
def _should_continue(self, state: AgentState) -> str:
    last_message = state["messages"][-1]
    
    # 如果有工具调用请求，路由到工具节点
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    
    # 否则结束
    return "end"
```

#### 完整的 Agent-Loop 图结构

```python
graph = StateGraph(AgentState)

# 添加节点
graph.add_node("llm", self._llm_node)      # 思考节点
graph.add_node("tools", self._tool_node)    # 行动节点

# 添加边
graph.add_edge(START, "llm")                # 开始 → 思考
graph.add_conditional_edges(                 # 思考后 → 根据情况路由
    "llm", 
    self._should_continue,
    {"tools": "tools", "end": END}
)
graph.add_edge("tools", "llm")              # 行动后 → 回到思考（循环）

# 编译
self.graph = graph.compile()
```

**执行流程**：
```
START → llm_node → 有工具调用? → tool_node → llm_node（循环）
                   无工具调用? → END
```

### 1.3 HTML/CSS/JS 基础（预计 2-3 小时）

本项目的前端是一个**单文件 SPA**（单页应用），所有代码都在 `web/index.html` 中。

你需要掌握：

#### JavaScript fetch API

```javascript
// 发送 POST 请求
async function sendMessage(message) {
    const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message })
    });
    
    const data = await response.json();
    
    // 渲染回复
    displayMessage(data.data.response);
}
```

#### DOM 操作

```javascript
// 获取元素
const chatBox = document.getElementById('chat-box');

// 创建并添加元素
const messageDiv = document.createElement('div');
messageDiv.className = 'message';
messageDiv.textContent = 'Hello';
chatBox.appendChild(messageDiv);
```

#### Markdown 渲染

```javascript
// 使用 marked.js 库
const markdown = "**粗体** 和 *斜体*";
const html = marked.parse(markdown);
element.innerHTML = html;
```

**学习资源**：
- MDN Web Docs：https://developer.mozilla.org/zh-CN/
- 重点：fetch API、DOM 操作、事件监听

### 1.4 开发环境搭建

```bash
# 1. 克隆项目
git clone <repo-url>
cd ai-agent-writer-dev

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 设置 API Key（环境变量）
# Windows PowerShell:
$env:LLM_API_KEY = "your-api-key"
# Linux/Mac:
export LLM_API_KEY="your-api-key"

# 6. 验证环境
python demo/demo-langgraph.py
```

**验证成功标志**：
- 看到 "Agent-Loop 开始" 等日志输出
- Agent 能够调用工具并返回结果

---

## 第二部分：项目架构总览

### 2.1 分层架构

```
┌─────────────────────────────────────────────────────┐
│                   用户界面层                          │
│  web/index.html（单文件 SPA：HTML + CSS + JS）        │
└──────────────────────┬──────────────────────────────┘
                       │ REST API (/api/*)
┌──────────────────────┼──────────────────────────────┐
│              Web 服务层 (web/app.py)                  │
│  Flask 路由 → @指令解析 → Agent 路由 → 项目管理       │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────┼──────────────────────────────┐
│              业务逻辑层                               │
│  core/workflow/          写作工作流引擎               │
│  core/agents/            Agent 定义与注册             │
│  core/project_manager.py 项目管理                    │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────┼──────────────────────────────┐
│              基础设施层                               │
│  core/agent_graph.py     LangGraph 状态图引擎         │
│  core/agent_llm.py       LLM 客户端封装              │
│  core/config_manager.py  配置管理                    │
│  core/tools/             工具注册表                  │
│  core/agent_logger.py    日志模块                    │
└─────────────────────────────────────────────────────┘
```

### 2.2 文件职责速查表

| 文件 | 职责 | 核心知识点 |
|------|------|-----------|
| `main.py` | 命令行入口 | argparse、@指令解析 |
| `web/app.py` | Flask Web 服务 | Flask 路由、REST API |
| `core/agent_graph.py` | **Agent-Loop 核心** | LangGraph StateGraph |
| `core/agents/base_agent.py` | Agent 基类 | 继承、封装 |
| `core/agents/*.py` | 具体 Agent | 系统提示词、工具绑定 |
| `core/tools/__init__.py` | 工具注册表 | importlib 动态加载 |
| `core/tools/builtin/*.py` | 内置工具 | @tool 装饰器 |
| `core/workflow/*.py` | 写作工作流 | 三阶段编排 |
| `core/project_manager.py` | 项目管理 | 文件读写、目录操作 |
| `core/config_manager.py` | 配置管理 | ConfigParser |
| `core/prompts/*.md` | 系统提示词 | Markdown 格式 |

### 2.3 数据流示例

**场景**：用户输入 `@写作 第1章`

```
用户输入 → web/app.py
         ↓
    AgentWriter.chat()
         ↓
    parse_command("@写作 第1章")
         ↓ 返回 ('writer', '第1章')
    WritingWorkflow.write_chapter(1, 1)
         ↓
    ┌─────────────────────────────────────┐
    │ Step 1: OutlineReviewer.review()    │
    │   → 读取大纲                        │
    │   → LLM 审查大纲合理性              │
    │   → 返回审查结果                    │
    └─────────────────────────────────────┘
         ↓
    ┌─────────────────────────────────────┐
    │ Step 2: NovelWriter.chat()          │
    │   → AgentGraph.invoke()             │
    │   → llm_node（思考）                │
    │   → tool_node（调用 read_file）     │
    │   → llm_node（思考）                │
    │   → tool_node（调用 write_file）    │
    │   → llm_node（任务完成）→ END       │
    └─────────────────────────────────────┘
         ↓
    ┌─────────────────────────────────────┐
    │ Step 3: LogicReviewer.review()      │
    │   → 读取所有前文章节                │
    │   → LLM 检查逻辑一致性              │
    │   → 返回审查结果                    │
    └─────────────────────────────────────┘
         ↓
    返回结果给前端
```

---

## 第三部分：核心概念详解

### 3.1 Agent-Loop（代理循环）

**这是整个项目最核心的概念。**

Agent-Loop 是 AI Agent 的运行模式：

```
思考（LLM） → 行动（工具） → 观察（结果） → 再思考 → ... → 完成
```

**类比**：就像一个人写文章
1. **思考**：我需要先看看大纲写了什么
2. **行动**：调用 `read_file` 读大纲
3. **观察**：看到大纲内容了
4. **再思考**：根据大纲开始写作
5. **行动**：调用 `write_file` 写章节
6. **最终思考**：写完了，不需要更多工具 → END

**代码实现**（`core/agent_graph.py`）：

```python
def _llm_node(self, state: AgentState) -> dict:
    """思考节点：调用 LLM 进行推理"""
    # 添加系统提示词
    system_msg = SystemMessage(content=self.system_prompt)
    messages = [system_msg] + state["messages"]
    
    # 调用 LLM
    response = self.llm_with_tools.invoke(messages)
    
    # 返回新消息（会自动追加到 state["messages"]）
    return {"messages": [response]}

def _tool_node(self, state: AgentState) -> dict:
    """行动节点：执行工具调用"""
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls
    
    results = []
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        # 执行工具
        tool_result = self.tool_map[tool_name].invoke(tool_args)
        
        # 构造 ToolMessage
        results.append(ToolMessage(
            content=tool_result,
            tool_call_id=tool_call["id"]
        ))
    
    return {"messages": results}
```

### 3.2 工具系统

工具是 Agent 与外部世界交互的接口。

**工具注册流程**：

```python
# 1. 定义工具（使用 @tool 装饰器）
from langchain_core.tools import tool

@tool
def read_file(file_path: str, start_line: int = 1, end_line: int = -1) -> str:
    """读取文件内容
    
    Args:
        file_path: 文件路径
        start_line: 起始行号
        end_line: 结束行号
    
    Returns:
        文件内容
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return content

# 2. 自动注册（core/tools/__init__.py 中的 _load_builtin_tools()）
# 扫描 builtin/ 目录，自动发现并注册所有 @tool 函数

# 3. Agent 获取工具
tools = get_tools_by_names(['read_file', 'write_file', 'edit_file'])
```

**全局注册表**：

```python
# core/tools/__init__.py
_tool_registry: Dict[str, BaseTool] = {}

def register_tool(tool: BaseTool) -> None:
    """注册工具"""
    _tool_registry[tool.name] = tool

def get_tools_by_names(names: List[str]) -> List[BaseTool]:
    """根据名称列表获取工具"""
    return [_tool_registry[name] for name in names if name in _tool_registry]
```

**热加载机制**：

```python
def reload_custom_tools() -> None:
    """重新加载自定义工具（无需重启服务）"""
    # 清空非内置工具
    custom_names = [name for name in _tool_registry if not name.startswith("builtin_")]
    for name in custom_names:
        del _tool_registry[name]
    
    # 重新扫描 custom/ 目录
    _load_custom_tools()
```

### 3.3 @指令路由

用户通过 `@指令` 切换 Agent：

```python
def parse_command(self, user_input: str) -> tuple:
    """
    解析 @指令
    
    "@写作 第1章"  →  ("writer", "第1章")
    "@大纲润色 优化结构"  →  ("outline_polisher", "优化结构")
    "今天天气不错"  →  ("chat", "今天天气不错")
    """
    if user_input.startswith('@'):
        parts = user_input.split(maxsplit=1)  # 分成两部分
        command = parts[0]                     # "@写作"
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
    
    return 'chat', user_input  # 默认自由对话
```

### 3.4 小说项目结构

每个小说项目在 `output/{小说名}/` 目录下：

```
output/
└── 霸道总裁爱上我/
    ├── outline.md                    # 大纲（所有设定 + 分卷分章概要）
    └── chapters/                     # 章节正文
        └── 第一卷-命运的邂逅/         # 第一卷（第X卷-卷名）
            ├── 第一卷_第1章_命运的邂逅.md  # 章节文件（第X卷_第Y章_章节名.md）
            └── 第一卷_第2章_无法拒绝的条件.md
```

**ProjectManager 职责**：
- `list_projects()` - 扫描 output/ 目录
- `create_project(name)` - 创建目录 + 初始化 outline.md
- `load_project(name)` - 加载项目
- `delete_project(name)` - 删除项目

**NovelProject 职责**：
- `read_outline()` - 读取大纲
- `write_outline(content)` - 写入大纲
- `read_chapter(vol, ch)` - 读取章节
- `write_chapter(vol, ch, content)` - 写入章节
- `list_chapters()` - 列出所有章节
- `create_volume(vol_name)` - 创建新卷
- `delete_volume(volume)` - 删除卷及其所有章节
- `rename_volume(volume, new_name)` - 重命名卷
- `create_chapter(volume, chapter_name)` - 创建新章节
- `delete_chapter(volume, chapter)` - 删除章节
- `rename_chapter(volume, chapter, new_name)` - 重命名章节

---

## 第四部分：分阶段开发计划

### 阶段 1：基础设施 + 基础对话（1-2 周）

**目标**：搭建核心框架，实现基础对话和 @指令路由

#### 第 1 周：基础设施

| 天 | 任务 | 涉及文件 | 核心知识点 |
|----|------|---------|-----------|
| D1 | 配置管理 | `config_manager.py` | ConfigParser |
| D2 | 日志模块 | `agent_logger.py` | logging 模块 |
| D3 | LLM 客户端 | `agent_llm.py` | ChatOpenAI |
| D4 | Agent 状态图 | `agent_graph.py` | **LangGraph StateGraph** |
| D5 | Agent 基类 | `base_agent.py` | 继承、封装 |

**D1：config_manager.py**

```python
import configparser
import os

class ConfigManager:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini', encoding='utf-8')
    
    def get_llm_config(self) -> dict:
        return {
            "api_url": self.config.get("LLM", "api_url"),
            "model_name": self.config.get("LLM", "model_name"),
            "api_key": os.environ.get("LLM_API_KEY", ""),
            "temperature": self.config.getfloat("LLM", "temperature"),
        }

config_manager = ConfigManager()  # 全局单例
```

**D4：agent_graph.py（核心）**

```python
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

class AgentGraph:
    def __init__(self, llm, tools, system_prompt):
        self.llm = llm
        self.tools = tools
        self.llm_with_tools = llm.bind_tools(tools)
        self.tool_map = {tool.name: tool for tool in tools}
        self.system_prompt = system_prompt
        self.graph = self._build_graph()
    
    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("llm", self._llm_node)
        
        if self.tools:
            graph.add_node("tools", self._tool_node)
            graph.add_edge(START, "llm")
            graph.add_conditional_edges(
                "llm", 
                self._should_continue,
                {"tools": "tools", "end": END}
            )
            graph.add_edge("tools", "llm")
        else:
            graph.add_edge(START, "llm")
            graph.add_edge("llm", END)
        
        return graph.compile()
```

#### 第 2 周：工具系统 + 项目管理

| 天 | 任务 | 涉及文件 |
|----|------|---------|
| D1 | 工具注册表 | `core/tools/__init__.py` |
| D2 | 基础工具 | `read_tool.py`、`write_tool.py`、`list_tool.py` |
| D3 | 更多工具 | `edit_tool.py`、`glob_tool.py`、`ask_tool.py` |
| D4 | 项目管理 | `project_manager.py` |
| D5 | @指令路由 | `main.py` 中的 AgentWriter |

**验证清单**：
- [ ] `python main.py` 能启动
- [ ] 输入消息能收到回复
- [ ] `@写作 第1章` 能切换到 writer Agent
- [ ] 工具能被正确调用

### 阶段 2：写作工作流 + 核心 Agent（2-3 周）

**目标**：实现完整的写作工作流和 6 个 Agent

#### 第 3 周：Agent 开发

| 天 | 任务 | 涉及文件 |
|----|------|---------|
| D1 | ChatAgent | `chat_agent.py` |
| D2 | NovelWriter | `novel_writer.py` |
| D3 | 提示词模板 | `prompts/being_writer.md` |
| D4 | OutlinePolisher + ContentPolisher | 对应文件 |
| D5 | SummaryGenerator + InfoQuery | 对应文件 |

**创建新 Agent 的步骤**：

```python
# 1. 创建提示词文件：core/prompts/my_agent.md
# 2. 创建 Agent 文件：core/agents/my_agent.py

from core.agents.base_agent import BaseAgent
from core.tools import get_tools_by_names

class MyAgent(BaseAgent):
    def __init__(self):
        # 读取提示词
        with open("core/prompts/my_agent.md", "r", encoding="utf-8") as f:
            system_prompt = f.read()
        
        # 选择工具
        tools = get_tools_by_names(['read_file', 'write_file'])
        
        # 调用基类
        super().__init__(
            name="my_agent",
            system_prompt=system_prompt,
            tools=tools
        )

# 3. 在 core/agents/__init__.py 中导出
# from .my_agent import MyAgent

# 4. 在 parse_command() 中添加映射
# '@我的指令': 'my_agent'
```

#### 第 4 周：工作流引擎

| 天 | 任务 | 涉及文件 |
|----|------|---------|
| D1 | OutlineReviewer | `outline_reviewer.py` |
| D2 | LogicReviewer | `logic_reviewer.py` |
| D3-4 | WritingWorkflow | `writing_workflow.py` |
| D5 | 集成测试 | 全流程测试 |

**工作流控制器**：

```python
class WritingWorkflow:
    def __init__(self, writer: NovelWriter):
        self.writer = writer
        self.outline_reviewer = OutlineReviewer()
        self.logic_reviewer = LogicReviewer()
    
    def write_chapter(self, volume: int, chapter: int) -> dict:
        # Step 1: 大纲审查
        outline_section = self._extract_outline_section(volume, chapter)
        outline_review = self.outline_reviewer.review(outline_section)
        
        # Step 2: 章节写作
        chapter_content = self._write_chapter_content(volume, chapter)
        
        # Step 3: 逻辑审查
        previous_chapters = self._get_all_previous_chapters(volume, chapter)
        logic_review = self.logic_reviewer.review(chapter_content, previous_chapters)
        
        return {
            "success": True,
            "chapter_content": chapter_content,
            "outline_review": outline_review,
            "logic_review": logic_review
        }
```

**验证清单**：
- [ ] `@写作 第1卷 第1章` 能触发完整工作流
- [ ] 大纲审查能检测问题
- [ ] 章节能正确写入文件
- [ ] 逻辑审查能检查与前文的矛盾

### 阶段 3：自定义工具系统（1 周）

**目标**：实现 Skill 目录格式和热加载

| 天 | 任务 |
|----|------|
| D1 | 设计 Skill 目录格式 |
| D2 | 实现 `_load_custom_tools()` |
| D3 | 创建示例工具 |
| D4 | 编写文档 |
| D5 | 测试热加载 |

**Skill 目录结构**：

```
core/tools/custom/my-tool/
├── SKILL.md              # 必须：描述工具功能
└── scripts/
    └── my_tool.py        # 工具实现
```

**热加载关键代码**：

```python
import importlib.util

def _load_skill(skill_name: str, skill_dir: str):
    scripts_dir = os.path.join(skill_dir, "scripts")
    
    for filename in os.listdir(scripts_dir):
        if filename.endswith(".py"):
            # 从文件路径动态加载模块
            spec = importlib.util.spec_from_file_location(
                f"custom.{skill_name}.{filename[:-3]}",
                os.path.join(scripts_dir, filename)
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 扫描 @tool 函数并注册
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, BaseTool):
                    register_tool(attr)
```

### 阶段 4：预览 + 导出 + 章节管理（1-2 周）

| 天 | 任务 |
|----|------|
| D1-2 | 章节列表 API + 章节目录树 API |
| D3 | 卷/章节的创建、删除、重命名 API（`POST/DELETE/PUT`） |
| D4 | 前端章节目录树 UI（卷/章节增删改按钮） |
| D5 | 导出为 ZIP |
| D6 | 集成测试 |

**命名规则**（默认生成 + 解析均遵循）：
- 卷目录：`第X卷-{卷名}`（中划线分隔），例如 `第一卷-命运的邂逅/`；未命名时仅 `第一卷`
- 章节文件：`第X卷_第Y章_{章节名}.md`（下划线分隔），例如 `第一卷_第1章_命运的邂逅.md`；未命名时为 `第一卷_第1章.md`
- 中文数字由 `core.project_manager.num_to_cn()` 生成（1→一、2→二、...、11→十一、23→二十三）
- 解析兼容旧格式 `第X卷_卷名` 与 `vol{N}` 目录，保证历史项目可继续读取

**命名规则校验**（`core.project_manager.validate_name()`）：
- 禁止字符：`/ \ : * ? " < > | - _`（这些字符会与命名规范或文件系统冲突）
- 长度限制：不超过50个字符
- 前端 `validateName()` 函数在用户输入时即时校验，弹出提示框显示规则和示例
- 后端 `validate_name()` 在创建/重命名时再次校验，抛出 `ValueError` 异常
- API 层捕获 `ValueError` 并返回400错误，附带清晰的错误信息

**REST API（卷/章节管理）**：
- `POST   /api/projects/{name}/volume` — 新建卷（body: `{name}`）
- `DELETE /api/projects/{name}/volume/{vol}` — 删除卷及其所有章节
- `PUT    /api/projects/{name}/volume/{vol}` — 重命名卷（body: `{name}`）
- `POST   /api/projects/{name}/chapter/create` — 新建章节（body: `{volume, name}`）
- `DELETE /api/projects/{name}/chapter/{vol}/{ch}` — 删除章节
- `PUT    /api/projects/{name}/chapter/{vol}/{ch}` — 重命名章节（body: `{name}`）

**前端交互（右侧栏【章节】面板）**：
- 工具栏：`🔄 刷新` + `＋ 新建卷`
- 每个卷标题右侧悬浮：`＋`（新建章节）、`✏`（重命名卷）、`✕`（删除卷）
- 每个章节项悬浮：`✏`（重命名章节）、`✕`（删除章节）
- 重命名/新建通过 `prompt()` 弹窗输入名称；删除通过 `confirm()` 二次确认

### 阶段 5：Web 界面整合（1-2 周）

| 天 | 任务 |
|----|------|
| D1 | Flask 路由骨架 |
| D2 | 项目管理 API |
| D3 | 对话 API |
| D4-5 | 前端页面 |
| D6-7 | 设置面板 + Ollama |
| D8-10 | UI 优化与测试 |

**Flask 路由示例**：

```python
@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.json
    user_input = data.get('message', '')
    
    result = agent_writer.chat(user_input)
    
    return jsonify({
        'success': True,
        'data': result
    })
```

---

## 第五部分：关键技术实现

### 5.1 创建新 Agent（完整示例）

**目标**：创建一个"翻译 Agent"

**Step 1：创建提示词**

```markdown
<!-- core/prompts/translator.md -->
# 翻译 Agent

你是一个专业的翻译助手，擅长中英文互译。

## 职责

1. 将用户提供的中文翻译成英文
2. 将用户提供的英文翻译成中文
3. 保持翻译的准确性和流畅性

## 工具

- `read_file` - 读取需要翻译的文件
- `write_file` - 保存翻译结果
```

**Step 2：创建 Agent 类**

```python
# core/agents/translator.py
from core.agents.base_agent import BaseAgent
from core.tools import get_tools_by_names
import os

class Translator(BaseAgent):
    def __init__(self):
        # 读取提示词
        prompt_path = os.path.join(
            os.path.dirname(__file__), 
            "..", "prompts", "translator.md"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
        
        # 选择工具
        tools = get_tools_by_names(['read_file', 'write_file'])
        
        # 调用基类
        super().__init__(
            name="translator",
            system_prompt=system_prompt,
            tools=tools
        )
```

**Step 3：注册 Agent**

```python
# core/agents/__init__.py
from .translator import Translator

__all__ = [
    # ... 其他 Agent
    'Translator'
]
```

**Step 4：添加指令映射**

```python
# main.py 或 web/app.py
command_map = {
    '@写作': 'writer',
    '@大纲润色': 'outline_polisher',
    '@翻译': 'translator',  # 新增
}
```

### 5.2 创建新工具（完整示例）

**目标**：创建一个"字数统计工具"

**方式 1：内置工具**

```python
# core/tools/builtin/count_words.py
from langchain_core.tools import tool

@tool
def count_words(text: str) -> str:
    """统计文本字数
    
    Args:
        text: 要统计的文本
    
    Returns:
        字数统计结果
    """
    count = len(text.replace(' ', '').replace('\n', ''))
    return f"总字数：{count}"
```

> 放在 `builtin/` 目录下会自动注册，无需额外操作。

**方式 2：自定义工具**

```
core/tools/custom/word-counter/
├── SKILL.md
└── scripts/
    └── counter.py
```

```markdown
<!-- SKILL.md -->
# 字数统计工具

统计文本的字数和行数。

## 参数

- `text`: 要统计的文本

## 示例

```python
count_words("这是一段测试文本")
# 返回："总字数：8，行数：1"
```
```

```python
# scripts/counter.py
from langchain_core.tools import tool

@tool
def count_words(text: str) -> str:
    """统计文本字数和行数"""
    char_count = len(text.replace(' ', '').replace('\n', ''))
    line_count = text.count('\n') + 1
    return f"总字数：{char_count}，行数：{line_count}"
```

### 5.3 调试 Agent 行为

**技巧 1：查看思考过程**

```python
result = agent.chat("写第一章")

for step in result['thought_process']:
    if step['type'] == 'thinking':
        print(f"💭 思考: {step['content'][:100]}")
    elif step['type'] == 'tool_call':
        print(f"🔧 调用: {step['tool']}({step['args']})")
    elif step['type'] == 'tool_result':
        print(f"📋 结果: {step['result'][:100]}")
```

**技巧 2：日志级别**

```python
# core/agent_logger.py
import logging

logging.basicConfig(level=logging.DEBUG)  # 看到所有细节
# logging.basicConfig(level=logging.INFO)   # 只看关键事件
# logging.basicConfig(level=logging.WARNING) # 只看警告和错误
```

**技巧 3：使用 demo 快速验证**

```bash
python demo/demo-langgraph.py
```

---

## 第六部分：调试与排错

### 6.1 常见错误速查表

| 错误现象 | 可能原因 | 解决方案 |
|---------|---------|---------|
| `API Key 无效或已过期` | 环境变量未设置 | `$env:LLM_API_KEY = "xxx"` |
| `无法连接到模型服务` | API URL 错误 | 检查 config.ini |
| `工具 xxx 不存在` | 工具未注册 | 检查 builtin/ 或 custom/ |
| Agent 无限循环 | 提示词问题 | 设置 `max_iterations` |
| `ModuleNotFoundError` | 导入路径错误 | 检查 `__init__.py` |
| 前端请求 404 | 路由未注册 | 检查 `@app.route()` |
| 跨域错误 | CORS 未启用 | 确保 `CORS(app)` |

### 6.2 调试流程

```
1. 运行 demo/demo-langgraph.py → 确认 LLM 连接正常
2. 运行 python main.py → 确认命令行模式正常
3. 运行 python web/app.py → 确认 Web 服务正常
4. 打开 http://localhost:8000 → 确认前端正常
5. 发送简单消息 → 确认 Agent 工作正常
6. 尝试 @指令 → 确认路由正常
7. 尝试 @写作 → 确认工作流正常
```

### 6.3 性能优化

- **对话历史过长**：定期调用 `agent.clear_history()`
- **工具调用过多**：优化提示词，让模型更精准
- **响应慢**：降低 `max_tokens` 或换用更快的模型
- **日志过多**：生产环境设为 WARNING

---

## 第七部分：扩展开发指南

### 7.1 添加新的 LLM 提供商

修改 `core/agent_llm.py`：

```python
from langchain_openai import ChatOpenAI

def create_llm(api_url, api_key, model, temperature=0.7):
    return ChatOpenAI(
        base_url=api_url,
        api_key=api_key,
        model=model,
        temperature=temperature
    )

# 支持的服务：
# - 阿里通义千问：https://dashscope.aliyuncs.com/compatible-mode/v1
# - OpenAI：https://api.openai.com/v1
# - Ollama 本地：http://localhost:11434/v1
# - DeepSeek：https://api.deepseek.com/v1
```

### 7.2 自定义工作流

参考 `writing_workflow.py`：

```python
class PolishWorkflow:
    def __init__(self, polisher: ContentPolisher):
        self.polisher = polisher
    
    def polish_chapter(self, volume: int, chapter: int) -> dict:
        # 1. 读取章节
        # 2. 调用润色 Agent
        # 3. 保存结果
        pass
```

### 7.3 开发检查清单

每个阶段完成时，对照以下清单：

- [ ] 代码能正常运行，无报错
- [ ] 关键函数有注释
- [ ] 提示词使用 Markdown 格式
- [ ] 工具的 docstring 清晰
- [ ] 日志输出有助于调试
- [ ] 新增 Agent 已注册到 `__init__.py`
- [ ] 新增 API 已更新 readme.md
- [ ] Ollama 模式下也能正常工作

---

## 附录：学习资源

| 资源 | 用途 | 链接 |
|------|------|------|
| LangGraph 文档 | 状态图 | https://langchain-ai.github.io/langgraph/ |
| LangChain 工具 | @tool 装饰器 | https://python.langchain.com/docs/how_to/custom_tools/ |
| Flask 文档 | Web 框架 | https://flask.palletsprojects.com/ |
| OpenAI API | Function Calling | https://platform.openai.com/docs/guides/function-calling |
| MDN Web Docs | HTML/CSS/JS | https://developer.mozilla.org/zh-CN/ |

---

## 结语

本手册涵盖了开发 Agent-Writer 项目所需的全部知识。建议你：

1. **先通读手册**，建立整体认知
2. **按阶段开发**，每阶段完成后对照检查清单
3. **多运行 demo**，理解 Agent-Loop 的执行流程
4. **勤查日志**，DEBUG 级别能看到所有细节

祝你开发顺利！🚀
