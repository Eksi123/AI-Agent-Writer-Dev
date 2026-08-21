"""
逻辑审查器
职责：
- 审查正文与前面所有章节的逻辑一致性
- 检查情节、角色、时间线等是否矛盾
- 提供修改建议
"""
from typing import Optional, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from core.config import config_manager
from core.prompts import get_prompt, LOGIC_REVIEW_PROMPT
from core.agent_logger import logger


class LogicReviewer:
    """
    逻辑审查器
    负责审查正文的逻辑一致性
    """
    
    def __init__(self):
        """初始化逻辑审查器"""
        config = config_manager.get_llm_config()
        
        # 创建 LLM 实例（不需要工具）
        self.llm = ChatOpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"],
            model=config["model"],
            temperature=0.3  # 使用较低温度，保证审查的严谨性
        )
        
        logger.debug("逻辑审查器已初始化")
    
    def review(self, current_chapter: str, previous_chapters: List[str]) -> dict:
        """
        审查当前章节的逻辑一致性
        
        Args:
            current_chapter: 当前章节内容
            previous_chapters: 前面所有章节的内容列表
        
        Returns:
            {
                "passed": bool,        # 是否通过审查
                "feedback": str,       # 审查反馈
                "issues": list,        # 发现的问题列表
                "suggestions": list    # 修改建议列表
            }
        """
        # 构建审查提示
        review_prompt = self._build_review_prompt(current_chapter, previous_chapters)
        
        # 调用 LLM 进行审查
        messages = [
            SystemMessage(content=get_prompt(LOGIC_REVIEW_PROMPT)),
            HumanMessage(content=review_prompt)
        ]
        
        response = self.llm.invoke(messages)
        feedback = response.content
        
        # 解析审查结果
        result = self._parse_review_result(feedback)
        
        logger.debug(f"逻辑审查完成: {'通过' if result['passed'] else '需要修改'}")
        
        return result
    
    def _build_review_prompt(self, current_chapter: str, previous_chapters: List[str]) -> str:
        """构建审查提示"""
        prompt_parts = ["请审查以下章节与前面所有章节的逻辑一致性：\n\n"]
        
        # 添加前文内容（限制长度，避免超出 token 限制）
        if previous_chapters:
            prompt_parts.append("【前面章节内容】\n")
            for i, chapter in enumerate(previous_chapters, 1):
                # 每章只取前 1000 字符，避免过长
                chapter_preview = chapter[:1000] + "..." if len(chapter) > 1000 else chapter
                prompt_parts.append(f"\n--- 第{i}章 ---\n{chapter_preview}\n")
        
        # 添加当前章节
        prompt_parts.append(f"\n\n【当前章节内容】\n{current_chapter}\n")
        
        return '\n'.join(prompt_parts)
    
    def _parse_review_result(self, feedback: str) -> dict:
        """
        解析审查结果
        
        Returns:
            {
                "passed": bool,
                "feedback": str,
                "issues": list,
                "suggestions": list
            }
        """
        # 简单的判断逻辑
        passed = "通过" in feedback and "需要修改" not in feedback
        
        # 提取问题
        issues = []
        if "问题" in feedback:
            lines = feedback.split('\n')
            in_issues_section = False
            for line in lines:
                if "问题" in line and "发现" in line:
                    in_issues_section = True
                    continue
                if in_issues_section and (line.strip().startswith('-') or line.strip().startswith('•')):
                    issues.append(line.strip())
                elif in_issues_section and line.strip() and not line.strip().startswith('-'):
                    # 遇到新的段落，结束问题部分
                    if "建议" in line or "修改" in line:
                        break
        
        # 提取建议
        suggestions = []
        if "建议" in feedback:
            lines = feedback.split('\n')
            in_suggestions_section = False
            for line in lines:
                if "建议" in line:
                    in_suggestions_section = True
                    continue
                if in_suggestions_section and (line.strip().startswith('-') or line.strip().startswith('•')):
                    suggestions.append(line.strip())
        
        return {
            "passed": passed,
            "feedback": feedback,
            "issues": issues,
            "suggestions": suggestions
        }


if __name__ == '__main__':
    # 测试代码
    reviewer = LogicReviewer()
    
    test_previous = [
        "第1章内容：李明离开了家乡，踏上了江湖之路...",
        "第2章内容：李明遇到了第一位伙伴张伟..."
    ]
    
    test_current = "第3章内容：李明和张伟一起前往京城，在路上遭遇了山贼..."
    
    result = reviewer.review(test_current, test_previous)
    print(f"审查结果: {'通过' if result['passed'] else '需要修改'}")
    print(f"反馈:\n{result['feedback']}")
