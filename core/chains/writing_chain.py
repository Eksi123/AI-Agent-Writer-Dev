"""
正文写作链
负责根据大纲和上下文生成章节正文
"""
import re
from typing import Optional, List, Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from core.agent_llm import LangChainChatModel
from core.models.chapter_outline import ChapterOutline
from core.models.story_blueprint import StoryBlueprint
from core.logger import Logger


_logger = Logger("writing_chain")


# ========== 章节正文写作 ==========

WRITING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是一位才华横溢的小说家，拥有深厚的文学功底和丰富的创作经验。

## 写作规范
- 视角：{pov}
- 时态：过去时
- 对话风格：自然、有区分度，每个角色的说话方式应与其性格匹配
- 描写要求：细腻但不冗长，注重感官细节
- 节奏控制：张弛有度，根据情绪曲线调整

## 风格指南
{style_guide}

## 角色卡片
{character_sheets}

## 写作禁忌
- 不要使用"他心想"、"她想到"等直白的心理描写，改用行为和细节暗示
- 不要过度使用形容词和副词
- 不要让角色说出与性格不符的话
- 不要出现与设定矛盾的情节
- 不要写出大段独白或说教

## 输出要求
请直接输出章节正文，不要包含章节标题和任何元信息。
正文应当流畅自然，仿佛出自一位真正的小说家之手。"""),
    ("human", """## 故事背景
{story_background}

## 前情提要
{previous_context}

## 情节线索追踪
{plot_tracking}

## 上一章结尾
{last_chapter_ending}

## 本章大纲
{chapter_outline}

## 本章要求
- 目标字数：约{word_count_target}字
- 情绪曲线：{emotional_arc}
- 章末钩子：{chapter_hook}

请写出完整的第{chapter_id}章正文。""")
])


# ========== 分段写作（场景级别）==========

SCENE_WRITING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是一位才华横溢的小说家。请根据场景大纲和前文续写。

## 风格指南
{style_guide}

## 写作要求
- 视角：{pov}
- 时态：过去时
- 与前文自然衔接
- 完成场景目标，推进冲突
- 注意角色言行一致性

请直接输出场景正文。"""),
    ("human", """## 前文（最后部分）
{previous_text}

## 当前场景大纲
场景地点：{scene_location}
出场角色：{scene_characters}
场景目标：{scene_goal}
场景冲突：{scene_conflict}
场景结果：{scene_outcome}
场景氛围：{scene_mood}

## 角色信息
{character_info}

请续写这个场景，约{scene_word_target}字。""")
])


class WritingChain:
    """正文写作链"""
    
    def __init__(self, llm: LangChainChatModel):
        """
        初始化写作链
        
        Args:
            llm: LangChain 兼容的 LLM 实例
        """
        self.llm = llm
        self.output_parser = StrOutputParser()
        _logger.info("写作链初始化完成")
    
    def write_chapter(self, outline: ChapterOutline, blueprint: StoryBlueprint,
                     story_background: str, previous_context: str,
                     plot_tracking: str, last_chapter_ending: str,
                     character_sheets: str, style_guide: str = "") -> str:
        """
        生成完整章节
        
        Args:
            outline: 章节大纲
            blueprint: 故事蓝图
            story_background: 故事背景
            previous_context: 前情提要
            plot_tracking: 情节追踪
            last_chapter_ending: 上一章结尾
            character_sheets: 角色卡片
            style_guide: 风格指南
        
        Returns:
            章节正文
        """
        _logger.info(f"开始写作第{outline.chapter_id}章: {outline.title}")
        
        # 如果场景较多，使用分段写作
        if len(outline.scenes) > 2:
            return self._write_by_scenes(
                outline, blueprint, story_background, previous_context,
                plot_tracking, last_chapter_ending, character_sheets, style_guide
            )
        
        # 否则一次性生成
        chain = WRITING_PROMPT | self.llm | self.output_parser
        response = chain.invoke({
            "pov": blueprint.pov,
            "style_guide": style_guide or "自然流畅，注重细节",
            "character_sheets": character_sheets or "请参考大纲中的角色信息",
            "story_background": story_background,
            "previous_context": previous_context,
            "plot_tracking": plot_tracking or "暂无",
            "last_chapter_ending": last_chapter_ending or "（这是第一章）",
            "chapter_outline": outline.to_prompt_string(),
            "word_count_target": outline.word_count_target,
            "emotional_arc": outline.emotional_arc or "平稳",
            "chapter_hook": outline.chapter_hook or "无特殊要求",
            "chapter_id": outline.chapter_id,
        })
        
        _logger.info(f"第{outline.chapter_id}章写作完成，正文长度: {len(response)}字")
        return response
    
    def _write_by_scenes(self, outline: ChapterOutline, blueprint: StoryBlueprint,
                        story_background: str, previous_context: str,
                        plot_tracking: str, last_chapter_ending: str,
                        character_sheets: str, style_guide: str = "") -> str:
        """
        分段写作（按场景）
        
        当章节场景较多时，逐场景生成以保证质量
        """
        _logger.info(f"使用分段写作模式，共{len(outline.scenes)}个场景")
        
        full_chapter = ""
        
        # 第一个场景使用上一章结尾作为前文
        previous_text = last_chapter_ending or "（这是第一章的开头）"
        
        # 每个场景的字数目标
        scene_word_target = outline.word_count_target // max(len(outline.scenes), 1)
        
        for i, scene in enumerate(outline.scenes):
            _logger.info(f"写作场景 {scene.scene_id}: {scene.location}")
            
            # 获取出场角色信息
            char_info = character_sheets  # 简化处理，传入全部角色信息
            
            chain = SCENE_WRITING_PROMPT | self.llm | self.output_parser
            scene_text = chain.invoke({
                "style_guide": style_guide or "自然流畅，注重细节",
                "pov": blueprint.pov,
                "previous_text": previous_text[-2000:] if previous_text else "",
                "scene_location": scene.location,
                "scene_characters": ", ".join(scene.characters_present),
                "scene_goal": scene.goal,
                "scene_conflict": scene.conflict or "无明确冲突",
                "scene_outcome": scene.outcome or "待定",
                "scene_mood": scene.mood or "自然",
                "character_info": char_info,
                "scene_word_target": scene_word_target,
            })
            
            full_chapter += scene_text + "\n\n"
            previous_text = scene_text  # 更新前文
        
        _logger.info(f"分段写作完成，总长度: {len(full_chapter)}字")
        return full_chapter.strip()
    
    def revise_chapter(self, original_text: str, outline: ChapterOutline,
                      review_report: str, blueprint: StoryBlueprint,
                      character_sheets: str, style_guide: str = "") -> str:
        """
        根据审校意见修改章节
        
        Args:
            original_text: 原始正文
            outline: 章节大纲
            review_report: 审校报告
            blueprint: 故事蓝图
            character_sheets: 角色卡片
            style_guide: 风格指南
        
        Returns:
            修改后的正文
        """
        _logger.info(f"开始修改第{outline.chapter_id}章")
        
        revise_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一位专业的小说编辑和作家。请根据审校意见修改小说章节。

## 修改原则
1. 保留原文的优点和风格
2. 针对性地解决审校指出的问题
3. 不要大幅改动不需要修改的部分
4. 确保修改后的文本与前后章节衔接自然

## 风格指南
{style_guide}

请直接输出修改后的完整章节正文。"""),
            ("human", """## 原始正文
{original_text}

## 章节大纲
{chapter_outline}

## 审校报告
{review_report}

## 角色卡片
{character_sheets}

请根据审校意见修改以上章节，输出修改后的完整正文。""")
        ])
        
        chain = revise_prompt | self.llm | self.output_parser
        revised = chain.invoke({
            "style_guide": style_guide or "自然流畅，注重细节",
            "original_text": original_text,
            "chapter_outline": outline.to_prompt_string(),
            "review_report": review_report,
            "character_sheets": character_sheets,
        })
        
        _logger.info(f"第{outline.chapter_id}章修改完成，修改后长度: {len(revised)}字")
        return revised
