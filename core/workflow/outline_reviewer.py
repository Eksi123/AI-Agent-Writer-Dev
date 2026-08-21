"""
大纲审查器
职责：
- 审查大纲的合理性
- 检查与前文的衔接
- 提供修改建议
"""
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from core.config import config_manager
from core.prompts import get_prompt, OUTLINE_REVIEW_PROMPT
from core.agent_logger import logger


class OutlineReviewer:
    """
    大纲审查器
    负责审查大纲的合理性
    """
    
    def __init__(self):
        """初始化大纲审查器"""
        config = config_manager.get_llm_config()
        
        # 创建 LLM 实例（不需要工具）
        self.llm = ChatOpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"],
            model=config["model"],
            temperature=0.3  # 使用较低温度，保证审查的严谨性
        )
        
        logger.debug("大纲审查器已初始化")
    
    def review(self, outline_section: str, previous_content: str = "") -> dict:
        """
        审查大纲片段
        
        Args:
            outline_section: 要审查的大纲片段
            previous_content: 前文内容（可选，用于检查衔接）
        
        Returns:
            {
                "passed": bool,        # 是否通过审查
                "feedback": str,       # 审查反馈
                "suggestions": list    # 修改建议列表
            }
        """
        # 构建审查提示
        review_prompt = self._build_review_prompt(outline_section, previous_content)
        
        # 调用 LLM 进行审查
        messages = [
            SystemMessage(content=get_prompt(OUTLINE_REVIEW_PROMPT)),
            HumanMessage(content=review_prompt)
        ]
        
        response = self.llm.invoke(messages)
        feedback = response.content
        
        # 解析审查结果
        result = self._parse_review_result(feedback)
        
        logger.debug(f"大纲审查完成: {'通过' if result['passed'] else '需要修改'}")
        
        return result
    
    def _build_review_prompt(self, outline_section: str, previous_content: str) -> str:
        """构建审查提示"""
        prompt_parts = ["请审查以下大纲片段：\n\n"]
        prompt_parts.append(f"【大纲片段】\n{outline_section}\n")
        
        if previous_content:
            prompt_parts.append(f"\n【前文内容】\n{previous_content[:2000]}...\n")
            prompt_parts.append("\n请特别注意与前文的衔接是否自然。")
        
        return '\n'.join(prompt_parts)
    
    def _parse_review_result(self, feedback: str) -> dict:
        """
        解析审查结果
        
        Returns:
            {
                "passed": bool,
                "feedback": str,
                "suggestions": list
            }
        """
        # 简单的判断逻辑：如果包含"通过"则认为通过
        passed = "通过" in feedback and "需要修改" not in feedback
        
        # 提取建议（如果有的话）
        suggestions = []
        if "建议" in feedback:
            # 简单的文本提取，实际可以更复杂
            lines = feedback.split('\n')
            for line in lines:
                if line.strip().startswith('-') or line.strip().startswith('•'):
                    suggestions.append(line.strip())
        
        return {
            "passed": passed,
            "feedback": feedback,
            "suggestions": suggestions
        }


if __name__ == '__main__':
    # 测试代码
    reviewer = OutlineReviewer()
    
    test_outline = """
    ## 第1章：初入江湖
    
    主角李明是一个普通的大学生，意外获得了一本武功秘籍。
    他决定离开家乡，踏入江湖。在途中遇到了第一位伙伴。
    """
    
    result = reviewer.review(test_outline)
    print(f"审查结果: {'通过' if result['passed'] else '需要修改'}")
    print(f"反馈:\n{result['feedback']}")
