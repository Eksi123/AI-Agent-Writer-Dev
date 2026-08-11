"""
摘要管理器
管理章节摘要的生成、存储和滑动窗口
"""
import json
import os
from typing import List, Optional, Dict

from core.agent_llm import AgentLLM
from core.logger import Logger


_logger = Logger("summary_manager")


class ChapterSummary:
    """章节摘要"""
    
    def __init__(self, chapter_id: int, summary: str, key_events: List[str] = None,
                 word_count: int = 0, last_paragraph: str = ""):
        self.chapter_id = chapter_id
        self.summary = summary
        self.key_events = key_events or []
        self.word_count = word_count
        self.last_paragraph = last_paragraph  # 最后一段，用于衔接
    
    def to_dict(self) -> dict:
        return {
            "chapter_id": self.chapter_id,
            "summary": self.summary,
            "key_events": self.key_events,
            "word_count": self.word_count,
            "last_paragraph": self.last_paragraph,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ChapterSummary":
        return cls(
            chapter_id=data["chapter_id"],
            summary=data["summary"],
            key_events=data.get("key_events", []),
            word_count=data.get("word_count", 0),
            last_paragraph=data.get("last_paragraph", ""),
        )


class ActSummary:
    """幕摘要"""
    
    def __init__(self, act_id: int, act_name: str, summary: str, 
                 chapter_range: tuple = (0, 0)):
        self.act_id = act_id
        self.act_name = act_name
        self.summary = summary
        self.chapter_range = chapter_range  # (start, end)
    
    def to_dict(self) -> dict:
        return {
            "act_id": self.act_id,
            "act_name": self.act_name,
            "summary": self.summary,
            "chapter_range": list(self.chapter_range),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ActSummary":
        return cls(
            act_id=data["act_id"],
            act_name=data["act_name"],
            summary=data["summary"],
            chapter_range=tuple(data.get("chapter_range", [0, 0])),
        )


class SummaryManager:
    """
    摘要管理器
    
    负责：
    - 生成章节摘要
    - 合并幕摘要
    - 管理滑动窗口
    - 提供上下文组装
    """
    
    def __init__(self, project_dir: str, llm: AgentLLM = None):
        """
        初始化摘要管理器
        
        Args:
            project_dir: 项目输出目录
            llm: LLM 客户端（用于生成摘要）
        """
        self.project_dir = project_dir
        self.llm = llm
        self.memory_dir = os.path.join(project_dir, "memory")
        os.makedirs(self.memory_dir, exist_ok=True)
        
        # 章节摘要列表
        self.chapter_summaries: List[ChapterSummary] = []
        
        # 幕摘要列表
        self.act_summaries: List[ActSummary] = []
        
        # 全书摘要
        self.book_summary: str = ""
        
        # 文件路径
        self.state_file = os.path.join(self.memory_dir, "summaries.json")
        
        _logger.info("摘要管理器初始化完成")
    
    def generate_chapter_summary(self, chapter_id: int, chapter_text: str) -> ChapterSummary:
        """
        生成章节摘要
        
        Args:
            chapter_id: 章节编号
            chapter_text: 章节正文
        
        Returns:
            章节摘要对象
        """
        if not self.llm:
            _logger.warning("未配置 LLM，无法自动生成摘要")
            return ChapterSummary(
                chapter_id=chapter_id,
                summary="(未生成摘要)",
                word_count=len(chapter_text),
            )
        
        prompt = f"""请为以下小说章节生成一份简洁的摘要（200字以内），并列出关键事件。

要求：
1. 摘要要包含：主要情节、角色行为、重要对话、情绪变化
2. 关键事件用列表形式列出（最多5条）
3. 保留最后一段原文（用于下一章衔接）

章节内容：
{chapter_text}

请按以下 JSON 格式输出：
{{
    "summary": "章节摘要文本",
    "key_events": ["事件1", "事件2", ...],
    "last_paragraph": "章节最后一段原文"
}}"""
        
        try:
            response = self.llm.chat(
                prompt=prompt,
                system_prompt="你是一个专业的小说编辑，擅长提炼故事摘要。请只输出 JSON，不要输出其他内容。",
                max_tokens=2000,
                temperature=0.3,
            )
            
            # 解析 JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                summary = ChapterSummary(
                    chapter_id=chapter_id,
                    summary=data.get("summary", ""),
                    key_events=data.get("key_events", []),
                    word_count=len(chapter_text),
                    last_paragraph=data.get("last_paragraph", ""),
                )
            else:
                summary = ChapterSummary(
                    chapter_id=chapter_id,
                    summary=response[:500],
                    word_count=len(chapter_text),
                )
            
            self.chapter_summaries.append(summary)
            _logger.info(f"第{chapter_id}章摘要已生成（{len(summary.summary)}字）")
            return summary
            
        except Exception as e:
            _logger.error(f"生成第{chapter_id}章摘要失败: {e}")
            return ChapterSummary(
                chapter_id=chapter_id,
                summary="(摘要生成失败)",
                word_count=len(chapter_text),
            )
    
    def add_chapter_summary(self, summary: ChapterSummary):
        """手动添加章节摘要"""
        self.chapter_summaries.append(summary)
        _logger.info(f"添加第{summary.chapter_id}章摘要")
    
    def generate_act_summary(self, act_id: int, act_name: str, 
                            chapter_range: tuple) -> ActSummary:
        """
        生成幕摘要（合并多章摘要）
        
        Args:
            act_id: 幕编号
            act_name: 幕名称
            chapter_range: 章节范围 (start, end)
        
        Returns:
            幕摘要对象
        """
        start, end = chapter_range
        
        # 收集该幕所有章节摘要
        act_chapters = [
            s for s in self.chapter_summaries
            if start <= s.chapter_id <= end
        ]
        
        if not act_chapters:
            return ActSummary(act_id, act_name, "(无章节摘要)", chapter_range)
        
        if self.llm:
            # 使用 LLM 合并摘要
            summaries_text = "\n\n".join([
                f"第{s.chapter_id}章摘要：{s.summary}"
                for s in act_chapters
            ])
            
            prompt = f"""请将以下多个章节摘要合并为一份{act_name}的总体摘要（500字以内）。

要求：
1. 保留关键情节线索和转折点
2. 体现情节发展的脉络
3. 突出主要角色的变化

各章摘要：
{summaries_text}

请输出合并后的摘要文本："""
            
            try:
                merged = self.llm.chat(
                    prompt=prompt,
                    system_prompt="你是一个专业的小说编辑，擅长合并和提炼故事摘要。",
                    max_tokens=2000,
                    temperature=0.3,
                )
                act_summary = ActSummary(act_id, act_name, merged, chapter_range)
            except Exception as e:
                _logger.error(f"生成第{act_id}幕摘要失败: {e}")
                # 降级：直接拼接
                merged = "；".join([s.summary for s in act_chapters])
                act_summary = ActSummary(act_id, act_name, merged, chapter_range)
        else:
            # 无 LLM，直接拼接
            merged = "；".join([s.summary for s in act_chapters])
            act_summary = ActSummary(act_id, act_name, merged, chapter_range)
        
        self.act_summaries.append(act_summary)
        _logger.info(f"第{act_id}幕摘要已生成（{len(act_summary.summary)}字）")
        return act_summary
    
    def update_book_summary(self):
        """更新全书摘要"""
        if not self.act_summaries:
            self.book_summary = "；".join([s.summary for s in self.chapter_summaries[:5]])
            return
        
        if self.llm and len(self.act_summaries) > 1:
            acts_text = "\n\n".join([
                f"{a.act_name}：{a.summary}" for a in self.act_summaries
            ])
            
            prompt = f"""请将以下各幕摘要合并为一份全书摘要（500字以内）。

各幕摘要：
{acts_text}

请输出全书摘要："""
            
            try:
                self.book_summary = self.llm.chat(
                    prompt=prompt,
                    system_prompt="你是一个专业的小说编辑。请只输出摘要文本。",
                    max_tokens=2000,
                    temperature=0.3,
                )
            except Exception as e:
                _logger.error(f"更新全书摘要失败: {e}")
                self.book_summary = "；".join([a.summary for a in self.act_summaries])
        else:
            self.book_summary = "；".join([a.summary for a in self.act_summaries])
        
        _logger.info(f"全书摘要已更新（{len(self.book_summary)}字）")
    
    def get_sliding_window(self, current_chapter: int, window_size: int = 3) -> List[ChapterSummary]:
        """
        获取滑动窗口内的章节摘要
        
        Args:
            current_chapter: 当前章节
            window_size: 窗口大小（默认3章）
        
        Returns:
            窗口内的章节摘要列表
        """
        start = max(1, current_chapter - window_size)
        return [
            s for s in self.chapter_summaries
            if start <= s.chapter_id < current_chapter
        ]
    
    def get_last_chapter_ending(self, current_chapter: int, max_chars: int = 500) -> str:
        """
        获取上一章的结尾文本
        
        Args:
            current_chapter: 当前章节
            max_chars: 最大字符数
        
        Returns:
            上一章结尾文本
        """
        prev = [s for s in self.chapter_summaries if s.chapter_id == current_chapter - 1]
        if prev:
            text = prev[0].last_paragraph
            return text[:max_chars] if len(text) > max_chars else text
        return ""
    
    def assemble_context(self, current_chapter: int, 
                        window_size: int = 3) -> Dict[str, str]:
        """
        组装写作上下文
        
        Args:
            current_chapter: 当前章节
            window_size: 滑动窗口大小
        
        Returns:
            上下文字典
        """
        # 全书摘要
        book_summary = self.book_summary or "(暂无全书摘要)"
        
        # 当前幕摘要
        current_act_summary = ""
        for act in self.act_summaries:
            start, end = act.chapter_range
            if start <= current_chapter <= end:
                current_act_summary = act.summary
                break
        
        # 滑动窗口摘要
        window = self.get_sliding_window(current_chapter, window_size)
        window_text = "\n".join([
            f"第{s.chapter_id}章：{s.summary}" for s in window
        ]) if window else "(前面章节暂无摘要)"
        
        # 上一章结尾
        last_ending = self.get_last_chapter_ending(current_chapter)
        
        return {
            "book_summary": book_summary,
            "current_act_summary": current_act_summary or "(暂无当前幕摘要)",
            "previous_summaries": window_text,
            "last_chapter_ending": last_ending or "(这是第一章，没有前文)",
        }
    
    def get_context_prompt(self, current_chapter: int, window_size: int = 3) -> str:
        """
        获取上下文提示词
        
        Args:
            current_chapter: 当前章节
            window_size: 滑动窗口大小
        
        Returns:
            格式化的上下文文本
        """
        ctx = self.assemble_context(current_chapter, window_size)
        
        lines = [
            "## 前情提要",
            "",
            "### 全书概要",
            ctx["book_summary"],
            "",
        ]
        
        if ctx["current_act_summary"]:
            lines.extend([
                "### 当前幕进展",
                ctx["current_act_summary"],
                "",
            ])
        
        lines.extend([
            "### 最近章节",
            ctx["previous_summaries"],
            "",
        ])
        
        if ctx["last_chapter_ending"]:
            lines.extend([
                "### 上一章结尾",
                ctx["last_chapter_ending"],
                "",
            ])
        
        return "\n".join(lines)
    
    def save(self):
        """保存状态到文件"""
        state = {
            "chapter_summaries": [s.to_dict() for s in self.chapter_summaries],
            "act_summaries": [a.to_dict() for a in self.act_summaries],
            "book_summary": self.book_summary,
        }
        
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        
        _logger.info(f"摘要数据已保存到: {self.state_file}")
    
    def load(self):
        """从文件加载状态"""
        if not os.path.exists(self.state_file):
            _logger.warning(f"摘要文件不存在: {self.state_file}")
            return
        
        with open(self.state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
        
        self.chapter_summaries = [
            ChapterSummary.from_dict(s) 
            for s in state.get("chapter_summaries", [])
        ]
        self.act_summaries = [
            ActSummary.from_dict(a) 
            for a in state.get("act_summaries", [])
        ]
        self.book_summary = state.get("book_summary", "")
        
        _logger.info(
            f"摘要数据已从文件加载: "
            f"{len(self.chapter_summaries)} 章摘要, "
            f"{len(self.act_summaries)} 幕摘要"
        )
