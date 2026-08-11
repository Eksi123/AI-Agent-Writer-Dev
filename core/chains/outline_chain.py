"""
大纲生成链
负责生成故事蓝图和章节大纲
"""
import json
import re
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from core.agent_llm import LangChainChatModel
from core.models.story_blueprint import StoryBlueprint, Act, Character
from core.models.chapter_outline import ChapterOutline, Scene
from core.logger import Logger


_logger = Logger("outline_chain")


# ========== 故事蓝图生成 ==========

BLUEPRINT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是一位资深的小说策划大师，擅长构建完整的故事框架。

请根据用户提供的信息，生成一份详细的故事蓝图。

要求：
1. 故事结构清晰，有明确的起承转合
2. 角色性格鲜明，有成长弧线
3. 冲突设计合理，层层递进
4. 伏笔和线索布局精心
5. 风格统一，基调一致

请严格按照 JSON 格式输出，不要输出其他内容。"""),
    ("human", """请为以下小说生成故事蓝图：

题材类型：{genre}
目标字数：{target_word_count}字（约{estimated_chapters}章）
风格要求：{style}
核心设定/前提：{premise}
参考作品：{reference}
其他要求：{extra_requirements}

请按以下 JSON 格式输出：
{{
    "title": "小说标题",
    "genre": "题材类型",
    "theme": "核心主题",
    "target_word_count": {target_word_count},
    "structure": "叙事结构（如三幕式）",
    "acts": [
        {{
            "name": "幕名称",
            "chapters": [起始章节, 结束章节],
            "summary": "本幕概要（100-200字）",
            "key_events": ["关键事件1", "关键事件2"]
        }}
    ],
    "characters": [
        {{
            "name": "角色姓名",
            "role": "角色定位（主角/配角/反派等）",
            "age": 年龄数字或null,
            "personality": "性格特征描述",
            "arc": "角色成长弧线",
            "speech_style": "说话风格",
            "appearance": "外貌描述",
            "background": "背景故事"
        }}
    ],
    "world_setting": "世界观/背景设定（100-200字）",
    "tone": "整体基调",
    "pov": "叙事视角（第一人称/第三人称等）",
    "style_reference": "风格参考说明",
    "main_conflict": "主要冲突描述",
    "sub_conflicts": ["次要冲突1", "次要冲突2"]
}}""")
])


# ========== 章节大纲生成 ==========

CHAPTER_OUTLINE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是一位专业的小说编剧，擅长将故事蓝图拆解为详细的章节大纲。

请根据故事蓝图和前文信息，为指定章节生成详细大纲。

要求：
1. 每个场景要有明确的目标、冲突和结果
2. 注意与前后章的衔接
3. 合理布局伏笔和线索
4. 设计好章末钩子
5. 控制节奏和情绪曲线

请严格按照 JSON 格式输出。"""),
    ("human", """## 故事蓝图
{blueprint_text}

## 前情摘要
{previous_summaries}

## 情节追踪
{plot_tracking}

请为第{chapter_id}章生成详细大纲。

章节位置：第{act_number}幕（{act_name}）
本章在整体故事中的位置：{chapter_position}

请按以下 JSON 格式输出：
{{
    "chapter_id": {chapter_id},
    "title": "章节标题",
    "act": {act_number},
    "pov_character": "视角角色姓名",
    "timeline": "时间线描述",
    "location": "主要地点",
    "scenes": [
        {{
            "scene_id": "{chapter_id}-1",
            "location": "场景地点",
            "characters_present": ["出场角色1", "出场角色2"],
            "goal": "场景目标",
            "conflict": "场景冲突",
            "outcome": "场景结果",
            "mood": "场景氛围"
        }}
    ],
    "foreshadowing": ["本章埋下的伏笔1", "伏笔2"],
    "chapter_hook": "章末钩子描述",
    "word_count_target": {word_count_target},
    "emotional_arc": "情绪曲线（如：平静→紧张→震惊）",
    "previous_chapter_connection": "与上一章的衔接点",
    "next_chapter_setup": "为下一章做的铺垫"
}}""")
])


class OutlineChain:
    """大纲生成链"""
    
    def __init__(self, llm: LangChainChatModel):
        """
        初始化大纲链
        
        Args:
            llm: LangChain 兼容的 LLM 实例
        """
        self.llm = llm
        self.output_parser = StrOutputParser()
        _logger.info("大纲生成链初始化完成")
    
    def generate_blueprint(self, genre: str, target_word_count: int,
                          style: str, premise: str,
                          reference: str = "", extra_requirements: str = "") -> StoryBlueprint:
        """
        生成故事蓝图
        
        Args:
            genre: 题材类型
            target_word_count: 目标字数
            style: 风格要求
            premise: 核心设定/前提
            reference: 参考作品
            extra_requirements: 其他要求
        
        Returns:
            StoryBlueprint 对象
        """
        # 估算章节数（按每章 5000-8000 字计算）
        estimated_chapters = target_word_count // 6000
        
        _logger.info(f"开始生成故事蓝图: {genre}, {target_word_count}字, 约{estimated_chapters}章")
        
        # 构建提示词
        prompt = BLUEPRINT_PROMPT.format_messages(
            genre=genre,
            target_word_count=target_word_count,
            estimated_chapters=estimated_chapters,
            style=style,
            premise=premise,
            reference=reference or "无",
            extra_requirements=extra_requirements or "无",
        )
        
        # 调用 LLM
        chain = BLUEPRINT_PROMPT | self.llm | self.output_parser
        response = chain.invoke({
            "genre": genre,
            "target_word_count": target_word_count,
            "estimated_chapters": estimated_chapters,
            "style": style,
            "premise": premise,
            "reference": reference or "无",
            "extra_requirements": extra_requirements or "无",
        })
        
        # 解析 JSON
        blueprint = self._parse_blueprint(response)
        _logger.info(f"故事蓝图生成完成: 《{blueprint.title}》, {len(blueprint.characters)}个角色, {len(blueprint.acts)}幕")
        return blueprint
    
    def generate_chapter_outline(self, chapter_id: int, blueprint: StoryBlueprint,
                                 previous_summaries: str = "", plot_tracking: str = "",
                                 word_count_target: int = 5000) -> ChapterOutline:
        """
        生成章节大纲
        
        Args:
            chapter_id: 章节编号
            blueprint: 故事蓝图
            previous_summaries: 前情摘要
            plot_tracking: 情节追踪信息
            word_count_target: 目标字数
        
        Returns:
            ChapterOutline 对象
        """
        # 获取章节所属幕信息
        act = blueprint.get_act_for_chapter(chapter_id)
        act_number = blueprint.acts.index(act) + 1 if act else 1
        act_name = act.name if act else "未知"
        
        # 计算章节在整体中的位置
        total_chapters = sum(a.chapters[1] - a.chapters[0] + 1 for a in blueprint.acts)
        chapter_position = f"第{chapter_id}章/共{total_chapters}章"
        
        _logger.info(f"开始生成第{chapter_id}章大纲: {act_name}")
        
        # 调用 LLM
        chain = CHAPTER_OUTLINE_PROMPT | self.llm | self.output_parser
        response = chain.invoke({
            "blueprint_text": blueprint.to_prompt_string(),
            "previous_summaries": previous_summaries or "(这是第一章，暂无前情)",
            "plot_tracking": plot_tracking or "(暂无情节追踪信息)",
            "chapter_id": chapter_id,
            "act_number": act_number,
            "act_name": act_name,
            "chapter_position": chapter_position,
            "word_count_target": word_count_target,
        })
        
        # 解析 JSON
        outline = self._parse_chapter_outline(response, chapter_id)
        _logger.info(f"第{chapter_id}章大纲生成完成: 《{outline.title}》, {len(outline.scenes)}个场景")
        return outline
    
    def _parse_blueprint(self, response: str) -> StoryBlueprint:
        """解析蓝图 JSON 响应"""
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                
                # 解析幕
                acts = []
                for act_data in data.get("acts", []):
                    acts.append(Act(**act_data))
                
                # 解析角色
                characters = []
                for char_data in data.get("characters", []):
                    characters.append(Character(**char_data))
                
                # 构建蓝图
                blueprint = StoryBlueprint(
                    title=data.get("title", "未命名"),
                    genre=data.get("genre", ""),
                    theme=data.get("theme", ""),
                    target_word_count=data.get("target_word_count", 0),
                    structure=data.get("structure", "三幕式"),
                    acts=acts,
                    characters=characters,
                    world_setting=data.get("world_setting", ""),
                    tone=data.get("tone", ""),
                    pov=data.get("pov", "第三人称"),
                    style_reference=data.get("style_reference", ""),
                    main_conflict=data.get("main_conflict", ""),
                    sub_conflicts=data.get("sub_conflicts", []),
                )
                return blueprint
            else:
                raise ValueError("未找到 JSON 内容")
        except Exception as e:
            _logger.error(f"解析故事蓝图失败: {e}")
            _logger.error(f"原始响应: {response[:500]}")
            # 返回一个最小化的蓝图
            return StoryBlueprint(
                title="解析失败",
                genre="",
                theme="",
                target_word_count=0,
            )
    
    def _parse_chapter_outline(self, response: str, chapter_id: int) -> ChapterOutline:
        """解析章节大纲 JSON 响应"""
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                
                # 解析场景
                scenes = []
                for scene_data in data.get("scenes", []):
                    scenes.append(Scene(**scene_data))
                
                outline = ChapterOutline(
                    chapter_id=data.get("chapter_id", chapter_id),
                    title=data.get("title", f"第{chapter_id}章"),
                    act=data.get("act", 1),
                    pov_character=data.get("pov_character", ""),
                    timeline=data.get("timeline", ""),
                    location=data.get("location", ""),
                    scenes=scenes,
                    foreshadowing=data.get("foreshadowing", []),
                    chapter_hook=data.get("chapter_hook", ""),
                    word_count_target=data.get("word_count_target", 5000),
                    emotional_arc=data.get("emotional_arc", ""),
                    previous_chapter_connection=data.get("previous_chapter_connection", ""),
                    next_chapter_setup=data.get("next_chapter_setup", ""),
                )
                return outline
            else:
                raise ValueError("未找到 JSON 内容")
        except Exception as e:
            _logger.error(f"解析章节大纲失败: {e}")
            _logger.error(f"原始响应: {response[:500]}")
            return ChapterOutline(
                chapter_id=chapter_id,
                title=f"第{chapter_id}章（解析失败）",
                act=1,
                pov_character="",
            )