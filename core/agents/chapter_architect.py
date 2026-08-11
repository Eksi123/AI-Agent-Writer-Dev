"""
分章编剧 Agent
负责将故事蓝图拆解为详细的章节大纲
"""
import json
import os
from typing import List

from core.agent_llm import AgentLLM, create_agent_llm, create_langchain_llm
from core.chains.outline_chain import OutlineChain
from core.models.story_blueprint import StoryBlueprint
from core.models.chapter_outline import ChapterOutline
from core.logger import Logger


_logger = Logger("chapter_architect")


class ChapterArchitectAgent:
    """
    分章编剧 Agent
    
    职责：
    - 将蓝图拆解为章节大纲
    - 设计每章的场景、冲突、转折
    - 管理伏笔和线索布局
    """
    
    def __init__(self, llm: AgentLLM = None, project_dir: str = None):
        """
        初始化分章编剧
        
        Args:
            llm: LLM 客户端
            project_dir: 项目输出目录
        """
        self.llm = llm or create_agent_llm()
        self.project_dir = project_dir
        
        # 创建 LangChain 兼容的 LLM
        self.lc_llm = create_langchain_llm()
        self.outline_chain = OutlineChain(self.lc_llm)
        
        _logger.info("分章编剧 Agent 初始化完成")
    
    def generate_all_outlines(self, blueprint: StoryBlueprint,
                             previous_summaries: str = "",
                             plot_tracking: str = "",
                             word_count_per_chapter: int = 5000) -> List[ChapterOutline]:
        """
        生成所有章节大纲
        
        Args:
            blueprint: 故事蓝图
            previous_summaries: 前情摘要（用于续写）
            plot_tracking: 情节追踪信息
            word_count_per_chapter: 每章目标字数
        
        Returns:
            章节大纲列表
        """
        # 计算总章节数
        total_chapters = sum(a.chapters[1] - a.chapters[0] + 1 for a in blueprint.acts)
        
        _logger.info(f"开始生成 {total_chapters} 章的大纲")
        
        outlines = []
        
        for chapter_id in range(1, total_chapters + 1):
            outline = self.generate_chapter_outline(
                chapter_id=chapter_id,
                blueprint=blueprint,
                previous_summaries=previous_summaries,
                plot_tracking=plot_tracking,
                word_count_target=word_count_per_chapter,
            )
            outlines.append(outline)
            
            # 保存单章大纲
            if self.project_dir:
                self._save_outline(outline)
        
        _logger.info(f"所有章节大纲生成完成，共 {len(outlines)} 章")
        return outlines
    
    def generate_chapter_outline(self, chapter_id: int, blueprint: StoryBlueprint,
                                previous_summaries: str = "",
                                plot_tracking: str = "",
                                word_count_target: int = 5000) -> ChapterOutline:
        """
        生成单章大纲
        
        Args:
            chapter_id: 章节编号
            blueprint: 故事蓝图
            previous_summaries: 前情摘要
            plot_tracking: 情节追踪
            word_count_target: 目标字数
        
        Returns:
            ChapterOutline 对象
        """
        _logger.info(f"开始生成第{chapter_id}章大纲")
        
        outline = self.outline_chain.generate_chapter_outline(
            chapter_id=chapter_id,
            blueprint=blueprint,
            previous_summaries=previous_summaries,
            plot_tracking=plot_tracking,
            word_count_target=word_count_target,
        )
        
        _logger.info(f"第{chapter_id}章大纲生成完成: 《{outline.title}》")
        return outline
    
    def refine_outline(self, outline: ChapterOutline, blueprint: StoryBlueprint,
                       feedback: str) -> ChapterOutline:
        """
        根据反馈优化大纲
        
        Args:
            outline: 当前大纲
            blueprint: 故事蓝图
            feedback: 用户反馈
        
        Returns:
            优化后的大纲
        """
        _logger.info(f"根据反馈优化第{outline.chapter_id}章大纲")
        
        prompt = f"""请根据用户反馈修改章节大纲。

## 故事蓝图
{blueprint.to_prompt_string()}

## 当前大纲
{outline.to_prompt_string()}

## 用户反馈
{feedback}

请输出修改后的完整章节大纲（JSON 格式）。"""
        
        response = self.llm.chat(
            prompt=prompt,
            system_prompt="你是专业的小说编剧。请根据反馈优化大纲，保持 JSON 格式。",
            max_tokens=4000,
            temperature=0.5,
        )
        
        # 解析新大纲
        try:
            import re
            from core.models.chapter_outline import Scene
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                scenes = [Scene(**s) for s in data.get("scenes", [])]
                
                new_outline = ChapterOutline(
                    chapter_id=data.get("chapter_id", outline.chapter_id),
                    title=data.get("title", outline.title),
                    act=data.get("act", outline.act),
                    pov_character=data.get("pov_character", outline.pov_character),
                    timeline=data.get("timeline", outline.timeline),
                    location=data.get("location", outline.location),
                    scenes=scenes,
                    foreshadowing=data.get("foreshadowing", outline.foreshadowing),
                    chapter_hook=data.get("chapter_hook", outline.chapter_hook),
                    word_count_target=data.get("word_count_target", outline.word_count_target),
                    emotional_arc=data.get("emotional_arc", outline.emotional_arc),
                    previous_chapter_connection=data.get("previous_chapter_connection", ""),
                    next_chapter_setup=data.get("next_chapter_setup", ""),
                )
                
                if self.project_dir:
                    self._save_outline(new_outline)
                
                _logger.info(f"第{outline.chapter_id}章大纲优化完成")
                return new_outline
        except Exception as e:
            _logger.error(f"解析优化后的大纲失败: {e}")
        
        _logger.warning("大纲优化失败，返回原大纲")
        return outline
    
    def _save_outline(self, outline: ChapterOutline):
        """保存大纲到文件"""
        outlines_dir = os.path.join(self.project_dir, "outlines")
        os.makedirs(outlines_dir, exist_ok=True)
        
        filepath = os.path.join(outlines_dir, f"chapter_{outline.chapter_id:03d}.json")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(outline.model_dump_json(indent=2))
        
        _logger.debug(f"大纲已保存: {filepath}")
