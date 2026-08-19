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

**交互方式：**
- 本地 Python 服务启动后自动打开浏览器页面
- 统一对话窗口 + @指令切换 Agent
- 最终打包为 exe 可执行文件（更建议采用html文件启动）

---

## 核心概念

### 小说项目（Novel Project）

每个大纲对应一个独立的项目，项目包含以下核心内容：

**核心配置文件（Markdown 格式）：**
- `outline.md` — 大纲（故事梗概、分卷分章的情节规划）
- `characters.md` — 角色信息（主要角色设定、性格、关系）
- `worldview.md` — 世界观设定（故事背景、规则、历史）
- `requirements.md` — 写作要求（风格、主题、特殊约束）
- `prompts.md` — 自定义提示词（可选，覆盖默认系统提示词）

**正文组织：**
- 若小说分卷，采用分卷文件夹管理：`vol{卷序号}/`
- 章节文件命名规范：`vol{卷序号}_ch{章节序号}_{章节名}.md`
- 示例：`vol1_ch01_初入江湖.md`

**项目结构：**
- 大纲和正文统一存储在 `output/{小说名}/` 目录下
- 支持多卷、多章节的灵活组织

### 预置 Agent

通过 `@指令` 在统一对话中切换不同职能的 Agent：

| 指令 | Agent | 职责 |
|------|-------|------|
| `@写作` | NovelWriter | 执行写作工作流（大纲审查→逐章写作→逻辑审查） |
| `@大纲润色` | OutlinePolisher | 优化大纲结构、章节安排 |
| `@汇总说明` | SummaryGenerator | 生成简介、卖点分析、目标读者定位 |
| `@润色优化` | ContentPolisher | 章节内容润色、文笔优化 |
| `@信息查询` | InfoQuery | 查询角色、设定、进度等信息 |
| 无指令（默认） | ChatAgent | 自由对话 |

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
│  - 输出：审查报告    │
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
│  - 输出：审查报告    │
└────────┬────────────┘
         │ 审查通过 / 用户确认修改后
         ▼
    本章完成，可进入下一章
```

**关键规则：**
- 每章写作前**必须**先审查对应大纲部分是否合理正确
- 审查完成后才开始写作，必须**逐章节**完成（不能跳章）
- 每章写作完成后**必须**审查本章正文与前面所有正文的逻辑一致性
- 审查报告由 `@大纲润色` 或专门的审查逻辑生成，用户可介入修改

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
│   │   ├── novel_writer.py           # @写作 Agent（执行写作工作流）
│   │   ├── outline_polisher.py       # @大纲润色 Agent
│   │   ├── summary_generator.py      # @汇总说明 Agent
│   │   ├── content_polisher.py       # @润色优化 Agent
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
│   │   └── custom/                   # 用户自定义工具（热加载）
│   │       ├── README.md             # 工具开发手册
│   │       ├── content_review.py     # 小说审查器
│   │       └── tool_creator.py       # 工具创建器
│   │
│   └── prompts/                      # 系统提示词模板
│       ├── being_writer.py           # 写作要求提示词
│       ├── outline_polisher.py       # 大纲润色优化提示词
│       ├── content_polisher.py       # 正文润色优化提示词
│       └── review.py                 # 小说审查提示词
│       
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
│       ├── metadata.md               # 项目元数据（标题、作者、类型、状态）
│       ├── outline.md                # 大纲（故事梗概、分卷分章规划）
│       ├── characters.md             # 角色信息
│       ├── worldview.md              # 世界观设定
│       ├── requirements.md           # 写作要求
│       ├── prompts.md                # 自定义提示词（可选）
│       ├── chapters/                 # 章节内容
│       │   ├── vol1/
│       │   │   ├── vol1_ch01_初入江湖.md
│       │   │   └── ...
│       │   └── vol2/
│       │       └── ...
│       ├── reviews/                  # 审查报告（工作流生成）
│       │   ├── outline_review_vol1_ch01.md
│       │   ├── logic_review_vol1_ch01.md
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
│ - 切换/删除   │  - 工作流状态显示                   │
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

### Phase 2: 写作工作流 + 核心 Agent (4-5 天)

**目标：** 实现写作工作流引擎 + 5 个预置 Agent

**任务：**

1. **写作工作流引擎** (`core/workflow/`)
   - `writing_workflow.py`: 工作流控制器
     - 状态机管理：`REVIEW_OUTLINE` → `WRITING` → `REVIEW_LOGIC` → `DONE`
     - 每个阶段可暂停、可回退
     - 支持用户介入修改
   - `outline_reviewer.py`: 大纲审查逻辑
     - 审查当前章节大纲是否合理、与前文衔接
     - 输出审查报告（问题列表 + 修改建议）
   - `logic_reviewer.py`: 正文逻辑审查逻辑
     - 审查本章正文与前面所有正文的逻辑一致性
     - 检查：角色行为、时间线、设定矛盾、伏笔衔接

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
   - 功能：生成简介、卖点分析、目标读者定位

5. **`@润色优化` Agent** (`core/agents/content_polisher.py`)
   - 系统提示词：专注于文笔润色
   - 工具：`read_tool`、`write_tool`、`edit_tool`
   - 功能：对指定章节进行润色、优化对话、描写增强

6. **`@信息查询` Agent** (`core/agents/info_query.py`)
   - 系统提示词：查询小说相关信息
   - 工具：`read_tool`、`list_tool`、`glob_tool`
   - 功能：回答关于角色、设定、写作进度的问题

7. **内置工具开发**
   - `core/tools/builtin/read_tool.py`: 文件读取
   - `core/tools/builtin/write_tool.py`: 文件写入
   - `core/tools/builtin/edit_tool.py`: 文件修改
   - `core/tools/builtin/glob_tool.py`: 文件查询（按模式匹配）
   - `core/tools/builtin/list_tool.py`: 列出指定目录下的文件和文件夹
   - `core/tools/builtin/todo_tool.py`: 创建或更新任务清单
   - `core/tools/builtin/ask_tool.py`: 向用户提问以澄清需求
   - `core/tools/builtin/sub_agent_tool.py`: 启动子代理完成并行写作任务
   - `core/tools/builtin/online_tool.py`: 从互联网请求获取资料

8. **提示词模板** (`core/prompts/`)
   - `being_writer.py`: 写作要求提示词（遵循工作流）
   - `outline_polisher.py`: 大纲润色优化提示词
   - `content_polisher.py`: 正文润色优化提示词
   - `review.py`: 小说审查提示词（大纲审查 + 逻辑审查）

**验证：**
- `@写作 第1章` → 触发工作流：大纲审查 → 写作 → 逻辑审查
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
    "@写作": "novel_writer",
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
├── metadata.md         # 项目元数据（标题、作者、类型、状态）
├── outline.md          # 大纲（核心配置文件）
├── characters.md       # 角色信息
├── worldview.md        # 世界观设定
├── requirements.md     # 写作要求
├── prompts.md          # 自定义提示词（可选，覆盖默认系统提示词）
├── chapters/           # 章节正文目录
│   ├── vol1/           # 第一卷
│   │   ├── vol1_ch01_初入江湖.md
│   │   ├── vol1_ch02_神秘老者.md
│   │   └── ...
│   └── vol2/           # 第二卷
│       └── ...
├── reviews/            # 审查报告（工作流自动生成）
│   ├── outline_review_vol1_ch01.md   # 大纲审查报告
│   ├── logic_review_vol1_ch01.md     # 逻辑审查报告
│   └── ...
└── export/             # 导出文件目录
    ├── full.txt        # 完整小说（纯文本）
    └── full.md         # 完整小说（Markdown）
```

#### 核心文件说明

所有配置文件均采用 **Markdown 格式**，自由书写，无需遵循固定 JSON 结构。以下是参考格式示例：

**1. metadata.md - 项目元数据**
```markdown
# 小说名称

- 作者：作者名
- 类型：玄幻 / 都市 / 科幻
- 状态：planning / writing / completed
- 一句话简介：...
- 总字数：125000
```

**2. outline.md - 大纲**
```markdown
# 小说名称

## 故事梗概
（500-1000字的故事梗概）

## 主题
- 主题1
- 主题2

## 第一卷：卷标题

本卷概要（200-500字）

### 第1章：章节标题
- 章节概要（100-300字）
- 要点：要点1、要点2
- 出场角色：角色1、角色2
- 目标字数：5000

### 第2章：章节标题
- ...

## 第二卷：卷标题
...
```

**3. characters.md - 角色信息**
```markdown
# 角色设定

## 主角：角色名
- 年龄：25
- 性别：男/女
- 性格：性格特点描述
- 背景：背景故事
- 动机：动机1、动机2
- 成长弧线：角色成长弧线描述

### 关系
- 与 角色B：朋友关系，描述...
- 与 角色C：敌对关系，描述...

## 配角：角色B
...
```

**4. worldview.md - 世界观设定**
```markdown
# 世界观设定

## 世界背景
世界背景描述...

## 时代背景
...

## 地理环境
...

## 社会结构
...

## 力量体系
...

## 世界规则
- 规则1
- 规则2

## 历史事件
...

## 文化特色
...
```

**5. requirements.md - 写作要求**
```markdown
# 写作要求

## 风格
轻松幽默 / 严肃沉重

## 基调
积极向上 / 黑暗压抑

## 视角
第一人称 / 第三人称

## 目标字数
10万 - 30万字

## 目标读者
...

## 特殊约束
- 约束1
- 约束2

## 参考作品
- 参考作品1
- 参考作品2
```

**6. prompts.md - 自定义提示词（可选）**
```markdown
# 自定义提示词

如果提供此文件，将覆盖对应 Agent 的默认系统提示词。

## 写作 Agent
你是一个专业的小说写手...

## 大纲润色 Agent
你是一个大纲优化专家...

## 审查 Agent
你是一个严格的小说审查员...
```

**7. 章节文件命名规范**
- 格式：`vol{卷序号}_ch{章节序号}_{章节名}.md`
- 示例：
  - `vol1_ch01_初入江湖.md`
  - `vol1_ch02_神秘老者.md`
  - `vol2_ch15_最终决战.md`
- 章节内容采用 Markdown 格式，包含标题、正文、对话等

**8. 审查报告（reviews/）**

审查报告同样采用 Markdown 格式，由工作流自动生成：

```markdown
# 大纲审查报告 - vol1_ch01

- 审查时间：2026-01-20 14:30
- 状态：✅ 通过 / ⚠️ 需修改

## 问题
1. [高] 逻辑问题：问题描述
   - 建议：修改建议
2. [中] 其他问题：...

## 优点
- 优点1
- 优点2

## 改进建议
- 建议1
- 建议2
```

```markdown
# 逻辑审查报告 - vol1_ch01

- 审查时间：2026-01-20 15:00
- 状态：✅ 通过 / ⚠️ 需修改
- 对比章节：vol1_ch00

## 问题
1. [中] 时间线矛盾（第3段）：问题描述
   - 建议：修改建议

## 一致性评分
95%
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

### Phase 1: 项目管理 + 基础对话 + @指令路由
- [ ] 可以创建新的小说项目
- [ ] 可以导入现有大纲（JSON/Markdown格式）
- [ ] 项目列表正常显示，支持切换/删除
- [ ] 对话中 `@大纲润色` 等指令能正确路由到对应 Agent
- [ ] 无 @指令时默认使用 ChatAgent 进行自由对话
- [ ] 对话历史正确保存到 SQLite

### Phase 2: 写作工作流 + 核心 Agent
- [ ] `@写作 第1章` 触发完整工作流：大纲审查 → 写作 → 逻辑审查
- [ ] 大纲审查能检测逻辑问题并生成审查报告
- [ ] 逐章写作功能正常，参考世界观、角色设定、前文内容
- [ ] 逻辑审查能检测与前文的矛盾点
- [ ] `@大纲润色` 能分析并优化大纲结构
- [ ] `@汇总说明` 能生成小说简介和卖点分析
- [ ] `@润色优化` 能对指定章节进行文笔润色
- [ ] `@信息查询` 能正确查询角色、设定、进度信息
- [ ] 所有内置工具正常工作（read/write/edit/list/todo/ask/online）

### Phase 3: 用户自定义工具
- [ ] 用户编写 `custom/my_tool.py` 后系统自动发现并注册
- [ ] 工具管理面板正确显示所有工具（内置 + 自定义）
- [ ] 可以启用/禁用特定工具
- [ ] 文件变更监听正常工作，无需重启服务

### Phase 4: 大纲/章节预览 + 导出
- [ ] 大纲查看器正常显示树形结构（卷 → 章）
- [ ] 章节预览正确渲染 Markdown 内容
- [ ] 导出功能可生成完整小说（TXT/Markdown格式）
- [ ] 导出文件可正常下载

### Phase 5: exe 打包
- [ ] PyInstaller 打包成功
- [ ] 干净 Windows 环境双击 exe 可正常启动
- [ ] 服务启动后自动打开浏览器
- [ ] 所有功能在打包版本中正常工作

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
2. 版本管理（大纲/章节的历史版本，支持回滚）
3. 离线 LLM 支持（Ollama）
4. 云同步（可选将小说同步到 GitHub Gist / 云盘）
5. 写作统计（字数、进度、完成率可视化）
6. 多项目对比（同时管理多个小说项目，对比分析）