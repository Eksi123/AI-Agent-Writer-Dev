"""
审校编辑 Agent
负责对章节进行质量评审和修改建议
"""
import os
from typing import Optional

from core.agent_llm import AgentLLM, create_agent_llm, create_langchain_llm
from core.chains.review_chain import ReviewChain
from core.chains.consistency_chain import ConsistencyChain
from core.models.chapter_outline import ChapterOutline
from core.models.review_report import ReviewReport
from core.logger import Logger


_logger = Logger("review_editor")


class ReviewEditorAgent:
    """
    审校编辑 Agent
    
    职责：
    - 对章节进行多维度评分
    - 检查一致性问题
    - 提供修改建议
    - 判断是否通过审校
    """
    
    def __init__(self, llm: AgentLLM = None, project_dir: str = None):
        """
        初始化审校编辑
        
        Args:
            llm: LLM 客户端
            project_dir: 项目输出目录
        """
        self.llm = llm or create_agent_llm()
        self.project_dir = project_dir
        
        # 创建 LangChain 兼容的 LLM
        self.lc_llm = create_langchain_llm()
        self.review_chain = ReviewChain(self.lc_llm)
        self.consistency_chain = ConsistencyChain(self.lc_llm)
        
        _logger.info("审校编辑 Agent 初始化完成")
    
    def review_chapter(self, chapter_text: str, outline: ChapterOutline,
                      character_sheets: str, style_guide: str = "",
                      previous_context: str = "",
                      existing_settings: str = "",
                      revision_count: int = 0) -> ReviewReport:
        """
        审校章节
        
        Args:
            chapter_text: 章节正文
            outline: 章节大纲
            character_sheets: 角色卡片
            style_guide: 风格指南
            previous_context: 前情提要
            existing_settings: 已有设定（用于一致性检查）
            revision_count: 当前修改轮次
        
        Returns:
            ReviewReport 对象
        """
        _logger.info(f"开始审校第{outline.chapter_id}章")
        
        # 1. 质量评审
        review_report = self.review_chain.review_chapter(
            chapter_text=chapter_text,
            outline=outline,
            character_sheets=character_sheets,
            style_guide=style_guide,
            previous_context=previous_context,
            revision_count=revision_count,
        )
        
        # 2. 一致性检查
        if existing_settings:
            consistency_result = self.consistency_chain.check_consistency(
                new_content=chapter_text,
                existing_settings=existing_settings,
                character_sheets=character_sheets,
                previous_summaries=previous_context,
            )
            
            # 如果发现一致性问题，添加到报告中
            if not consistency_result["consistent"]:
                from core.models.review_report import ReviewIssue
                for issue in consistency_result["issues"]:
                    review_report.add_issue(
                        category="一致性",
                        severity="高",
                        description=issue.get("description", ""),
                        suggestion=issue.get("suggestion", ""),
                    )
                # 有严重一致性问题时，不通过
                if any(i["type"] in ["角色", "设定"] for i in consistency_result["issues"]):
                    review_report.passed = False
        
        # 保存审校报告
        if self.project_dir:
            self._save_review_report(outline.chapter_id, review_report)
        
        _logger.info(
            f"第{outline.chapter_id}章审校完成: "
            f"总分 {review_report.scores.total_score}/10, "
            f"{'通过' if review_report.passed else '未通过'}"
        )
        
        return review_report
    
    def _save_review_report(self, chapter_id: int, report: ReviewReport):
        """保存审校报告"""
        reviews_dir = os.path.join(self.project_dir, "reviews")
        os.makedirs(reviews_dir, exist_ok=True)
        
        filename = f"review_chapter_{chapter_id:03d}_round_{report.revision_count}.json"
        filepath = os.path.join(reviews_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))
        
        _logger.debug(f"审校报告已保存: {filepath}")
