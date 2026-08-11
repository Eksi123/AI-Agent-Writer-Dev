"""
章节写手 Agent
负责根据大纲和上下文生成章节正文
"""
import os
from typing import Optional

from core.agent_llm import AgentLLM, create_agent_llm, create_langchain_llm
from core.chains.writing_chain import WritingChain
from core.models.story_blueprint import StoryBlueprint
from core.models.chapter_outline import ChapterOutline
from core.logger import Logger


_logger = Logger("chapter_writer")


class ChapterWriterAgent:
    """
    章节写手 Agent
    
    职责：
    - 根据大纲和上下文生成章节正文
    - 支持分段写作（按场景）
    - 根据审校意见修改章节
    """
    
    def __init__(self, llm: AgentLLM = None, project_dir: str = None):
        """
        初始化章节写手
        
        Args:
            llm: LLM 客户端
            project_dir: 项目输出目录
        """
        self.llm = llm or create_agent_llm()
        self.project_dir = project_dir
        
        # 创建 LangChain 兼容的 LLM
        self.lc_llm = create_langchain_llm()
        self.writing_chain = WritingChain(self.lc_llm)
        
        _logger.info("章节写手 Agent 初始化完成")
    
    def write_chapter(self, outline: ChapterOutline, blueprint: StoryBlueprint,
                     story_background: str, previous_context: str,
                     plot_tracking: str, last_chapter_ending: str,
                     character_sheets: str, style_guide: str = "") -> str:
        """
        生成章节正文
        
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
        
        chapter_text = self.writing_chain.write_chapter(
            outline=outline,
            blueprint=blueprint,
            story_background=story_background,
            previous_context=previous_context,
            plot_tracking=plot_tracking,
            last_chapter_ending=last_chapter_ending,
            character_sheets=character_sheets,
            style_guide=style_guide,
        )
        
        # 保存章节
        if self.project_dir:
            self._save_chapter(outline.chapter_id, chapter_text)
        
        _logger.info(f"第{outline.chapter_id}章写作完成，正文长度: {len(chapter_text)}字")
        return chapter_text
    
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
        
        revised_text = self.writing_chain.revise_chapter(
            original_text=original_text,
            outline=outline,
            review_report=review_report,
            blueprint=blueprint,
            character_sheets=character_sheets,
            style_guide=style_guide,
        )
        
        # 保存修改后的章节
        if self.project_dir:
            self._save_chapter(outline.chapter_id, revised_text, revision=True)
        
        _logger.info(f"第{outline.chapter_id}章修改完成")
        return revised_text
    
    def _save_chapter(self, chapter_id: int, text: str, revision: bool = False):
        """保存章节到文件"""
        chapters_dir = os.path.join(self.project_dir, "chapters")
        os.makedirs(chapters_dir, exist_ok=True)
        
        if revision:
            filename = f"chapter_{chapter_id:03d}_revised.txt"
        else:
            filename = f"chapter_{chapter_id:03d}.txt"
        
        filepath = os.path.join(chapters_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        
        _logger.debug(f"章节已保存: {filepath}")
