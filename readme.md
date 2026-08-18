# Agent-Writer 项目

## 项目简介

Agent-Writer 是一个基于 langchain + langgraph + openai 实现的写作智能体专用系统，旨在更加灵活高效地实现中短篇小说（10~30万字）的编排写作。

**核心功能：**
- 小说大纲导入或创建
- 小说项目管理（每个大纲对应一个项目）
- 多 Agent 协作（通过 @指令切换不同职能 Agent）
- 小说预览与导出
- 小说内容优化与调整
- 用户自定义工具（Python 脚本热加载）

**交互方式：**
- 本地 Python 服务启动后自动打开浏览器页面
- 统一对话窗口 + @指令切换 Agent
- 最终打包为 exe 可执行文件

---

## 核心概念

### 小说项目（Novel Project）

每个大纲对应一个独立的项目，包含：
- 大纲文件（`outline.json`）
- 章节内容（`chapters/*.md`）
- 角色信息（`characters.json`）
- 世界观设定（`worldview.json`）
- 对话历史

项目存储在 `output/{小说名}/` 目录下。

### 预置 Agent

通过 `@指令` 在统一对话中切换不同职能的 Agent：

| 指令 | Agent | 职责 |
|------|-------|------|
| `@大纲润色` | OutlinePolisher | 优化大纲结构、章节安排 |
| `@汇总说明` | SummaryGenerator | 生成简介、卖点分析、目标读者定位 |
| `@润色优化` | ContentPolisher | 章节内容润色、文笔优化 |
| `@信息查询` | InfoQuery | 查询角色、设定、进度等信息 |
| 无指令（默认） | ChatAgent | 自由对话 |

### 用户自定义工具

用户可以在 `core/tools/custom/` 目录下编写 Python 脚本，系统会自动发现并热加载，无需重启服务。

示例：
```python
# core/tools/custom/example_tool.py
from langchain_core.tools import tool

@tool
def word_count(text: str) -> str:
    """统计文本字数"""
    return f"总字数: {len(text)}"
```

---

## 目录结构

```
ai-agent-writer-dev/
├── core/                              # Agent 所有内部代码
│   ├── agent_llm.py                  # LLM 客户端
│   ├── agent_logger.py               # 日志模块
│   ├── agent_graph.py                # LangGraph Agent 图（工厂模式）
│   ├── config.py                     # 配置管理
│   ├── database.py                   # SQLite 持久化
│   ├── project_manager.py            # 小说项目管理器
│   │
│   ├── agents/                       # Agent 定义
│   │   ├── base_agent.py             # Agent 基类
│   │   ├── outline_polisher.py       # @大纲润色 Agent
│   │   ├── summary_generator.py      # @汇总说明 Agent
│   │   ├── content_polisher.py       # @润色优化 Agent
│   │   ├── info_query.py             # @信息查询 Agent
│   │   └── chat_agent.py             # @自由对话 Agent（默认）
│   │
│   ├── tools/                        # Agent 工具
│   │   ├── __init__.py               # 工具注册表（含热加载逻辑）
│   │   ├── builtin/                  # 内置工具
│   │   │   ├── outline_tools.py      # 大纲操作
│   │   │   ├── chapter_tools.py      # 章节读写
│   │   │   ├── character_tools.py    # 角色管理
│   │   │   └── query_tools.py        # 信息查询
│   │   │
│   │   └── custom/                   # 用户自定义工具（热加载）
│   │       ├── README.md             # 工具开发文档
│   │       └── example_tool.py       # 示例工具
│   │
│   └── prompts/                      # 系统提示词模板
│       ├── outline_polisher.py       # 大纲润色提示词
│       ├── summary_generator.py      # 汇总说明提示词
│       ├── content_polisher.py       # 润色优化提示词
│       ├── info_query.py             # 信息查询提示词
│       └── chat.py                   # 自由对话提示词
│
├── web/                              # 浏览器页面脚本（纯 Python）
│   ├── app.py                        # Chainlit 入口
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
│       ├── metadata.json             # 项目元数据
│       ├── outline.json              # 大纲（树形结构：卷 → 章 → 节）
│       ├── characters.json           # 角色信息
│       ├── worldview.json            # 世界观设定
│       ├── chapters/                 # 章节内容
│       │   ├── vol1_ch01.md
│       │   └── ...
│       └── export/                   # 导出文件
│           ├── full.txt
│           └── full.md
│
├── demo/                             # 演示代码
│   ├── demo.py
│   ├── demo-langchain.py
│   └── demo-langgraph.py
│
├── launcher.py                       # exe 入口：启动服务 + 打开浏览器
├── writer-agent.spec                 # PyInstaller 打包配置
├── config.ini                        # API 配置
├── requirements.txt                  # 依赖
└── main.py                           # 命令行入口
```

---

## 架构设计

```
浏览器 UI (Chainlit)
┌──────────────┬──────────────────────────────────┐
│ 项目管理面板  │  统一对话窗口                      │
│ (侧边栏)     │  - @指令路由到不同 Agent            │
│ - 项目列表    │  - 工具调用可视化                   │
│ - 新建/导入   │  - 流式输出                        │
│ - 切换/删除   │                                   │
│              ├──────────────────────────────────┤
│              │  底部面板（可折叠）                 │
│              │  大纲查看 | 章节预览 | 工具管理     │
└──────────────┴──────────────────────────────────┘
                     │ HTTP (localhost:8000)
┌────────────────────┼──────────────────────────────┐
│  web/callbacks.py: @指令解析 → Agent 路由          │
└────────────────────┬──────────────────────────────┘
                     │
┌────────────────────┼──────────────────────────────┐
│  core/agents/ (Agent 注册表)                       │
│  OutlinePolisher / SummaryGenerator / ...          │
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

---

## 开发计划

### Phase 1: 项目管理 + 基础对话 + @指令路由 (3-4 天)

**目标：** 实现小说项目管理 + 统一对话 + @指令路由

**任务：**
1. `core/project_manager.py` — 创建/导入/切换/删除小说项目
2. `core/database.py` — SQLite 持久化（projects, sessions, messages 表）
3. `core/agents/base_agent.py` — Agent 基类 + 注册表
4. `core/agent_graph.py` — 从 demo 抽取 LangGraph 工厂
5. `web/callbacks.py` — @指令解析（`@大纲润色` → `outline_polisher`）
6. `web/app.py` — Chainlit 入口
7. `web/components/project_manager.py` — 侧边栏项目管理 UI

**验证：**
- 可以创建/导入小说项目
- 切换项目正常
- 对话中 `@大纲润色` 等指令能路由到对应 Agent
- 无 @指令时默认自由对话

---

### Phase 2: 预置 Agent 实现 (3-4 天)

**目标：** 实现 4 个预置 Agent 的核心功能

**任务：**
1. `@大纲润色` Agent (`core/agents/outline_polisher.py`)
   - 系统提示词：专注于大纲结构优化
   - 工具：`outline_tools.py`（读取/修改大纲）
   - 功能：分析大纲问题、建议优化方案、生成修改后的大纲

2. `@汇总说明` Agent (`core/agents/summary_generator.py`)
   - 系统提示词：生成小说汇总信息
   - 工具：`outline_tools.py`、`query_tools.py`
   - 功能：生成简介、卖点分析、目标读者定位

3. `@润色优化` Agent (`core/agents/content_polisher.py`)
   - 系统提示词：专注于文笔润色
   - 工具：`chapter_tools.py`（读取/修改章节）
   - 功能：对指定章节进行润色、优化对话、描写增强

4. `@信息查询` Agent (`core/agents/info_query.py`)
   - 系统提示词：查询小说相关信息
   - 工具：`query_tools.py`（查询角色、设定、进度等）
   - 功能：回答关于角色、设定、写作进度的问题

5. 内置工具开发
   - `core/tools/builtin/outline_tools.py`: 大纲读写、修改
   - `core/tools/builtin/chapter_tools.py`: 章节读写
   - `core/tools/builtin/character_tools.py`: 角色管理
   - `core/tools/builtin/query_tools.py`: 信息查询

6. 提示词模板 (`core/prompts/`)
   - 为每个 Agent 编写专用系统提示词

**验证：**
- `@大纲润色 帮我优化第一章的结构` → 调用大纲工具，返回优化建议
- `@汇总说明 生成小说简介` → 分析大纲，生成简介
- `@润色优化 润色第3章` → 读取章节，返回润色版本
- `@信息查询 主角的性格特点是什么` → 查询角色信息，返回答案

---

### Phase 3: 用户自定义工具 (2-3 天)

**目标：** 支持用户编写 Python 脚本注册工具

**任务：**
1. `core/tools/custom/` 自定义工具目录
   - `README.md`: 工具开发文档（接口规范、示例）
   - `example_tool.py`: 示例工具代码

2. 热加载机制 (`core/tools/__init__.py`)
   - 扫描 `custom/` 目录下所有 `.py` 文件
   - 动态导入并注册 `@tool` 函数
   - 支持文件变更监听（使用 `watchdog`）

3. `web/components/tool_manager.py` 工具管理 UI
   - 展示所有可用工具（内置 + 自定义）
   - 显示工具名称、描述、参数
   - 启用/禁用工具

**验证：**
- 用户编写 `custom/my_tool.py` → 系统自动发现并注册
- 工具管理面板显示新工具
- 对话中 Agent 可以调用自定义工具

---

### Phase 4: 大纲/章节预览 + 导出 (2 天)

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
   - 使用 `cl.File` 提供下载

**验证：**
- 大纲查看器正常显示树形结构
- 章节预览正常渲染 Markdown
- 导出功能可下载完整小说

---

### Phase 5: exe 打包 (2 天)

**目标：** 双击 exe → 启动服务 → 自动打开浏览器

**任务：**
1. `launcher.py` 启动脚本
   - subprocess 启动 `chainlit run web/app.py --port 8000`
   - 轮询等待服务就绪
   - `webbrowser.open()` 打开浏览器

2. PyInstaller 打包
   - `writer-agent.spec` 配置数据文件
   - 包含 `core/tools/custom/` 目录（用户自定义工具）
   - 包含 `output/` 目录（小说项目）

**验证：**
- 干净 Windows 环境双击 exe → 浏览器自动打开 → 功能完整

---

## 关键技术实现

### @指令解析

```python
# web/callbacks.py
AGENT_MAPPING = {
    "@大纲润色": "outline_polisher",
    "@汇总说明": "summary_generator",
    "@润色优化": "content_polisher",
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

```python
# core/tools/custom/example_tool.py
from langchain_core.tools import tool

@tool
def word_count(text: str) -> str:
    """统计文本字数"""
    return f"总字数: {len(text)}"
```

放入 `custom/` 目录后自动发现并注册，无需重启。

### 小说项目结构

```
output/{小说名}/
├── metadata.json       # {title, author, genre, synopsis, created_at}
├── outline.json        # {volumes: [{title, chapters: [{title, summary}]}]}
├── characters.json     # {characters: [{name, role, personality, relationships}]}
├── worldview.json      # {setting, rules, history}
├── chapters/
│   ├── vol1_ch01.md
│   └── ...
└── export/
    ├── full.txt
    └── full.md
```

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
chainlit>=1.0.0           # Web UI
pyinstaller>=6.0.0        # exe 打包
watchdog>=3.0.0           # 文件监听（热加载）
```

---

## 验证清单

- [ ] **Phase 1**: 项目管理 + 基础对话 + @指令路由
- [ ] **Phase 2**: 4 个预置 Agent 功能正常
- [ ] **Phase 3**: 用户自定义工具热加载
- [ ] **Phase 4**: 大纲/章节预览 + 导出
- [ ] **Phase 5**: exe 双击启动

---

## 技术选型

- **Chainlit** — 专为 LLM 聊天设计，与 LangGraph 深度集成，内置流式输出和工具调用展示
- **统一对话 + @指令** — 简化 UI，用户无需切换窗口
- **小说项目制** — 每个大纲对应一个项目，独立管理
- **用户自定义工具** — 支持 Python 脚本热加载，扩展性强
- **SQLite** — 本地工具零配置，足够个人使用

---

## 进一步优化

1. Agent 间协作（如 `@大纲润色` 完成后自动触发 `@汇总说明`）
2. 版本管理（大纲/章节的历史版本）
3. 离线 LLM 支持（Ollama）
4. 云同步（可选将小说同步到 GitHub Gist / 云盘）