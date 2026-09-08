# Agent-Writer 项目

## 项目简介

Agent-Writer 是一个基于 langchain + langgraph + openai 实现的写作智能体专用系统，旨在更加灵活高效地实现中短篇小说（10~30万字）的编排写作。

**核心功能：**

- 小说大纲导入或创建
- 小说项目管理（每个大纲对应一个项目）
- 固定写作工作流（写作前审查 → 逐章写作 → 写作后审查，支持自动重试）
- 多 Agent 协作（通过 @指令切换不同职能 Agent，默认Agent不用@切换）
- 小说预览与导出
- 小说内容优化与调整
- 用户自定义 Skill（统一通过 invoke_skill 调用，支持热加载）
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

![Agent-Writer Web页面](</web页面展示.png>)

### 5. 基本使用流程

1. **创建项目** — 在侧边栏点击"新建项目"，输入小说名称
2. **编写大纲** — 在对话中让 Agent 帮你创建大纲，或手动编辑 `outline.md`
3. **开始写作** — 输入 `@写作 第1章` 触发写作工作流
4. **查看进度** — 在大纲查看器和章节预览器中查看写作成果
5. **导出小说** — 选择本地目录导出完整小说（Markdown）

---

## 核心概念

### 小说项目（Novel Project）

每个大纲对应一个独立的项目，项目结构精简为两部分：

**项目文件（Markdown 格式）：**

- `outline.md` — 大纲（包含故事梗概、角色设定、世界观、写作要求、分卷分章的剧情概要等所有设定信息）

**正文组织：**

- 章节文件存放在 `chapters/` 目录下，按卷分子文件夹
- 卷目录命名规范：`第X卷-{卷名}`（中划线分隔），示例：`第一卷-命运的邂逅`
- 章节文件命名规范：`第X卷_第Y章_{章节名}.md`（下划线分隔），示例：`第一卷_第1章_初入江湖.md`
- 若卷未命名则目录名为 `第X卷`（如 `第一卷`）
- Web 端右侧栏【章节】面板支持新建/删除卷、新建/删除章节、重命名卷和章节

**命名规则校验：**

- 卷名和章节名不能包含特殊字符：`/ \ : * ? " < > | - _`
- 卷名和章节名长度不超过50个字符
- 命名时系统会弹出提示框，明确显示规则并给出示例
- 后端和前端均有校验，防止非法名称导致文件系统错误

**项目结构：**

- 大纲和正文统一存储在 `output/{小说名}/` 目录下
- 支持多卷、多章节的灵活组织

### 预置 Agent

通过 `@指令` 在统一对话中切换不同职能的 Agent：

| 指令           | Agent            | 职责                                                                         | 联网能力 |
| -------------- | ---------------- | ---------------------------------------------------------------------------- | -------- |
| `@写作`      | NovelWriter      | 执行写作工作流（写作前审查→逐章写作→写作后审查，最多重试3次）                | ✅       |
| `@大纲润色`  | OutlinePolisher  | 优化大纲结构、小说设定和章节安排                                             | ✅       |
| `@小说润色`  | ContentPolisher  | 章节内容润色、文笔优化                                                       | ✅       |
| `@汇总说明`  | SummaryGenerator | 生成小说各类信息汇总，包括人物汇总，地点汇总，剧情经历汇总，章节字数汇总等等 | ❌       |
| `@信息查询`  | InfoQuery        | 查询小说内各种细节信息                                                       | ❌       |
| 无指令（默认） | ChatAgent        | 自由对话，此时不支持编辑小说                                                 | ✅       |

> **联网能力**：标记为 ✅ 的 Agent 可以使用 `fetch_url` 工具从互联网获取参考资料。InfoQuery 仅支持小说内部信息检索，不支持联网查询。

### 写作工作流（Writing Workflow）

小说写作采用固定的工作流，通过写作前审查和写作后审查双重保障，确保章节质量：

```
开始写作（@写作 第X章）
        │
        ▼
┌──────────────────────────┐
│  Step 1: 写作前审查       │  理解用户要求，匹配大纲章节
│  - 匹配大纲章节           │  - 按优先级审查大纲质量
│    (高) 剧情衔接是否合理   │    (中) 剧情发展是否符合逻辑
│    (低) 剧情刻画是否丰富   │  - 未匹配则进入自由写作模式
│  - 有问题则建议修改大纲    │    （只输出，不写入文件）
└────────┬─────────────────┘
         │ 审查通过
         ▼
┌──────────────────────────┐
│  Step 2: 章节写作         │  基于大纲逐章完成写作
│  - 严格按照大纲写作       │  - 参考世界观、角色设定
│  - 参考前文内容           │  - 保持风格一致性
│  - 输出：章节正文         │
└────────┬─────────────────┘
         │ 本章写作完成
         ▼
┌──────────────────────────┐
│  Step 3: 写作后审查       │  审查生成的章节质量
│  - 是否按大纲剧情写作     │  - 剧情本身是否合理
│  - 与前3章衔接是否自然    │  - 严重问题则重新生成
│  - 最多重试 3 次          │  - 3次后仍有问题则交用户确认
└────────┬─────────────────┘
         │ 审查通过
         ▼
    保存章节，可进入下一章
```

**关键规则：**

- 每章写作前**必须**先通过写作前审查（pre_writing），确认大纲质量
- 写作要求未匹配到大纲章节时，进入**自由写作模式**，内容只在对话框输出，不写入 output 目录
- 每章写作完成后**必须**通过写作后审查（post_writing），确保章节符合大纲、剧情合理、与前文衔接
- 写作后审查发现严重问题时**自动重新生成**，最多重试 3 次
- Agent 在未经允许情况下**不主动修改大纲**，但允许重新生成章节

### 用户自定义工具

用户可以在 `core/tools/custom/` 目录下创建自定义 Skill，系统会自动发现并热加载，无需重启服务。

**统一调用机制：** 所有 Skill 都通过 `invoke_skill(skill_name, args)` 工具调用。Agent 在初始化时会读取所有 Skill 的 name 和 description，根据用户需求动态决策是否调用。

**Skill 目录结构：**

```
custom/
└── my-tool/                    # 工具目录
    ├── SKILL.md                # 工具描述文档（必需）
    ├── scripts/                # Python 脚本目录（可选）
    │   └── my_tool.py          # 工具实现脚本
    ├── references/             # 参考文档（可选）
    └── assets/                 # 资源文件（可选）
```

**SKILL.md 格式（YAML frontmatter + Markdown 正文）：**

```markdown
---
name: my-skill
description: 工具功能描述
---

## 工具详细说明

这里是 Markdown 正文，调用 invoke_skill 时会返回此内容。
```

**两种使用模式：**

1. **纯 Markdown Skill**：只有 `SKILL.md`，调用 `invoke_skill` 时返回 Markdown 正文内容
2. **带脚本的 Skill**：`SKILL.md` + `scripts/` 目录，调用 `invoke_skill` 时会懒加载脚本，然后调用脚本中定义的 `@tool` 函数

**Python 脚本工具规范（scripts/ 目录）：**

- 必须使用 `@tool` 装饰器（来自 `langchain_core.tools`）
- 必须提供清晰的 docstring（作为工具描述）
- 所有参数必须有类型注解
- 必须返回 `str` 类型结果

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

**调用流程：** Agent 看到 Skill 清单 → 根据 description 决策 → 调用 `invoke_skill("my-skill", '{"tool_name": "word_count", "text": "..."}')` → 系统懒加载脚本 → 执行工具 → 返回结果

```
## 可用的自定义工具（通过 invoke_custom_tool 调用）
- word_count: 统计文本字数和行数
- file_info: 获取文件的元信息（大小、修改时间等）
```

**懒加载机制：** 带 `scripts/` 的自定义工具采用懒加载策略——启动时仅解析 `SKILL.md` 的 frontmatter 获取工具名称和描述，**不立即加载** `scripts/` 目录下的 Python 脚本。只有当 Agent 首次调用 `invoke_custom_tool` 时，才会动态加载对应的脚本文件。这样可以加快启动速度并减少内存占用。

**热加载：** 修改自定义工具后，调用 `reload_custom_tools()` 即可重新加载，无需重启服务。

详细说明参见 `core/tools/custom/README.md`。

---

## 目录结构

```
ai-agent-writer-dev/
├── core/                              # 核心模块

│   ├── agent_logger.py               # 日志模块
│   ├── agent_graph.py                # LangGraph Agent 状态图（Agent-Loop 实现）
│   ├── config_manager.py             # 配置管理（运行时动态修改 LLM 配置）
│   ├── project_manager.py            # 小说项目管理器（创建/加载/切换/删除）
│   │
│   ├── agents/                       # Agent 定义
│   │   ├── base_agent.py             # Agent 基类（封装 LangGraph 调用）
│   │   ├── novel_writer.py           # @写作 Agent（执行写作工作流）
│   │   ├── outline_polisher.py       # @大纲润色 Agent
│   │   ├── summary_generator.py      # @汇总说明 Agent
│   │   ├── content_polisher.py       # @小说润色 Agent
│   │   ├── info_query.py             # @信息查询 Agent
│   │   └── chat_agent.py             # 自由对话 Agent（默认，无 @指令时使用）
│   │
│   ├── workflow/                     # 写作工作流引擎
│   │   ├── writing_workflow.py       # 工作流控制器（写作前审查→写作→写作后审查，最多重试3次）
│   │   ├── pre_writing.py            # 写作前审查（匹配大纲 + 审查大纲质量）
│   │   └── post_writing.py           # 写作后审查（大纲符合度 + 剧情合理性 + 前文衔接）
│   │
│   ├── tools/                        # Agent 工具系统
│   │   ├── __init__.py               # 工具注册表（自动加载 + 热加载）
│   │   ├── builtin/                  # 内置工具
│   │   │   ├── read_tool.py          # 文件读取（支持行范围）
│   │   │   ├── write_tool.py         # 文件写入（追加/覆盖模式）
│   │   │   ├── edit_tool.py          # 文件编辑（文本替换）
│   │   │   ├── glob_tool.py          # 文件搜索（glob 模式匹配）
│   │   │   ├── list_tool.py          # 目录列表（文件和文件夹）
│   │   │   ├── ask_tool.py           # 向用户提问
│   │   │   ├── online_tool.py        # 网络请求（获取网页内容）
│   │   │   └── invoke_skill.py       # 自定义 Skill 统一调用入口
│   │   │
│   │   └── custom/                   # 用户自定义工具（Skill 格式，热加载）
│   │       ├── README.md             # 工具开发指南
│   │       ├── example-word-count/   # 示例：字数统计工具
│   │       │   ├── SKILL.md          # 工具描述文档
│   │       │   └── scripts/
│   │       │       └── word_count.py # 工具实现
│   │       ├── example-file-info/    # 示例：文件信息工具
│   │       │   ├── SKILL.md
│   │       │   └── scripts/
│   │       │       └── file_info.py
│   │       ├── sumeru-outline/       # 大纲编写技能
│   │       │   ├── SKILL.md
│   │       │   └── references/       # 风格参考文档
│   │       ├── sumeru-polish/        # 内容润色技能
│   │       │   └── SKILL.md
│   │       ├── sumeru-review/        # 内容审查技能
│   │       │   ├── SKILL.md
│   │       │   └── scripts/
│   │       │       └── chapter-word-counter.py
│   │       ├── sumeru-write/         # 正文写作技能
│   │       │   └── SKILL.md
│   │       ├── sumeru-topic/         # 题材选择技能
│   │       │   └── SKILL.md
│   │       ├── sumeru-finalize/      # 完结收尾技能
│   │       │   └── SKILL.md
│   │       └── sumeru-worldbuilder/  # 世界观构建技能
│   │           └── SKILL.md
│   │
│   └── prompts/                      # 系统提示词模板（Markdown 格式）
│       ├── being_writer.md           # 写作 Agent 提示词
│       ├── outline_polisher.md       # 大纲润色提示词
│       ├── content_polisher.md       # 内容润色提示词
│       ├── pre_writing.md            # 写作前审查提示词
│       └── post_writing.md           # 写作后审查提示词
│
├── web/                              # Web 界面
│   ├── app.py                        # Flask Web 服务 + REST API
│   ├── index.html                    # 前端页面入口（HTML 结构）
│   ├── css/
│   │   └── style.css                 # 前端样式
│   └── js/                           # 前端 JavaScript 模块
│       ├── app.js                    # 全局状态、初始化、工具函数（必须最先加载）
│       ├── project.js                # 项目 CRUD 与管理
│       ├── chat.js                   # 对话与 Agent 切换
│       ├── outline.js                # 大纲面板管理
│       ├── chapters.js               # 章节目录树与内容管理
│       └── settings.js               # 设置面板与配置向导
│
├── output/                           # 小说产出目录
│   └── {小说名}/
│       ├── outline.md                # 大纲
│       └── chapters/                 # 章节正文
│           └── 第一卷-命运的邂逅/     # 卷目录：第X卷-{卷名}
│               └── 第一卷_第1章_初入江湖.md  # 章节文件：第X卷_第Y章_{章节名}.md
│
├── demo/                             # 演示代码（教学示例）
│   ├── demo.py                       # 原生 OpenAI API 实现
│   ├── demo-langchain.py             # LangChain 框架实现
│   └── demo-langgraph.py             # LangGraph 状态图实现
│
├── config.ini                        # 配置文件（LLM / Ollama / Web Server）
├── requirements.txt                  # Python 依赖
├── main.py                           # 命令行入口（支持 --web 参数）
└── web页面展示.png                    # Web 界面截图
```

### config.ini 配置说明

```ini
[LLM]
# 在线大模型 API 配置（支持 OpenAI 兼容接口）
api_url = https://dashscope.aliyuncs.com/compatible-mode/v1
# 模型名称（如 qwen-plus / gpt-4o 等）
model_name = qwen3.7-plus
# 模型提供商类型
provider = qwen
# 生成参数
temperature = 0.7
top_p = 0.9

[Ollama]
# 本地模型配置（Ollama 本地部署）
api_url = http://localhost:11434/v1
# 本地模型名称（如 qwen2.5 / llama3 等）
model_name = qwen2.5
temperature = 0.7
top_p = 0.9
# 是否启用本地模型（true 时使用 Ollama，false 时使用在线模型）
enabled = false

[Web Server]
# Web 服务端口
port = 8000
# 启动时是否自动打开浏览器
auto_open_browser = true
```

> **API Key 不存储在配置文件中**，通过环境变量 `LLM_API_KEY` 读取。`config.ini` 中的其他值可在 Web 页面的**设置面板**中实时修改，无需重启服务。使用 Ollama 本地模型时无需设置 API Key。

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
│              │  右侧面板（标签切换）               │
│              │  大纲查看 | 章节预览               │
└──────────────┴──────────────────────────────────┘
                     │ HTTP (localhost:8000)
┌────────────────────┼──────────────────────────────┐
│  web/app.py: 后端服务 + @指令解析 → Agent 路由      │
└────────────────────┬──────────────────────────────┘
                     │
┌────────────────────┼──────────────────────────────┐
│  core/workflow/ (写作工作流引擎)                   │
│  状态机: PRE_WRITING → WRITING → POST_WRITING      │
│  - 写作前审查: pre_writing.py（匹配大纲+审查质量） │
│  - 写作后审查: post_writing.py（符合度+合理性+衔接）│
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

### REST API

| 方法       | 路径                                        | 说明                                          |
| ---------- | ------------------------------------------- | --------------------------------------------- |
| `GET`    | `/api/projects`                           | 获取所有小说项目列表 + 当前项目名             |
| `POST`   | `/api/projects`                           | 创建新项目（自动用模板初始化大纲）            |
| `POST`   | `/api/projects/import`                    | 导入项目（上传 .md 文件作为大纲）             |
| `POST`   | `/api/projects/{name}/switch`             | 切换到指定项目                                |
| `DELETE` | `/api/projects/{name}`                    | 删除项目                                      |
| `GET`    | `/api/projects/{name}/export`             | 导出整个项目为 ZIP 文件                       |
| `GET`    | `/api/projects/{name}/outline`            | 读取大纲内容                                  |
| `PUT`    | `/api/projects/{name}/outline`            | 保存大纲内容                                  |
| `GET`    | `/api/projects/{name}/chapters`           | 获取章节列表                                  |
| `GET`    | `/api/projects/{name}/chapter-tree`       | 获取章节目录树（按卷分组，含预览）            |
| `GET`    | `/api/projects/{name}/chapter?file=xxx`   | 读取指定章节内容                              |
| `PUT`    | `/api/projects/{name}/chapter`            | 保存章节内容                                  |
| `POST`   | `/api/projects/{name}/volume`             | 新建卷（body:`{name, volume?}`）            |
| `DELETE` | `/api/projects/{name}/volume/{vol}`       | 删除卷及其所有章节                            |
| `PUT`    | `/api/projects/{name}/volume/{vol}`       | 重命名卷（body:`{name}`）                   |
| `POST`   | `/api/projects/{name}/chapter/create`     | 新建章节（body:`{volume, name, chapter?}`） |
| `DELETE` | `/api/projects/{name}/chapter/{vol}/{ch}` | 删除章节                                      |
| `PUT`    | `/api/projects/{name}/chapter/{vol}/{ch}` | 重命名章节（body:`{name}`）                 |
| `POST`   | `/api/chat`                               | 发送消息并获取 Agent 回复                     |
| `GET`    | `/api/agent/current`                      | 获取当前激活的 Agent                          |
| `GET`    | `/api/settings`                           | 获取当前 LLM 配置（API Key 掩码处理）         |
| `POST`   | `/api/settings`                           | 更新 LLM 配置                                 |
| `GET`    | `/api/settings/status`                    | 检查配置状态（是否完整）                      |
| `POST`   | `/api/settings/test`                      | 测试 LLM 连接                                 |
| `GET`    | `/api/llm/ollama/models`                  | 获取 Ollama 本地可用模型列表                  |

---

## 开发里程碑

### Phase 1: 项目管理 + 基础对话 + @指令路由 ✅

**已完成功能：**

- 小说项目创建/导入/切换/删除（`core/project_manager.py`）
- Agent 基类和注册表（`core/agents/base_agent.py`）
- LangGraph 状态图工厂（`core/agent_graph.py`）
- @指令解析和路由（`main.py` 和 `web/app.py`）
- Flask Web 服务（`web/app.py`）
- 项目管理 UI（`web/index.html` 侧边栏）

**已验证：**

- ✅ 可以创建/导入小说项目
- ✅ 切换项目正常
- ✅ 对话中 `@大纲润色` 等指令能路由到对应 Agent
- ✅ 无 @指令时默认自由对话

---

### Phase 2: 写作工作流 + 核心 Agent ✅

**已完成功能：**

1. **写作工作流引擎** (`core/workflow/`)

   - 工作流控制器（`writing_workflow.py`）
   - 写作前审查（`pre_writing.py`）— 匹配大纲章节 + 审查大纲质量
   - 写作后审查（`post_writing.py`）— 大纲符合度 + 剧情合理性 + 前文衔接（最多重试3次）
2. **6 个预置 Agent**

   - `@写作` Agent（`novel_writer.py`）- 执行写作工作流
   - `@大纲润色` Agent（`outline_polisher.py`）- 大纲结构优化
   - `@汇总说明` Agent（`summary_generator.py`）- 生成汇总信息
   - `@小说润色` Agent（`content_polisher.py`）- 文笔润色
   - `@信息查询` Agent（`info_query.py`）- 查询小说内部细节信息
   - 自由对话 Agent（`chat_agent.py`）- 默认模式
3. **7 个内置工具**（启动时自动注册）

   - 文件读写：`read_tool`、`write_tool`、`edit_tool`
   - 目录操作：`glob_tool`、`list_tool`
   - 用户交互：`ask_tool`
   - 网络请求：`online_tool`
4. **提示词模板** (`core/prompts/`)

   - Markdown 格式的提示词文件
   - 包括写作、润色、审查等专用提示词

**已验证：**

- ✅ `@写作 第1章` 触发完整工作流
- ✅ `@大纲润色` 能分析并优化大纲
- ✅ `@汇总说明` 能生成各类汇总
- ✅ `@小说润色` 能润色章节
- ✅ `@信息查询` 能查询小说内部信息

---

### Phase 3: 用户自定义工具 ✅

**已完成功能：**

1. Skill 目录格式支持（`core/tools/custom/`）

   - 包含 `SKILL.md` 和示例工具
   - 两个完整示例：字数统计、文件信息
2. 热加载机制（`core/tools/__init__.py`）

   - 自动扫描 `custom/` 目录
   - 动态导入并注册 `@tool` 函数
   - 调用 `reload_custom_tools()` 可重新加载

**验证：**

- 用户创建 `custom/my-tool/SKILL.md` + `scripts/my_tool.py` → 系统自动发现并注册
- 工具管理面板显示新工具
- 对话中 Agent 可以调用自定义工具

---

### Phase 4: 大纲/章节预览 + 导出 ✅

**已完成功能：**

1. 大纲查看器（`web/index.html` 右侧面板）

   - 树形结构展示大纲
   - 可折叠展开
2. 章节预览器（`web/index.html` 右侧面板）

   - Markdown 渲染章节内容
   - 分章节浏览
3. 导出功能

   - 导出整个项目为 ZIP 文件
   - 包含大纲和所有章节

**已验证：**

- ✅ 大纲查看器正常显示
- ✅ 章节预览正常渲染
- ✅ 导出功能可用

---

### Phase 5: Web 界面 ✅

**已完成功能：**

1. 前端页面（`web/index.html` + `web/css/` + `web/js/`）

   - 模块化 SPA（HTML + 独立 CSS/JS 文件）
   - 多项目管理：创建、导入、删除、切换
   - 项目侧边栏
   - 对话界面、大纲查看器、章节预览器
   - 设置面板：修改 LLM 配置
   - Ollama 本地模型支持
2. 后端服务（`web/app.py`）

   - Flask Web 服务
   - 支持 `main.py --web` 或 `main.py` 启动
   - 自动打开浏览器（可配置）
3. 前后端通信

   - REST API 实现所有操作

**已验证：**

- ✅ 启动服务后自动打开浏览器
- ✅ 多项目管理正常
- ✅ 对话、工具调用等功能完整可用
- ✅ Ollama 本地模型支持正常

---

## 关键技术实现

### @指令解析

`@指令` 解析在 `main.py` 和 `web/app.py` 中的 `AgentWriter.parse_command()` 方法中实现：

```python
def parse_command(self, user_input: str) -> tuple:
    """解析用户输入，提取 @指令并映射到对应的 Agent"""
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
  
    return 'chat', user_input  # 无指令时默认自由对话
```

### Agent 基类

每个 Agent 继承自 `BaseAgent`，封装了 LangGraph 状态图的构建、Skill 提示词注入和 LLM 调用：

```python
class BaseAgent:
    def __init__(self, name: str, system_prompt: str, tools: List[BaseTool]):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools
        self._init_agent_graph()  # 构建 LangGraph 状态图 + 注入 Skill 提示词
  
    def _init_agent_graph(self) -> None:
        """初始化 Agent：自动拼接匹配的 Skill 提示词到 system_prompt"""
        config = config_manager.get_llm_config()
        full_prompt = self._build_full_prompt()
        self.agent_graph = create_agent_graph(
            base_url=config["api_url"], api_key=config["api_key"],
            model=config["model_name"], tools=self.tools,
            system_prompt=full_prompt, temperature=config["temperature"]
        )
  
    def _build_full_prompt(self) -> str:
        """构建完整 system_prompt：基础提示词 + Skill 提示词 + 自定义工具清单（含懒加载工具）"""
        skill_prompts = get_skill_prompts_for_agent(self.name)
        custom_tools = get_custom_tools_info()  # 获取自定义工具 name + description（包括待懒加载的）
        parts = [self.system_prompt]
        if skill_prompts:
            parts.extend(skill_prompts)
        if custom_tools:
            tools_desc = "\n".join([f"- {t['name']}: {t['description']}" for t in custom_tools])
            parts.append(f"## 可用的自定义工具（通过 invoke_custom_tool 调用）\n{tools_desc}")
        separator = "\n\n---\n\n"
        return separator.join(parts)
  
    def chat(self, user_input: str) -> dict:
        """调用 Agent，返回回复和思考过程"""
        result = self.agent_graph.invoke({"messages": [HumanMessage(content=user_input)]})
        return {"response": ..., "thought_process": [...]}
```

### LangGraph Agent 状态图

核心图结构在 `core/agent_graph.py` 中构建，采用经典的 Agent-Loop 模式：

```
START → llm_node → (有工具调用?) → tool_node → llm_node (循环) → END
```

### 用户自定义工具

自定义 Skill 支持两种模式：

**模式 A：纯 Markdown Skill（提示词注入）**

```
core/tools/custom/
└── sumeru-write/                 # Skill 目录
    └── SKILL.md                  # 正文注入到 applyTo 指定的 Agent
```

```markdown
---
name: sumeru-write
description: 须弥小说写作技能
applyTo: writer                   # 注入到 NovelWriter（@写作 Agent）
---

## 写作规范
1. 每次写作前先阅读大纲对应章节...
```

**模式 B：带脚本的 Skill（提示词注入 + 可调用工具）**

```
core/tools/custom/
└── example-word-count/
    ├── SKILL.md                  # applyTo: all（默认注入所有 Agent）
    └── scripts/
        └── word_count.py         # @tool 函数注册为自定义工具
```

```python
from langchain_core.tools import tool

@tool
def word_count(text: str) -> str:
    """统计文本字数"""
    return f"总字数: {len(text)}"
```

> Agent 初始化时会读取所有自定义工具的 name 和 description，注入到 system_prompt 中。Agent 根据用户需求通过 `invoke_custom_tool` **动态决策**是否调用。

创建或修改 Skill 目录后系统自动发现并注册，无需重启。

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

- `outline.md` 包含故事梗概、角色设定、世界观、写作要求、分卷分章剧情概要等所有设定信息
- 审查结果不生成文件，有问题时直接询问用户是否修改
- 小说导出时由用户自选本地目录保存，不存放在 output 下
- 大纲模板文件：`output/outline_template.md`，创建新项目时自动初始化

---

## 依赖

```txt
langchain==1.3.15         # LangChain 框架
langchain-core==1.5.4     # LangChain 核心（工具装饰器等）
langchain-openai==1.5.1   # OpenAI 兼容接口封装
langgraph==1.2.11         # LangGraph 状态图框架
openai==2.54.0            # OpenAI Python SDK
flask==3.1.3              # Flask Web 框架
flask-cors==6.0.2         # Flask 跨域支持
```

---

## 验证清单

### 基础功能

- [X] 创建/导入/切换/删除小说项目
- [X] `@大纲润色` 等指令正确路由到对应 Agent
- [X] 无 @指令时默认使用 ChatAgent 自由对话

### 写作工作流

- [X] `@写作 第1卷 第1章` 触发工作流：写作前审查 → 写作 → 写作后审查（最多重试3次）
- [X] 写作前审查能匹配大纲章节并检测大纲质量问题
- [X] 写作后审查能检测大纲偏离、剧情矛盾与前文冲突
- [X] 自由写作模式下内容只在对话框输出，不写入文件
- [X] 所有内置工具正常工作

### 自定义工具

- [X] 创建 `custom/my-tool/SKILL.md` + `scripts/` 后系统自动注册
- [X] `reload_custom_tools()` 可重新加载

### Web 界面

- [X] 启动服务后自动打开浏览器
- [X] 多项目管理（创建、导入、删除、切换）
- [X] 对话、工具调用等功能完整可用
- [X] 设置面板可修改 LLM 配置
- [X] Ollama 本地模型检测和切换
- [X] API Key 从环境变量读取，不在配置文件中存储
- [X] 导出项目为 ZIP 文件

---

## 技术选型

- **Flask** — 轻量级 Web 框架，提供 REST API
- **LangChain + LangGraph** — Agent 框架 + 状态图引擎，实现 Agent-Loop
- **OpenAI 兼容接口** — 统一封装在线/本地模型调用
- **HTML 单页应用** — 模块化前端（HTML + 独立 CSS/JS 文件），点击即可打开
- **统一对话 + @指令** — 简化 UI，用户无需切换窗口
- **小说项目制** — 每个大纲对应一个项目，独立管理
- **用户自定义工具** — 支持 Python 脚本热加载，扩展性强

---

### LLM 配置管理

- 用户在 Web 页面可动态修改大模型配置（API URL、模型名称、温度等）
- API Key 通过环境变量 `LLM_API_KEY` 安全传入，不在配置文件中存储
- 支持在线模型和 Ollama 本地模型切换，`config.ini` 中有独立的 `[Ollama]` 配置节
- Web 页面可自动检测本地 Ollama 可用模型列表，并可测试连接

---

## 进一步优化方向

1. Agent 间协作（如 `@大纲润色` 完成后自动触发 `@汇总说明`）
2. 版本管理（大纲/章节的历史版本，支持回滚）
3. 云同步（可选将小说同步到 GitHub Gist / 云盘）
4. 对话历史持久化（当前对话历史仅存内存，重启后丢失）
5. 流式输出（当前为完整响应后一次性返回）
