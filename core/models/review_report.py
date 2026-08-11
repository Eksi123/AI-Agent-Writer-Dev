"""
审校报告模型
定义章节审校的评分和修改建议
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class ReviewScore(BaseModel):
    """审校评分"""
    plot_progression: float = Field(0, description="情节推进评分（0-10）", ge=0, le=10)
    character_performance: float = Field(0, description="角色表现评分（0-10）", ge=0, le=10)
    dialogue_quality: float = Field(0, description="对话质量评分（0-10）", ge=0, le=10)
    writing_style: float = Field(0, description="文笔风格评分（0-10）", ge=0, le=10)
    pacing_tension: float = Field(0, description="节奏张力评分（0-10）", ge=0, le=10)
    
    @property
    def total_score(self) -> float:
        """计算总分（加权平均）"""
        weights = {
            "plot_progression": 0.25,
            "character_performance": 0.25,
            "dialogue_quality": 0.20,
            "writing_style": 0.15,
            "pacing_tension": 0.15,
        }
        
        total = (
            self.plot_progression * weights["plot_progression"] +
            self.character_performance * weights["character_performance"] +
            self.dialogue_quality * weights["dialogue_quality"] +
            self.writing_style * weights["writing_style"] +
            self.pacing_tension * weights["pacing_tension"]
        )
        return round(total, 2)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "plot_progression": self.plot_progression,
            "character_performance": self.character_performance,
            "dialogue_quality": self.dialogue_quality,
            "writing_style": self.writing_style,
            "pacing_tension": self.pacing_tension,
            "total_score": self.total_score,
        }


class ReviewIssue(BaseModel):
    """审校发现的问题"""
    category: str = Field(..., description="问题类别（一致性/连贯性/文风/质量/伏笔）")
    severity: str = Field(..., description="严重程度（高/中/低）")
    description: str = Field(..., description="问题描述")
    location: str = Field("", description="问题位置（章节/段落）")
    suggestion: str = Field("", description="修改建议")


class ReviewReport(BaseModel):
    """
    审校报告模型
    包含章节的审校结果和修改建议
    """
    chapter_id: int = Field(..., description="章节编号")
    revision_count: int = Field(0, description="修改轮次")
    
    # 评分
    scores: ReviewScore = Field(default_factory=ReviewScore, description="各项评分")
    
    # 发现的问题
    issues: List[ReviewIssue] = Field(default_factory=list, description="问题列表")
    
    # 总体评价
    overall_comment: str = Field("", description="总体评价")
    
    # 修改建议
    suggestions: List[str] = Field(default_factory=list, description="修改建议列表")
    
    # 是否通过
    passed: bool = Field(False, description="是否通过审校")
    
    @property
    def should_revise(self) -> bool:
        """判断是否需要修改"""
        return not self.passed and self.revision_count < 3
    
    def add_issue(self, category: str, severity: str, description: str, 
                  location: str = "", suggestion: str = ""):
        """添加问题"""
        self.issues.append(ReviewIssue(
            category=category,
            severity=severity,
            description=description,
            location=location,
            suggestion=suggestion,
        ))
    
    def to_prompt_string(self) -> str:
        """转换为提示词格式"""
        lines = [
            f"## 第{self.chapter_id}章审校报告（第{self.revision_count}轮）",
            "",
            "### 评分",
            f"- 情节推进：{self.scores.plot_progression}/10",
            f"- 角色表现：{self.scores.character_performance}/10",
            f"- 对话质量：{self.scores.dialogue_quality}/10",
            f"- 文笔风格：{self.scores.writing_style}/10",
            f"- 节奏张力：{self.scores.pacing_tension}/10",
            f"- **总分：{self.scores.total_score}/10**",
            "",
        ]
        
        if self.issues:
            lines.append("### 发现的问题")
            for issue in self.issues:
                lines.append(f"#### [{issue.severity}] {issue.category}")
                lines.append(f"问题：{issue.description}")
                if issue.location:
                    lines.append(f"位置：{issue.location}")
                if issue.suggestion:
                    lines.append(f"建议：{issue.suggestion}")
                lines.append("")
        
        if self.suggestions:
            lines.append("### 修改建议")
            for i, suggestion in enumerate(self.suggestions, 1):
                lines.append(f"{i}. {suggestion}")
            lines.append("")
        
        if self.overall_comment:
            lines.append("### 总体评价")
            lines.append(self.overall_comment)
        
        return "\n".join(lines)
