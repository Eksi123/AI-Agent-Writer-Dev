# Agent-Writer 项目

## 项目简介

Agent-Writer 是一个基于 langchain + langgraph + openai 实现的写作智能体专用系统，旨在更加灵活高效地实现中短篇小说（10~30万字）的编排写作。

**核心功能：**
- 小说大纲导入或创建
- 小说项目管理（每个大纲对应一个项目）
- 固定写作工作流（大纲审查 → 逐章写作 → 逻辑审查）
- 多 Agent 协作（通过 @指令切换不同职能 Agent，默认Agent不用@切换）
- 小说预览与导出
- 小说内容优化与调整
- 用户自定义工具（Python 脚本热加载）
- LLM 配置管理（Web 页面可修改 API URL / Key，支持切换本地离线模型如 Ollama）

**交互方式：**
- 本地 Python 服务启动后自动打开浏览器页面
- 统一对话窗口 + @指令切换 Agent
- 最终产出一个 HTML 文件，点击即可在浏览器中打开 Agent 可操作的 Web 界面

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 设置环境变量

API Key 通过环境变量传入，**不会写入配置文件**，确保安全：

```bash
# Windows PowerShell
$env:LLM_API_KEY = "your-api-key-here"

# Linux / macOS
export LLM_API_KEY="your-api-key-here"
```

> 建议将 `export LLM_API_KEY=...` 写入 `~/.bashrc` 或 `~/.zshrc`，避免每次手动设置。
> 如果使用 Ollama 本地模型，无需设置 API Key。

### 3. 配置 LLM（可选）

编辑 `config.ini` 设置默认 LLM 配置（也可在 Web 页面中修改）：

```ini
[LLM]
api_url = https://dashscope.aliyuncs.com/compatible-mode/v1
model_name = qwen-plus
provider = openai_compatible
temperature = 0.7
```

> API Key 从环境变量 `LLM_API_KEY` 读取，不在配置文件中存储。

### 4. 启动服务

```bash
python web/app.py
或
python main.py --web
```

服务启动后会自动打开浏览器加载 Web 界面。

### 5. 基本使用流程

1. **创建项目** — 在侧边栏点击"新建项目"，输入小说名称
2. **编写大纲** — 在对话中让 Agent 帮你创建大纲，或手动编辑 `outline.md`
3. **开始写作** — 输入 `@写作 第1章` 触发写作工作流
4. **查看进度** — 在大纲查看器和章节预览器中查看写作成果
5. **导出小说** — 选择本地目录导出完整小说（TXT / Markdown）

---

## 核心概念

### 小说项目（Novel Project）

每个大纲对应一个独立的项目，项目结构精简为两部分：

**项目文件（Markdown 格式）：**
- `outline.md` — 大纲（包含故事梗概、角色设定、世界观、写作要求、分卷分章的剧情概要等所有设定信息）

**正文组织：**
- 章节文件存放在 `chapters/` 目录下
- 若小说分卷，采用分卷子文件夹：`chapters/vol{卷序号}/`
- 章节文件命名规范：`vol{卷序号}_ch{章节序号}_{章节名}.md`
- 示例：`chapters/vol1/vol1_ch01_初入江湖.md`

**项目结构：**
- 大纲和正文统一存储在 `output/{小说名}/` 目录下
- 支持多卷、多章节的灵活组织

### 预置 Agent

通过 `@指令` 在统一对话中切换不同职能的 Agent：

| 指令 | Agent | 职责 |
|------|-------|------|
| `@写作` | NovelWriter | 执行写作工作流（大纲审查→逐章写作→逻辑审查） |
| `@大纲润色` | OutlinePolisher | 优化大纲结构、小说设定和章节安排 |
| `@小说润色` | ContentPolisher | 章节内容润色、文笔优化 |
| `@汇总说明` | SummaryGenerator | 生成小说各类信息汇总，包括人物汇总，地点汇总，剧情经历汇总，章节字数汇总等等 |
| `@信息查询` | InfoQuery | 查询小说内各种细节信息以及网络上信息 |
| 无指令（默认） | ChatAgent | 自由对话，此时不支持编辑小说 |

### 写作工作流（Writing Workflow）

小说写作采用固定的工作流，每次写作前必须经过审查，确保质量：

```
开始写作（@写作 第X章）
        │
        ▼
┌─────────────────────┐
│  Step 1: 大纲审查    │  审查当前章节对应的大纲部分
│  - 大纲是否合理      │  - 情节逻辑是否自洽
│  - 与前文是否衔接    │  - 角色行为是否符合设定
│  - 有问题则询问用户  │
└────────┬────────────┘
         │ 审查通过 / 用户确认修改后
         ▼
┌─────────────────────┐
│  Step 2: 章节写作    │  基于大纲逐章完成写作
│  - 逐章节完成        │  - 参考世界观、角色设定
│  - 参考前文内容      │  - 保持风格一致性
│  - 输出：章节正文    │
└────────┬────────────┘
         │ 本章写作完成
         ▼
┌─────────────────────┐
│  Step 3: 逻辑审查    │  审查本章正文与前面所有正文
│  - 情节逻辑是否严密  │  - 角色行为是否矛盾
│  - 时间线是否一致    │  - 伏笔/设定是否冲突
│  - 有问题则询问用户  │
└────────┬────────────┘
         │ 审查通过 / 用户确认修改后
         ▼
    本章完成，可进入下一章
```

**关键规则：**
- 每章写作前**必须**先审查对应大纲部分是否合理正确
- 审查完成后才开始写作，必须**逐章节**完成（不能跳章）
- 每章写作完成后**必须**审查本章正文与前面所有正文的逻辑一致性

### 用户自定义工具

用户可以在 `core/tools/custom/` 目录下创建自定义工具，系统会自动发现并热加载，无需重启服务。

**使用 Skill 目录格式创建工具：**

1. 在 `core/tools/custom/` 下创建一个以工具名命名的目录（如 `my-tool/`）
2. 在目录中创建 `SKILL.md` 文件（必需），描述工具功能、参数和使用示例
3. 在 `scripts/` 子目录中创建 Python 脚本，实现工具函数
4. 保存后系统自动加载

**Skill 目录结构：**
```
custom/
└── my-tool/                    # 工具目录（目录名即工具组名）
    ├── SKILL.md                # 工具描述文档（必需）
    ├── scripts/                # Python 脚本目录
    │   └── my_tool.py          # 工具实现脚本
    ├── references/             # 参考文档（可选）
    └── assets/                 # 资源文件（可选）
```

**工具规范：**
- 必须使用 `@tool` 装饰器（来自 `langchain_core.tools`）
- 必须提供清晰的 docstring（作为工具描述展示给 LLM）
- 所有参数必须有类型注解
- 必须返回 `str` 类型结果
- `SKILL.md` 必须包含工具描述、参数说明和使用示例

**示例：**
```python
# custom/my-tool/scripts/my_tool.py
from langchain_core.tools import tool

@tool
def word_count(text: str) -> str:
    """
    统计文本的字数和行数
    
    Args:
        text: 要统计的文本内容
    
    Returns:
        字数和行数统计结果
    """
    char_count = len(text.replace(' ', ''))
    line_count = text.count('\n') + 1
    return f"字符数: {char_count}, 行数: {line_count}"
```

**热加载：** 修改自定义工具后，调用 `reload_custom_tools()` 即可重新加载，无需重启服务。

详细说明参见 `core/tools/custom/README.md`。

---

## 目录结构

```
ai-agent-writer-dev/
├── core/                              # Agent 所有内部代码
│   ├── agent_llm.py                  # LLM 客户端（支持 OpenAI / Ollama 等多后端）
│   ├── agent_logger.py               # 日志模块
│   ├── agent_graph.py                # LangGraph Agent 图（工厂模式）
│   ├── config.py                     # 配置管理（支持运行时动态修改 LLM 配置）
│   ├── database.py                   # SQLite 持久化
│   ├── project_manager.py            # 小说项目管理器
│   │
│   ├── agents/                       # Agent 定义
│   │   ├── base_agent.py             # Agent 基类
│   │   ├── novel_writer.py           # @写作 Agent（执行写作工作流）
│   │   ├── outline_polisher.py       # @大纲润色 Agent
│   │   ├── summary_generator.py      # @汇总说明 Agent
│   │   ├── content_polisher.py       # @小说润色 Agent
│   │   ├── info_query.py             # @信息查询 Agent
│   │   └── chat_agent.py             # @自由对话 Agent（默认）
│   │
│   ├── workflow/                     # 写作工作流引擎
│   │   ├── writing_workflow.py       # 工作流控制器（大纲审查→写作→逻辑审查）
│   │   ├── outline_reviewer.py       # 大纲审查逻辑
│   │   └── logic_reviewer.py         # 正文逻辑审查逻辑
│   │
│   ├── tools/                        # Agent 工具
│   │   ├── __init__.py               # 工具注册表（含热加载逻辑）
│   │   ├── builtin/                  # 内置工具
│   │   │   ├── read_tool.py          # 文件读取
│   │   │   ├── write_tool.py         # 文件写入
│   │   │   ├── edit_tool.py          # 文件修改
│   │   │   ├── glob_tool.py          # 文件查询（按模式匹配）
│   │   │   ├── list_tool.py          # 列出指定目录下的文件和文件夹
│   │   │   ├── todo_tool.py          # 创建或更新任务清单
│   │   │   ├── ask_tool.py           # 向用户提问以澄清需求
│   │   │   └── online_tool.py        # 从互联网请求获取资料
│   │   │
│   │   └── custom/                   # 用户自定义工具（热加载，Skill 目录格式）
│   │       ├── README.md             # 工具开发手册
│   │       ├── skill_template.py     # Skill 格式模板说明
│   │       ├── example-word-count/   # 示例：字数统计工具
│   │       │   ├── SKILL.md          # 工具描述文档
│   │       │   └── scripts/
│   │       │       └── word_count.py # 工具实现
│   │       └── example-file-info/    # 示例：文件信息查询工具
│   │           ├── SKILL.md          # 工具描述文档
│   │           └── scripts/
│   │               └── file_info.py  # 工具实现
│   │
│   └── prompts/                      # 系统提示词模板
│       ├── being_writer.py           # 写作要求提示词
│       ├── outline_polisher.py       # 大纲润色优化提示词
│       ├── content_polisher.py       # 正文润色优化提示词
│       └── review.py                 # 小说审查提示词
│
├── web/                              # Web 界面
│   ├── index.html                    # 最终产出的 HTML 文件（点击即可打开 Web 界面）
│   ├── app.py                        # 后端服务入口
│   ├── callbacks.py                  # @指令解析 + 消息路由
│   ├── stream_handler.py             # 流式输出处理
│   └── components/                   # UI 组件封装
│       ├── project_manager.py        # 项目管理面板（侧边栏）
│       ├── chat.py                   # 对话聊天组件
│       ├── outline_viewer.py         # 大纲查看器
│       ├── chapter_preview.py        # 章节预览器
│       └── tool_manager.py           # 工具管理面板
│
├── output/                           # 小说产出目录（按小说名分目录）
│   └── {小说名}/
│       ├── outline.md                # 大纲（包含所有设定 + 分卷分章剧情概要）
│       └── chapters/                 # 章节正文
│           ├── vol1/
│           │   ├── vol1_ch01_初入江湖.md
│           │   └── ...
│           └── vol2/
│               └── ...
│
├── demo/                             # 演示代码
│   ├── demo.py
│   ├── demo-langchain.py
│   └── demo-langgraph.py
│
├── config.ini                        # API 配置（默认值，可在 Web 页面动态修改）
├── requirements.txt                  # 依赖
└── main.py                           # 命令行入口
```

### config.ini 配置说明

```ini
[LLM]
# 大模型 API 地址（支持 OpenAI 兼容接口 / Ollama 本地接口）
api_url = https://dashscope.aliyuncs.com/compatible-mode/v1
# 模型名称（如 qwen-plus / gpt-4o / llama3 等）
model_name = qwen-plus
# 模型后端类型：openai_compatible | ollama
provider = openai_compatible
# 生成参数
temperature = 0.7
top_p = 0.9

[Server]
# 后端服务端口
port = 8000
# 是否自动打开浏览器
auto_open_browser = true
```

> **API Key 不存储在配置文件中**，通过环境变量 `LLM_API_KEY` 读取。`config.ini` 中的其他值可在 Web 页面的**设置面板**中实时修改，无需重启服务。

---

## 架构设计

```
浏览器 UI (HTML 页面)
┌──────────────┬──────────────────────────────────┐
│ 项目管理面板  │  统一对话窗口                      │
│ (侧边栏)     │  - @指令路由到不同 Agent            │
│ - 项目列表    │  - 工具调用可视化                   │
│ - 新建/导入   │  - 流式输出                        │
│ - 切换/删除   │  - 工作流状态显示                   │
│              ├──────────────────────────────────┤
│              │  底部面板（可折叠）                 │
│              │  大纲查看 | 章节预览 | 工具管理     │
└──────────────┴──────────────────────────────────┘
                     │ HTTP (localhost:8000)
┌────────────────────┼──────────────────────────────┐
│  web/app.py: 后端服务 + @指令解析 → Agent 路由      │
└────────────────────┬──────────────────────────────┘
                     │
┌────────────────────┼──────────────────────────────┐
│  core/workflow/ (写作工作流引擎)                   │
│  状态机: REVIEW_OUTLINE → WRITING → REVIEW_LOGIC   │
│  - 大纲审查: outline_reviewer.py                   │
│  - 逻辑审查: logic_reviewer.py                     │
└────────────────────┬──────────────────────────────┘
                     │
┌────────────────────┼──────────────────────────────┐
│  core/agents/ (Agent 注册表)                       │
│  NovelWriter / OutlinePolisher / ...               │
│  每个 Agent 有专用系统提示词 + 工具集              │
└────────────────────┬──────────────────────────────┘
                     │
┌────────────────────┼──────────────────────────────┐
│  core/tools/ (工具注册表)                          │
│  builtin/ (内置) + custom/ (用户自定义，热加载)     │
└────────────────────┬──────────────────────────────┘
                     │
┌────────────────────┼──────────────────────────────┐
│  output/{小说名}/ (小说项目数据)                    │
└───────────────────────────────────────────────────┘
```

### API 端点

#### REST API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/projects` | 获取所有小说项目列表 |
| `POST` | `/api/projects` | 创建新项目（请求体：`{name, outline_content?}`） |
| `GET` | `/api/projects/{id}` | 获取项目详情（大纲、章节列表、状态） |
| `DELETE` | `/api/projects/{id}` | 删除项目 |
| `GET` | `/api/projects/{id}/outline` | 读取大纲内容 |
| `PUT` | `/api/projects/{id}/outline` | 更新大纲内容 |
| `GET` | `/api/projects/{id}/chapters` | 获取章节列表（树形结构） |
| `GET` | `/api/projects/{id}/chapters/{chapter_id}` | 读取指定章节内容 |
| `POST` | `/api/projects/{id}/export` | 导出完整小说（请求体：`{format, save_path}`） |
| `GET` | `/api/llm/config` | 获取当前 LLM 配置（不含 API Key） |
| `PUT` | `/api/llm/config` | 更新 LLM 配置（不含 API Key） |
| `GET` | `/api/llm/ollama/models` | 获取 Ollama 本地可用模型列表 |
| `GET` | `/api/tools` | 获取所有可用工具列表（内置 + 自定义） |
| `POST` | `/api/tools/reload` | 重新加载自定义工具 |

#### WebSocket

- **连接地址：** `ws://localhost:8000/ws/chat`
- **消息格式（客户端 → 服务端）：**

```json
{
    "type": "chat",
    "project_id": "项目ID",
    "message": "@写作 第1章"
}
```

- **消息格式（服务端 → 客户端）：**

```json
{
    "type": "stream",
    "content": "正在审查大纲...",
    "agent": "novel_writer",
    "status": "running"
}
```

- **status 状态值：** `running`（生成中）| `tool_call`（工具调用）| `done`（完成）| `error`（错误）

### 数据库结构（SQLite）

数据库文件：`data/agent_writer.db`

```sql
-- 小说项目表
CREATE TABLE projects (
    id TEXT PRIMARY KEY,              -- 项目唯一 ID（UUID）
    name TEXT NOT NULL,               -- 小说名称
    output_path TEXT NOT NULL,        -- 产出目录路径（output/{小说名}/）
    status TEXT DEFAULT 'planning',   -- 状态：planning / writing / completed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 会话表（每个项目的每次对话为一个会话）
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,              -- 会话唯一 ID
    project_id TEXT NOT NULL,         -- 所属项目 ID
    agent_type TEXT DEFAULT 'chat',   -- 当前 Agent 类型
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- 消息表（会话中的每条消息）
CREATE TABLE messages (
    id TEXT PRIMARY KEY,              -- 消息唯一 ID
    session_id TEXT NOT NULL,         -- 所属会话 ID
    role TEXT NOT NULL,               -- 角色：user / assistant / tool
    content TEXT NOT NULL,            -- 消息内容
    tool_calls TEXT,                  -- 工具调用记录（JSON，仅 assistant 角色）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- LLM 配置表（运行时动态修改的配置，不含 API Key）
CREATE TABLE llm_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- 单行配置
    api_url TEXT,
    model_name TEXT,
    provider TEXT DEFAULT 'openai_compatible',
    temperature REAL DEFAULT 0.7,
    top_p REAL DEFAULT 0.9,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- 注意：API Key 始终从环境变量 LLM_API_KEY 读取，不入库、不入配置文件
```

---

## 开发计划

### Phase 1: 项目管理 + 基础对话 + @指令路由 

**目标：** 实现小说项目管理 + 统一对话 + @指令路由

**任务：**
1. `core/project_manager.py` — 创建/导入/切换/删除小说项目
2. `core/database.py` — SQLite 持久化（projects, sessions, messages 表）
3. `core/agents/base_agent.py` — Agent 基类 + 注册表
4. `core/agent_graph.py` — 从 demo 抽取 LangGraph 工厂
5. `web/callbacks.py` — @指令解析（`@大纲润色` → `outline_polisher`）
6. `web/app.py` — 后端服务入口
7. `web/components/project_manager.py` — 侧边栏项目管理 UI

**验证：**
- 可以创建/导入小说项目
- 切换项目正常
- 对话中 `@大纲润色` 等指令能路由到对应 Agent
- 无 @指令时默认自由对话

---

### Phase 2: 写作工作流 + 核心 Agent 

**目标：** 实现写作工作流引擎 + 5 个预置 Agent

**任务：**

1. **写作工作流引擎** (`core/workflow/`)
   - `writing_workflow.py`: 工作流控制器
     - 状态机管理：`REVIEW_OUTLINE` → `WRITING` → `REVIEW_LOGIC` → `DONE`
     - 每个阶段可暂停、可回退
     - 支持用户介入修改
   - `outline_reviewer.py`: 大纲审查逻辑
     - 审查当前章节大纲是否合理、与前文衔接
     - 发现问题时通过对话询问用户是否修改
   - `logic_reviewer.py`: 正文逻辑审查逻辑
     - 审查本章正文与前面所有正文的逻辑一致性
     - 检查：角色行为、时间线、设定矛盾、伏笔衔接
     - 发现问题时通过对话询问用户是否修改

2. **`@写作` Agent** (`core/agents/novel_writer.py`)
   - 系统提示词：专注于小说写作，遵循写作工作流
   - 工具：`read_tool`、`write_tool`、`edit_tool`、`list_tool`
   - 功能：执行完整写作工作流（大纲审查→逐章写作→逻辑审查）
   - 必须逐章节完成，每章完成后进行逻辑审查

3. **`@大纲润色` Agent** (`core/agents/outline_polisher.py`)
   - 系统提示词：专注于大纲结构优化
   - 工具：`read_tool`、`write_tool`、`edit_tool`
   - 功能：分析大纲问题、建议优化方案、生成修改后的大纲

4. **`@汇总说明` Agent** (`core/agents/summary_generator.py`)
   - 系统提示词：生成小说汇总信息
   - 工具：`read_tool`、`list_tool`
   - 功能：生成小说简介、人物汇总、剧情汇总、地点汇总、章节统计等汇总信息

5. **`@小说润色` Agent** (`core/agents/content_polisher.py`)
   - 系统提示词：专注于文笔润色
   - 工具：`read_tool`、`write_tool`、`edit_tool`
   - 功能：对指定章节进行润色、优化对话、描写增强

6. **`@信息查询` Agent** (`core/agents/info_query.py`)
   - 系统提示词：查询小说相关信息
   - 工具：`read_tool`、`list_tool`、`glob_tool`
   - 功能：回答关于某一细节剧情，网络上其他小说相关联信息等

7. **内置工具**（已实现，启动时自动注册）
   - `core/tools/builtin/read_tool.py`: 文件读取
   - `core/tools/builtin/write_tool.py`: 文件写入
   - `core/tools/builtin/edit_tool.py`: 文件修改
   - `core/tools/builtin/glob_tool.py`: 文件查询（按模式匹配）
   - `core/tools/builtin/list_tool.py`: 列出指定目录下的文件和文件夹
   - `core/tools/builtin/todo_tool.py`: 创建或更新任务清单
   - `core/tools/builtin/ask_tool.py`: 向用户提问以澄清需求
   - `core/tools/builtin/online_tool.py`: 从互联网请求获取资料

8. **提示词模板** (`core/prompts/`)
   - `being_writer.py`: 写作要求提示词（遵循工作流）
   - `outline_polisher.py`: 大纲润色优化提示词
   - `content_polisher.py`: 正文润色优化提示词
   - `review.py`: 小说审查提示词（大纲审查 + 逻辑审查）

**验证：**
- `@写作 第1章` → 触发工作流：大纲审查 → 写作 → 逻辑审查
- `@大纲润色 帮我优化第一章的结构` → 调用大纲工具，返回优化建议
- `@汇总说明 生成小说简介` → 读取整部小说，帮我生成一个汇总文档
- `@小说润色 润色第3章` → 读取章节，返回润色版本
- `@信息查询 主角的性格特点是什么` → 查询角色的剧情发展，返回答案

---

### Phase 3: 用户自定义工具 

**目标：** 支持用户通过 Skill 目录格式创建自定义工具

**任务：**
1. `core/tools/custom/` 自定义工具目录（Skill 目录格式）
   - `README.md`: 工具开发文档（Skill 格式规范、示例）
   - `skill_template.py`: Skill 格式模板说明
   - `example-word-count/`: 示例工具目录
     - `SKILL.md`: 工具描述文档
     - `scripts/word_count.py`: 工具实现脚本

2. 热加载机制 (`core/tools/__init__.py`)
   - 扫描 `custom/` 目录下所有包含 `SKILL.md` 的子目录
   - 动态导入 `scripts/` 目录下的 `@tool` 函数并注册
   - 支持文件变更监听（使用 `watchdog`）

3. `web/components/tool_manager.py` 工具管理 UI
   - 展示所有可用工具（内置 + 自定义）
   - 显示工具名称、描述、参数
   - 启用/禁用工具

**验证：**
- 用户创建 `custom/my-tool/SKILL.md` + `scripts/my_tool.py` → 系统自动发现并注册
- 工具管理面板显示新工具
- 对话中 Agent 可以调用自定义工具

---

### Phase 4: 大纲/章节预览 + 导出 

**目标：** 实现大纲查看、章节预览、导出功能

**任务：**
1. `web/components/outline_viewer.py` 大纲查看器
   - 树形结构展示大纲（卷 → 章 → 节）
   - 可折叠展开
   - 点击章节跳转到对应内容

2. `web/components/chapter_preview.py` 章节预览器
   - Markdown 渲染章节内容
   - 分章节浏览

3. 导出功能
   - 合并所有章节为完整小说
   - 导出为 TXT / Markdown
   - 用户自选本地目录保存

**验证：**
- 大纲查看器正常显示树形结构
- 章节预览正常渲染 Markdown
- 导出功能可选择目录保存完整小说

---

### Phase 5: HTML 产出

**目标：** 最终产出一个 HTML 文件，点击即可在浏览器中打开 Agent 可操作的 Web 界面

**任务：**
1. `web/index.html` 前端页面
   - 单文件 HTML（内嵌 CSS + JS），点击即可在浏览器中打开
   - 多项目管理：支持创建、导入、删除小说项目，可在多个项目间自由切换
   - 项目侧边栏：显示项目列表，点击即可切换当前项目，各项目的对话历史独立
   - 包含完整的对话界面、大纲查看器、章节预览器
   - 设置面板：可修改 LLM API URL、模型名称，API Key 通过环境变量配置
   - 模型切换：支持选择本地离线模型（如 Ollama），自动检测本地可用模型列表
   - 通过 WebSocket / HTTP 与本地后端服务通信

2. 后端服务启动
   - `main.py` 或启动脚本：启动本地 Python 后端服务
   - 自动打开浏览器加载 `index.html`
   - 后端处理 Agent 调用、工具执行、文件读写等

3. 前后端通信
   - WebSocket 实现流式输出
   - REST API 实现项目管理、大纲/章节读写等操作

**验证：**
- 启动服务后自动打开浏览器 → 显示 Agent Web 界面
- 可创建多个小说项目，项目侧边栏正确显示所有项目
- 切换项目后对话界面、大纲、章节内容正确更新，对话历史独立
- 对话、工具调用、项目管理等功能完整可用

---

## 关键技术实现

### @指令解析

```python
# web/callbacks.py
AGENT_MAPPING = {
    "@写作": "novel_writer",
    "@大纲润色": "outline_polisher",
    "@汇总说明": "summary_generator",
    "@小说润色": "content_polisher",
    "@信息查询": "info_query",
}

def parse_agent_command(message: str) -> tuple[str, str]:
    """
    解析 @指令
    Returns: (agent_type, clean_message)
    """
    for prefix, agent_type in AGENT_MAPPING.items():
        if message.startswith(prefix):
            return agent_type, message[len(prefix):].strip()
    
    # 无 @指令，默认自由对话
    return "chat", message
```

### Agent 基类

```python
# core/agents/base_agent.py
from abc import ABC, abstractmethod
from typing import List, Dict

class BaseAgent(ABC):
    def __init__(self, name: str, system_prompt: str, tools: List):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """构建 LangGraph 状态图"""
        from core.agent_graph import create_agent
        return create_agent(self.tools, self.system_prompt)
    
    @abstractmethod
    async def process(self, message: str, context: Dict) -> str:
        """处理用户消息"""
        pass
```

### 用户自定义工具示例

```
custom/
└── example-word-count/           # Skill 目录
    ├── SKILL.md                  # 工具描述文档
    └── scripts/
        └── word_count.py         # 工具实现
```

```python
# custom/example-word-count/scripts/word_count.py
from langchain_core.tools import tool

@tool
def word_count(text: str) -> str:
    """统计文本字数"""
    return f"总字数: {len(text)}"
```

创建 `SKILL.md` + `scripts/` 目录后自动发现并注册，无需重启。

### 小说项目结构

```
output/{小说名}/
├── outline.md          # 大纲（包含所有设定 + 分卷分章剧情概要）
└── chapters/           # 章节正文目录
    ├── vol1/           # 第一卷
    │   ├── vol1_ch01_初入江湖.md
    │   ├── vol1_ch02_神秘老者.md
    │   └── ...
    └── vol2/           # 第二卷
        └── ...
```

**说明：**
- `outline.md` 包含故事梗概、角色设定、世界观、写作要求、自定义提示词、分卷分章剧情概要等所有设定信息
- 审查结果不生成文件，有问题时直接询问用户是否修改
- 小说导出时由用户自选本地目录保存，不存放在 output 下

#### 核心文件说明

所有配置文件均采用 **Markdown 格式**，自由书写，无需遵循固定 JSON 结构。

**1. outline.md - 大纲（唯一的核心配置文件）**

outline.md 包含小说的所有设定信息（故事梗概、角色设定、世界观、写作要求、自定义提示词、分卷分章剧情概要），是整个小说项目的核心文件。

> 📄 完整的大纲模板文件位于 `output/outline_template.md`，用户在 Web 页面可预览此模板。创建新项目时，系统会基于此模板生成 `outline.md`。

模板包含以下章节：
1. **故事梗概** - 500-1000字的故事梗概
2. **主题** - 小说核心主题
3. **角色设定** - 主角/配角的详细信息及关系
4. **世界观设定** - 世界背景、时代背景、力量体系、世界规则
5. **写作要求** - 风格、基调、视角、目标字数、特殊约束
6. **自定义提示词（可选）** - 覆盖各 Agent 的默认系统提示词
7. **分卷分章剧情概要** - 每卷概要 + 每章概要、要点、出场角色、目标字数

**2. 章节文件命名规范**
- 格式：`vol{卷序号}_ch{章节序号}_{章节名}.md`
- 示例：`vol1_ch01_初入江湖.md`、`vol2_ch15_最终决战.md`

**3. 审查机制**
- 审查结果不生成独立文件，有问题时直接询问用户是否修改

**4. 小说导出**
- 导出时由用户自选本地目录保存，支持 TXT / Markdown 格式

---

## 依赖

```txt
# 现有
langchain==1.3.15
langchain-core==1.5.4
langchain-openai==1.5.1
langgraph==1.2.11
openai==2.54.0

# 新增
fastapi>=0.100.0          # Web 后端框架
uvicorn>=0.23.0           # ASGI 服务器
websockets>=11.0          # WebSocket 支持
watchdog>=3.0.0           # 文件监听（热加载）
jinja2>=3.1.0             # HTML 模板引擎
langchain-ollama>=0.2.0   # Ollama 本地离线模型支持
```

---

## 验证清单

### Phase 1: 项目管理 + 基础对话 + @指令路由
- [ ] 可以创建新的小说项目
- [ ] 可以导入现有大纲（JSON/Markdown格式）
- [ ] 项目列表正常显示，支持切换/删除
- [ ] 对话中 `@大纲润色` 等指令能正确路由到对应 Agent
- [ ] 无 @指令时默认使用 ChatAgent 进行自由对话
- [ ] 对话历史正确保存到 SQLite

### Phase 2: 写作工作流 + 核心 Agent
- [ ] `@写作 第1章` 触发完整工作流：大纲审查 → 写作 → 逻辑审查
- [ ] 大纲审查能检测逻辑问题并询问用户是否修改
- [ ] 逐章写作功能正常，参考世界观、角色设定、前文内容
- [ ] 逻辑审查能检测与前文的矛盾点
- [ ] `@大纲润色` 能分析并优化大纲结构
- [ ] `@汇总说明` 能生成小说简介、人物汇总、剧情汇总、地点汇总、章节统计等
- [ ] `@小说润色` 能对指定章节进行文笔润色
- [ ] `@信息查询` 能正确查询小说细节信息及网络信息
- [ ] 所有内置工具正常工作（read/write/edit/list/todo/ask/online）

### Phase 3: 用户自定义工具
- [ ] 用户创建 `custom/my-tool/SKILL.md` + `scripts/my_tool.py` 后系统自动发现并注册
- [ ] 工具管理面板正确显示所有工具（内置 + 自定义）
- [ ] 可以启用/禁用特定工具
- [ ] 文件变更监听正常工作，无需重启服务

### Phase 4: 大纲/章节预览 + 导出
- [ ] 大纲查看器正常显示树形结构（卷 → 章）
- [ ] 章节预览正确渲染 Markdown 内容
- [ ] 导出功能可生成完整小说（TXT/Markdown格式）
- [ ] 用户可选择本地目录保存导出文件

### Phase 5: HTML 产出
- [ ] web/index.html 前端页面完整
- [ ] 后端服务正常启动
- [ ] 浏览器自动打开并加载页面
- [ ] WebSocket 流式输出正常
- [ ] 多项目管理：可创建、导入、删除小说项目
- [ ] 项目侧边栏正确显示所有项目，点击可切换
- [ ] 切换项目后对话界面、大纲、章节内容正确更新
- [ ] 各项目的对话历史独立，互不干扰
- [ ] 设置面板可修改 LLM API URL、模型名称
- [ ] API Key 从环境变量 `LLM_API_KEY` 读取，不在配置文件和数据库中存储
- [ ] 修改 LLM 配置后即时生效，无需重启
- [ ] Ollama 本地模型检测正常，可列出已下载模型
- [ ] 切换 Ollama 模型后对话正常
- [ ] 所有功能在 Web 界面中正常工作

---

## 技术选型

- **FastAPI + WebSocket** — 轻量级 Web 框架，支持流式输出和实时通信
- **HTML 单页应用** — 最终产出 HTML 文件，点击即可在浏览器中打开
- **统一对话 + @指令** — 简化 UI，用户无需切换窗口
- **小说项目制** — 每个大纲对应一个项目，独立管理
- **用户自定义工具** — 支持 Python 脚本热加载，扩展性强
- **SQLite** — 本地存储零配置，足够个人使用

---

### LLM 配置管理

- 用户在 Web 页面可动态修改大模型配置（API URL、模型名称），API Key 通过环境变量 `LLM_API_KEY` 安全传入，无需重启服务
- 支持本地离线模型（如 Ollama），自动检测本地可用模型列表

---

## 进一步优化

1. Agent 间协作（如 `@大纲润色` 完成后自动触发 `@汇总说明`）
2. 版本管理（大纲/章节的历史版本，支持回滚）
3. 云同步（可选将小说同步到 GitHub Gist / 云盘）