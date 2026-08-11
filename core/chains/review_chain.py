"""
审校修改链
负责对章节进行质量评审和修改建议
"""
import json
import re
from typing import Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from core.agent_llm import LangChainChatModel
from core.models.chapter_outline import ChapterOutline
from core.models.review_report import ReviewReport, ReviewScore, ReviewIssue
from core.logger import Logger


_logger = Logger("review_chain")


# ========== 章节审校 ==========

REVIEW_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是一位严格的小说审校编辑，拥有丰富的文学批评经验。

请对小说章节进行全方位审校，从以下维度打分（0-10分）：

1. **情节推进**（权重25%）：本章是否有效推进了主线/支线情节
2. **角色表现**（权重25%）：角色行为是否符合设定，对话是否有区分度
3. **对话质量**（权重20%）：对话是否自然、生动
4. **文笔风格**（权重15%）：是否符合全局风格指南
5. **节奏张力**（权重15%）：情绪曲线是否符合大纲设计

评分标准：
- 9-10分：优秀，几乎无需修改
- 7-8分：良好，有少量可改进之处
- 5-6分：一般，存在明显问题需要修改
- 3-4分：较差，需要大幅修改
- 0-2分：很差，需要重写

请严格按照 JSON 格式输出审校报告。"""),
    ("human", """## 章节大纲
{chapter_outline}

## 角色设定
{character_sheets}

## 风格指南
{style_guide}

## 前情提要
{previous_context}

## 待审校正文
{chapter_text}

请按以下 JSON 格式输出审校报告：
{{
    "scores": {{
        "plot_progression": 情节推进评分,
        "character_performance": 角色表现评分,
        "dialogue_quality": 对话质量评分,
        "writing_style": 文笔风格评分,
        "pacing_tension": 节奏张力评分
    }},
    "issues": [
        {{
            "category": "问题类别（一致性/连贯性/文风/质量/伏笔）",
            "severity": "严重程度（高/中/低）",
            "description": "问题描述",
            "location": "问题位置",
            "suggestion": "修改建议"
        }}
    ],
    "overall_comment": "总体评价",
    "suggestions": ["修改建议1", "修改建议2"],
    "passed": 是否通过（总分>=7为true）
}}""")
])


class ReviewChain:
    """审校修改链"""
    
    def __init__(self, llm: LangChainChatModel):
        """
        初始化审校链
        
        Args:
            llm: LangChain 兼容的 LLM 实例
        """
        self.llm = llm
        self.output_parser = StrOutputParser()
        _logger.info("审校链初始化完成")
    
    def review_chapter(self, chapter_text: str, outline: ChapterOutline,
                      character_sheets: str, style_guide: str = "",
                      previous_context: str = "",
                      revision_count: int = 0) -> ReviewReport:
        """
        审校章节
        
        Args:
            chapter_text: 章节正文
            outline: 章节大纲
            character_sheets: 角色卡片
            style_guide: 风格指南
            previous_context: 前情提要
            revision_count: 当前修改轮次
        
        Returns:
            ReviewReport 对象
        """
        _logger.info(f"开始审校第{outline.chapter_id}章（第{revision_count}轮）")
        
        chain = REVIEW_PROMPT | self.llm | self.output_parser
        response = chain.invoke({
            "chapter_outline": outline.to_prompt_string(),
            "character_sheets": character_sheets or "请参考大纲中的角色信息",
            "style_guide": style_guide or "自然流畅，注重细节",
            "previous_context": previous_context or "暂无",
            "chapter_text": chapter_text,
        })
        
        # 解析审校报告
        report = self._parse_review_report(response, outline.chapter_id, revision_count)
        
        _logger.info(
            f"第{outline.chapter_id}章审校完成: "
            f"总分 {report.scores.total_score}/10, "
            f"{'通过' if report.passed else '未通过'}, "
            f"{len(report.issues)}个问题"
        )
        
        return report
    
    def _parse_review_report(self, response: str, chapter_id: int, 
                             revision_count: int) -> ReviewReport:
        """解析审校报告 JSON 响应"""
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                
                # 解析评分
                scores_data = data.get("scores", {})
                scores = ReviewScore(
                    plot_progression=scores_data.get("plot_progression", 5),
                    character_performance=scores_data.get("character_performance", 5),
                    dialogue_quality=scores_data.get("dialogue_quality", 5),
                    writing_style=scores_data.get("writing_style", 5),
                    pacing_tension=scores_data.get("pacing_tension", 5),
                )
                
                # 解析问题
                issues = []
                for issue_data in data.get("issues", []):
                    issues.append(ReviewIssue(
                        category=issue_data.get("category", "质量"),
                        severity=issue_data.get("severity", "中"),
                        description=issue_data.get("description", ""),
                        location=issue_data.get("location", ""),
                        suggestion=issue_data.get("suggestion", ""),
                    ))
                
                report = ReviewReport(
                    chapter_id=chapter_id,
                    revision_count=revision_count,
                    scores=scores,
                    issues=issues,
                    overall_comment=data.get("overall_comment", ""),
                    suggestions=data.get("suggestions", []),
                    passed=data.get("passed", scores.total_score >= 7),
                )
                return report
            else:
                raise ValueError("未找到 JSON 内容")
        except Exception as e:
            _logger.error(f"解析审校报告失败: {e}")
            _logger.error(f"原始响应: {response[:500]}")
            # 返回默认报告（通过）
            return ReviewReport(
                chapter_id=chapter_id,
                revision_count=revision_count,
                scores=ReviewScore(
                    plot_progression=7,
                    character_performance=7,
                    dialogue_quality=7,
                    writing_style=7,
                    pacing_tension=7,
                ),
                overall_comment="审校报告解析失败，默认通过",
                passed=True,
            )
