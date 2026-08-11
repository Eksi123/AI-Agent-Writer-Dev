# AI Agent 中短篇小说写作系统

> 基于 LangChain 构建的中短篇小说（10~30万字）自动化写作 Agent

---

## 一、项目概述

本系统是一个基于 LangChain 的多 Agent 协作写作框架，专攻 **10~30 万字** 中短篇小说的全流程自动化生成。通过"总规划师 → 分章编剧 → 章节写手 → 审校编辑"的多角色协作模式，解决长篇小说写作中 **上下文窗口有限、情节一致性难维护、角色性格易漂移** 三大核心难题。

---

## 二、核心挑战与解决思路

| 挑战 | 说明 | 解决策略 |
|------|------|----------|
| **上下文窗口有限** | 10~30万字远超任何模型的 context window | 分层摘要 + 滑动上下文 + 章节级记忆 |
| **情节一致性** | 长跨度下伏笔、线索容易遗忘或矛盾 | 全局故事线图谱 + 实体状态追踪 |
| **角色性格漂移** | 角色行为随章节推进偏离初始设定 | 角色卡片（Character Sheet）+ 一致性校验 Agent |
| **风格统一性** | 不同章节文风差异大 | 全局风格锚定 + 风格参考库 |
| **质量波动** | 部分章节质量明显低于其他 | 多轮审校 + 评分反馈循环 |

---

## 三、系统架构

### 3.1 总体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                      用户输入层 (User Input)                      │
│  题材/类型/风格/字数/核心设定/参考作品                              │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  🧠 总规划师 Agent (Master Planner)               │
│  职责：全局故事线、主题、三幕结构、高潮节奏                          │
│  输出：Story Blueprint (故事蓝图)                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              📋 分章编剧 Agent (Chapter Architect)                │
│  职责：将蓝图拆解为章节大纲，每章含场景/冲突/转折                   │
│  输出：Chapter Outline[] (章节大纲数组)                           │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│             ✍️ 章节写手 Agent (Chapter Writer) [可并行]           │
│  职责：根据大纲 + 前文摘要 + 角色卡片 → 生成完整章节               │
│  输入：章节大纲 / 角色状态快照 / 前情摘要 / 风格样本               │
│  输出：Chapter Text (章节正文，约 3000~8000 字/章)                │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│             🔍 审校编辑 Agent (Review Editor)                     │
│  职责：一致性检查 / 文风校准 / 质量评分 / 修改建议                  │
│  输出：Review Report + 修改后正文                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              📚 记忆管理器 (Memory Manager)                       │
│  职责：维护全局记忆 / 角色状态 / 情节线索 / 伏笔追踪               │
│  贯穿全流程，为所有 Agent 提供记忆检索服务                          │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 模块划分

```
ai-agent-writer-dev/
├── config.ini                    # 配置（LLM API、模型参数）
├── main.py                       # 入口 & 编排器
├── requirements.txt              # 依赖
├── core/
│   ├── agent_llm.py              # LLM 客户端封装（已有）
│   ├── logger.py                 # 日志模块（已有）
│   │
│   ├── agents/                   # ★ 新增：Agent 定义
│   │   ├── master_planner.py     # 总规划师 Agent
│   │   ├── chapter_architect.py  # 分章编剧 Agent
│   │   ├── chapter_writer.py     # 章节写手 Agent
│   │   └── review_editor.py      # 审校编辑 Agent
│   │
│   ├── memory/                   # ★ 新增：记忆系统
│   │   ├── story_memory.py       # 全局故事记忆
│   │   ├── character_sheet.py    # 角色卡片管理
│   │   ├── plot_tracker.py       # 情节线索追踪
│   │   └── summary_chain.py      # 摘要生成链
│   │
│   ├── chains/                   # ★ 新增：LangChain 链定义
│   │   ├── outline_chain.py      # 大纲生成链
│   │   ├── writing_chain.py      # 正文写作链
│   │   ├── review_chain.py       # 审校修改链
│   │   └── consistency_chain.py  # 一致性校验链
│   │
│   ├── tools/                    # ★ 新增：Agent 工具
│   │   ├── web_search.py         # 联网搜索（素材收集）
│   │   ├── knowledge_retriever.py # 知识库检索（风格/设定参考）
│   │   └── text_analyzer.py      # 文本分析（字数/可读性）
│   │
│   └── models/                   # ★ 新增：数据模型
│       ├── story_blueprint.py    # 故事蓝图模型
│       ├── chapter_outline.py    # 章节大纲模型
│       ├── character.py          # 角色模型
│       └── review_report.py      # 审校报告模型
│
├── output/                       # 生成产物
│   ├── {project_name}/
│   │   ├── blueprint.json        # 故事蓝图
│   │   ├── outlines/             # 章节大纲
│   │   ├── chapters/             # 章节正文
│   │   ├── reviews/              # 审校报告
│   │   └── final/                # 最终稿
│   │
│   └── memory/                   # 持久化记忆
│       ├── story_state.json      # 故事状态快照
│       └── characters.json       # 角色状态
│
└── knowledge/                    # 知识库
    ├── style_samples/            # 风格样本
    ├── genre_templates/          # 类型模板（悬疑/言情/科幻...）
    └── reference_works/          # 参考作品摘要
```

---

## 四、核心流程详解

### 4.1 阶段一：故事蓝图生成

```
用户输入 → Master Planner Agent → Story Blueprint
```

**输入示例：**
```
题材：都市悬疑
字数：约 15 万字
风格：冷硬派，短句为主，类似东野圭吾
核心设定：一个失忆的刑警追查连环案，最终发现凶手是自己分裂的人格
参考作品：《白夜行》的心理深度 + 《唐人街探案》的节奏感
```

**输出（Story Blueprint）：**
```json
{
  "title": "镜中之罪",
  "genre": "都市悬疑",
  "theme": "自我认知与罪责",
  "target_word_count": 150000,
  "structure": "三幕式",
  "act_1": {
    "name": "迷雾",
    "chapters": [1, 5],
    "summary": "主角林渊在一次爆炸中失去部分记忆，被指派调查连环失踪案...",
    "key_events": ["爆炸失忆", "接手案件", "发现受害者关联"]
  },
  "act_2": {
    "name": "追影",
    "chapters": [6, 15],
    "summary": "调查深入，林渊发现所有线索都指向一个不存在的人...",
    "key_events": ["发现镜像证据", "搭档怀疑", "第二次爆炸"]
  },
  "act_3": {
    "name": "破镜",
    "chapters": [16, 20],
    "summary": "真相浮出水面，林渊必须面对自己就是凶手的现实...",
    "key_events": ["人格觉醒", "最终对决", "自我审判"]
  },
  "characters": [
    {
      "name": "林渊",
      "role": "主角",
      "age": 34,
      "personality": "冷静、执着、内心有隐藏的暴力倾向",
      "arc": "从正义刑警 → 怀疑自我 → 接受真相",
      "speech_style": "简短、克制、偶尔冒出冷幽默"
    }
  ],
  "world_setting": "2024年，某二线城市，连日阴雨的秋季",
  "tone": "压抑、紧张、偶尔的黑色幽默",
  "pov": "第一人称限制视角（林渊）"
}
```

**实现要点：**
- 使用 LangChain 的 `ChatPromptTemplate` + `StructuredOutputParser` 确保输出格式
- 支持多轮对话迭代（用户可修改蓝图后再进入下一阶段）
- 蓝图以 JSON 持久化，作为后续所有 Agent 的"宪法"

### 4.2 阶段二：章节大纲拆解

```
Story Blueprint → Chapter Architect Agent → Chapter Outline[]
```

**每章大纲结构：**
```json
{
  "chapter_id": 1,
  "title": "醒来",
  "act": 1,
  "pov_character": "林渊",
  "timeline": "Day 1 - 爆炸后第3天",
  "location": "市第一医院 → 刑警大队",
  "scenes": [
    {
      "scene_id": "1-1",
      "location": "医院病房",
      "characters_present": ["林渊", "护士小张"],
      "goal": "建立主角失忆状态，制造悬念",
      "conflict": "林渊试图回忆但只看到碎片化的血腥画面",
      "outcome": "被通知返回岗位，带着头痛和困惑出发"
    },
    {
      "scene_id": "1-2",
      "location": "刑警大队会议室",
      "characters_present": ["林渊", "队长赵刚", "搭档苏晴"],
      "goal": "引入主线案件",
      "conflict": "队长欲言又止，暗示林渊之前状态不对",
      "outcome": "林渊接手案件，发现第三个受害者照片似曾相识"
    }
  ],
  "foreshadowing": ["林渊的头痛（伏笔：人格切换的生理反应）", "照片的熟悉感（伏笔：潜意识记忆）"],
  "chapter_hook": "林渊在证物室看到第三受害者的遗物——一面碎镜子，镜中映出的自己让他感到陌生",
  "word_count_target": 7000,
  "emotional_arc": "困惑 → 焦虑 → 不安"
}
```

**实现要点：**
- Agent 拥有蓝图全文作为上下文（蓝图通常 < 5000 字，在 context window 内）
- 使用 LangChain 的 `SequentialChain` 按章节顺序生成，确保前后衔接
- 每生成一章大纲，更新 `plot_tracker` 中的伏笔/线索状态

### 4.3 阶段三：章节正文写作（核心）

```
Chapter Outline + Memory Snapshot → Chapter Writer Agent → Chapter Text
```

这是整个系统最关键的环节。由于单章 3000~8000 字可能接近或超出 context window，需要精心设计上下文组装策略。

**上下文组装策略（Context Assembly）：**

```
┌──────────────────────────────────────────────────────┐
│              Chapter Writer 的输入上下文               │
├──────────────────────────────────────────────────────┤
│                                                      │
│  [System Prompt]                                     │
│  ├── 全局风格指南（~500字）                            │
│  ├── 角色卡片：本章出场角色（~300字/角色）              │
│  └── 写作规范（POV、时态、禁忌词等）                   │
│                                                      │
│  [Story Context]                                     │
│  ├── 故事蓝图摘要（~800字）                            │
│  ├── 前情摘要链（滑动窗口，最近 3~5 章摘要，~1500字）   │
│  ├── 当前卷/幕的上下文（~500字）                       │
│  └── 活跃伏笔 & 待回收线索列表（~300字）               │
│                                                      │
│  [Chapter Instruction]                               │
│  ├── 本章大纲（完整）                                  │
│  ├── 上一章最后 500 字（衔接用）                       │
│  ├── 本章特殊要求（情绪曲线、节奏等）                   │
│  └── 风格参考片段（从知识库检索）                       │
│                                                      │
│  [Output]                                            │
│  └── 生成完整章节正文（3000~8000字）                   │
│                                                      │
└──────────────────────────────────────────────────────┘
```

**LangChain 实现：**

```python
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import StructuredOutputParser

# 写作链
writing_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一位专业的小说家。请严格按照以下规范写作：

## 风格指南
{style_guide}

## 角色卡片
{character_sheets}

## 写作规范
- 视角：{pov}
- 时态：过去时
- 对话风格：{dialogue_style}
- 禁止使用：{forbidden_words}
"""),
    ("human", """## 故事背景
{story_summary}

## 前情提要
{previous_summaries}

## 当前活跃伏笔
{active_foreshadowing}

## 上一章结尾
{last_chapter_ending}

## 本章大纲
{chapter_outline}

## 本章要求
- 目标字数：{word_count_target}
- 情绪曲线：{emotional_arc}
- 章末钩子：{chapter_hook}

请写出完整的第{chapter_id}章正文。""")
])
```

**分段写作（当章节目标字数 > 单次生成上限时）：**

```python
class ChapterWriterAgent:
    """章节写手 Agent - 支持分段写作"""

    def write_chapter(self, outline: ChapterOutline) -> str:
        scenes = outline.scenes
        full_chapter = ""

        for i, scene in enumerate(scenes):
            # 每段写作时注入：前文 + 场景大纲 + 衔接指令
            context = {
                "previous_text": full_chapter[-2000:],  # 前文最后2000字
                "scene_outline": scene.to_prompt(),
                "transition": self._get_transition(i, scenes),
            }
            scene_text = self.writing_chain.invoke(context)
            full_chapter += scene_text

            # 每写完一个场景，更新记忆
            self.memory.update_scene_state(scene, scene_text)

        return full_chapter
```

### 4.4 阶段四：审校与修改

```
Chapter Text → Review Editor Agent → Revised Text + Review Report
```

**审校维度：**

| 维度 | 检查内容 | 实现方式 |
|------|----------|----------|
| **一致性** | 角色行为是否符合设定、时间线是否矛盾 | 对比角色卡片 + 时间线图谱 |
| **连贯性** | 与前后章衔接是否自然 | 对比前后章摘要/结尾 |
| **文风** | 是否符合全局风格指南 | 风格相似度评分 |
| **质量** | 情节张力、对话自然度、描写质量 | LLM 多维度打分 |
| **伏笔** | 该埋的是否埋了、该收的是否收了 | 对比伏笔追踪表 |

**审校反馈循环：**

```
                    ┌─────────────┐
                    │  审校评分 <  │
                    │  阈值(7/10) │
                    └──────┬──────┘
                           │ 是
                           ▼
章节正文 → 审校 Agent → 修改建议 → 写手 Agent 修改 → 再次审校
                           │
                           │ 否（评分 ≥ 阈值）
                           ▼
                      通过，进入下一章
```

**最大修改轮次**：3 轮，超过则人工介入标记。

### 4.5 记忆管理系统（核心基础设施）

记忆系统是整个写作 Agent 的"大脑皮层"，贯穿全流程。

```
┌─────────────────────────────────────────────────────────┐
│                    Memory Manager                        │
├─────────────┬──────────────┬──────────────┬─────────────┤
│ Story Memory│ Character    │ Plot Tracker │ Summary      │
│ (故事记忆)  │ Sheets       │ (情节追踪)   │ (摘要管理)   │
│             │ (角色卡片)   │              │             │
├─────────────┼──────────────┼──────────────┼─────────────┤
│ • 世界观设定│ • 基础档案   │ • 伏笔列表   │ • 章节摘要  │
│ • 核心冲突  │ • 性格特征   │ • 线索链     │ • 场景摘要  │
│ • 时间线    │ • 关系图谱   │ • 红鲱鱼标记 │ • 滚动摘要  │
│ • 重要事件  │ • 状态变化   │ • 未解之谜   │ • 关键对话  │
│ • 规则/魔法 │ • 语言习惯   │ • 因果链     │             │
│   体系      │ • 成长弧线   │              │             │
└─────────────┴──────────────┴──────────────┴─────────────┘
```

**角色卡片示例：**

```json
{
  "name": "林渊",
  "base_profile": {
    "age": 34,
    "occupation": "刑警",
    "appearance": "身高180，瘦削，左眉有一道旧疤",
    "personality": "冷静、执着、寡言、内心有压抑的暴力冲动"
  },
  "speech_patterns": {
    "style": "短句为主，很少用形容词",
    "catchphrases": ["无所谓", "查下去就知道了"],
    "inner_monologue": "碎片化、跳跃式、常带自我怀疑"
  },
  "state_tracker": {
    "current_location": "刑警大队",
    "current_knowledge": ["三起失踪案", "受害者间有隐秘关联"],
    "emotional_state": "焦虑但克制",
    "relationships": {
      "苏晴": "搭档，信任但感到她在隐瞒什么",
      "赵刚": "上级，尊重但察觉他态度异常"
    }
  },
  "state_history": [
    {"chapter": 1, "changes": ["发现失忆", "接手案件"]},
    {"chapter": 2, "changes": ["头痛加剧", "对苏晴产生怀疑"]}
  ]
}
```

**摘要管理策略（滑动窗口 + 分层）：**

```
第 1 章写完 → 生成章节摘要（~200字）
第 5 章写完 → 前 5 章摘要合并为"第一卷摘要"（~500字）
第 10 章写完 → 前 10 章摘要合并为"第一幕摘要"（~800字）

写作第 N 章时的上下文：
  ├── 全书摘要（~500字）—— 始终携带
  ├── 当前幕摘要（~500字）—— 始终携带
  ├── 最近 3 章摘要（~600字）—— 滑动窗口
  ├── 上一章最后 500 字 —— 衔接用
  └── 相关角色卡片（~500字）—— 按需检索
  总计约 2500~3000 字上下文
```

---

## 五、LangChain 技术实现

### 5.1 技术栈

```
langchain >= 0.3          # 核心框架
langchain-openai          # OpenAI 兼容接口（阿里云 DashScope）
langchain-community       # 社区工具集
langgraph                 # Agent 编排（状态机）
pydantic >= 2.0           # 数据模型校验
chromadb / faiss          # 向量数据库（风格样本检索）
tiktoken                  # Token 计数
```

### 5.2 Agent 编排（基于 LangGraph 状态机）

使用 LangGraph 定义写作流程的状态机，支持条件分支和循环：

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

class WritingState(TypedDict):
    """写作状态机状态"""
    current_phase: str           # blueprint / outline / writing / review
    blueprint: dict              # 故事蓝图
    outlines: List[dict]         # 章节大纲列表
    current_chapter: int         # 当前章节号
    chapter_text: str            # 当前章节正文
    review_report: dict          # 审校报告
    revision_count: int          # 修改轮次
    memory_snapshot: dict        # 记忆快照

# 定义状态机
workflow = StateGraph(WritingState)

# 添加节点
workflow.add_node("generate_blueprint", generate_blueprint_node)
workflow.add_node("generate_outlines", generate_outlines_node)
workflow.add_node("write_chapter", write_chapter_node)
workflow.add_node("review_chapter", review_chapter_node)
workflow.add_node("revise_chapter", revise_chapter_node)
workflow.add_node("finalize_chapter", finalize_chapter_node)

# 定义边（流转逻辑）
workflow.add_edge("generate_blueprint", "generate_outlines")
workflow.add_edge("generate_outlines", "write_chapter")
workflow.add_edge("write_chapter", "review_chapter")

# 条件边：审校结果决定是否修改
workflow.add_conditional_edges(
    "review_chapter",
    should_revise,  # 评分 < 7 且修改轮次 < 3 → 修改
    {
        "revise": "revise_chapter",
        "pass": "finalize_chapter",
    }
)
workflow.add_edge("revise_chapter", "review_chapter")  # 修改后重新审校

# 完成一章后，决定是否继续
workflow.add_conditional_edges(
    "finalize_chapter",
    has_next_chapter,
    {
        "next": "write_chapter",    # 还有下一章
        "done": END,                # 全部完成
    }
)

# 编译
app = workflow.compile()
```

### 5.3 自定义 LLM 适配

基于项目已有的 `AgentLLM`，适配 LangChain 的 `BaseChatModel`：

```python
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage

class CustomChatModel(BaseChatModel):
    """适配项目已有的 AgentLLM 到 LangChain 接口"""

    client: object       # openai.OpenAI 实例
    model: str

    def _generate(self, messages, stop=None, **kwargs):
        # 将 LangChain messages 转为 OpenAI 格式
        openai_messages = [
            {"role": msg.type, "content": msg.content}
            for msg in messages
        ]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            **kwargs
        )
        content = response.choices[0].message.content
        return AIMessage(content=content)

    @property
    def _llm_type(self):
        return "custom-chat-model"
```

### 5.4 工具注册

```python
from langchain.tools import Tool
from langchain.agents import initialize_agent

# 工具定义
tools = [
    Tool(
        name="search_reference",
        func=web_search_tool,
        description="联网搜索参考资料（历史、地理、专业知识等）"
    ),
    Tool(
        name="retrieve_style_sample",
        func=knowledge_retriever,
        description="从知识库检索风格相似的参考文本片段"
    ),
    Tool(
        name="check_consistency",
        func=consistency_checker,
        description="检查新生成内容与已有设定的 consistency"
    ),
    Tool(
        name="count_words",
        func=word_counter,
        description="统计文本字数和预估阅读时间"
    ),
]
```

---

## 六、关键实现细节

### 6.1 Token 预算管理

```python
class TokenBudgetManager:
    """管理每次 LLM 调用的 Token 分配"""

    def __init__(self, max_context_tokens=120000, max_output_tokens=8000):
        self.max_context = max_context_tokens
        self.max_output = max_output_tokens

    def assemble_context(self, components: dict) -> list:
        """
        按优先级分配 Token 预算：
        1. System Prompt（风格+角色）: 固定 ~2000 tokens
        2. 故事背景摘要: 固定 ~1000 tokens
        3. 前情摘要（滑动窗口）: 弹性 ~3000 tokens
        4. 当前章大纲: 固定 ~1000 tokens
        5. 上一章结尾: 固定 ~800 tokens
        6. 风格参考: 弹性 ~1500 tokens
        7. 伏笔/线索: 弹性 ~700 tokens
        """
        budget = self.max_context
        allocated = []

        # 按优先级排序
        priorities = [
            ("system_prompt", 2000, True),     # 固定，不可裁剪
            ("story_background", 1000, True),
            ("chapter_outline", 1000, True),
            ("last_chapter_ending", 800, True),
            ("previous_summaries", 3000, False), # 可裁剪
            ("style_reference", 1500, False),
            ("foreshadowing", 700, False),
        ]

        for key, max_tokens, is_fixed in priorities:
            if key in components:
                text = components[key]
                token_count = self.count_tokens(text)
                if token_count > max_tokens and not is_fixed:
                    text = self.truncate(text, max_tokens)
                allocated.append(text)
                budget -= self.count_tokens(text)

        return allocated
```

### 6.2 风格一致性保障

```python
class StyleAnchor:
    """风格锚定器 - 确保全文风格统一"""

    def __init__(self, style_samples: List[str]):
        """
        style_samples: 用户提供的风格参考文本
        """
        # 提取风格特征
        self.style_profile = self._extract_style(style_samples)

    def _extract_style(self, samples) -> dict:
        return {
            "avg_sentence_length": ...,      # 平均句长
            "dialogue_ratio": ...,           # 对话占比
            "description_density": ...,      # 描写密度
            "vocabulary_level": ...,         # 词汇层级
            "pov_markers": ...,              # 视角标记词
            "forbidden_patterns": [...],     # 禁用表达
        }

    def inject_into_prompt(self, prompt: str) -> str:
        """将风格约束注入写作 prompt"""
        style_instruction = f"""
        请严格遵循以下风格：
        - 平均句长：{self.style_profile['avg_sentence_length']}字左右
        - 对话占比：约{self.style_profile['dialogue_ratio']*100}%
        - 禁止使用：{', '.join(self.style_profile['forbidden_patterns'])}
        - 整体感觉：{self.style_profile['overall_tone']}
        """
        return style_instruction + prompt
```

### 6.3 伏笔管理系统

```python
class PlotTracker:
    """情节线索 & 伏笔追踪器"""

    def __init__(self):
        self.foreshadowings = []   # 伏笔列表
        self.climax_events = []    # 高潮事件
        self.loose_ends = []       # 未解线索

    def plant(self, chapter_id: int, description: str, expected_payoff: int):
        """埋下伏笔"""
        self.foreshadowings.append({
            "id": len(self.foreshadowings) + 1,
            "planted_chapter": chapter_id,
            "description": description,
            "expected_payoff_chapter": expected_payoff,
            "status": "active",  # active / resolved / abandoned
        })

    def resolve(self, foreshadowing_id: int, chapter_id: int, resolution: str):
        """回收伏笔"""
        for f in self.foreshadowings:
            if f["id"] == foreshadowing_id:
                f["status"] = "resolved"
                f["resolved_chapter"] = chapter_id
                f["resolution"] = resolution

    def get_active_for_chapter(self, chapter_id: int) -> list:
        """获取当前章节需要关注的活跃伏笔"""
        return [
            f for f in self.foreshadowings
            if f["status"] == "active"
            and f["expected_payoff_chapter"] >= chapter_id
        ]

    def check_overdue(self, current_chapter: int) -> list:
        """检查逾期未回收的伏笔"""
        return [
            f for f in self.foreshadowings
            if f["status"] == "active"
            and f["expected_payoff_chapter"] < current_chapter
        ]
```

### 6.4 断点续写 & 进度恢复

```python
class WritingCheckpoint:
    """写作进度管理 - 支持断点续写"""

    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.state_file = os.path.join(project_dir, "writing_state.json")

    def save_state(self, state: WritingState):
        """保存当前写作状态"""
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def load_state(self) -> WritingState:
        """恢复写作状态"""
        with open(self.state_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def can_resume(self) -> bool:
        """是否可以恢复"""
        return os.path.exists(self.state_file)
```

---

## 七、运行流程示例

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 config.ini（LLM API 信息）

# 3. 启动写作任务
python main.py --task new \
    --genre "都市悬疑" \
    --words 150000 \
    --style "冷硬派，类似东野圭吾" \
    --premise "失忆刑警追查连环案，发现凶手是自己分裂的人格"

# 4. 查看进度
python main.py --task status --project "镜中之罪"

# 5. 断点续写
python main.py --task resume --project "镜中之罪"

# 6. 导出最终稿
python main.py --task export --project "镜中之罪" --format txt
```

---

## 八、质量保障机制

### 8.1 多层质量关卡

```
章节生成 → [关卡1] 基础检查（字数、格式）
         → [关卡2] 一致性检查（角色/时间线/设定）
         → [关卡3] 质量评分（情节/对话/描写/节奏）
         → [关卡4] 伏笔检查（该埋的是否埋了）
         → 通过 → 进入下一章
         → 未通过 → 修改（最多3轮）→ 人工标记
```

### 8.2 评分维度

| 维度 | 权重 | 说明 |
|------|------|------|
| 情节推进 | 25% | 本章是否有效推进了主线/支线 |
| 角色表现 | 25% | 行为是否符合角色设定 |
| 对话质量 | 20% | 对话是否自然、有区分度 |
| 文笔风格 | 15% | 是否符合全局风格指南 |
| 节奏张力 | 15% | 情绪曲线是否符合大纲设计 |

---

## 九、扩展方向

- [ ] **人机协作模式**：支持人工介入修改大纲/章节，Agent 基于修改继续
- [ ] **多模型协作**：不同 Agent 使用不同模型（规划用强模型，写作用创意模型）
- [ ] **RAG 素材库**：接入外部知识库（历史事件、地理信息、专业知识）
- [ ] **多视角叙事**：支持 POV 切换，每个角色独立记忆线
- [ ] **对话驱动**：支持用户以对话形式实时引导写作方向
- [ ] **Web UI**：基于 Streamlit/Gradio 的可视化写作面板

---

## 十、注意事项

1. **成本控制**：15 万字小说约需 20~40 章，每章经历 写作+审校+修改 ≈ 3~5 次 LLM 调用，总计约 100~200 次调用，注意 Token 消耗
2. **模型选择**：规划/审校用推理能力强的模型（如 qwen-max），写作用创意好的模型（如 qwen-plus）
3. **人工审核**：AI 生成的长篇小说仍需人工审核，尤其是关键情节转折和结局
4. **迭代优化**：建议先用短篇（3~5万字）测试流程，验证后再扩展到中长篇
