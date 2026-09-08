"""
写作前审查器 (Pre-Writing Reviewer)

在写作前理解用户的要求，判断是否与大纲章节对应：
- 匹配成功：审查大纲的剧情衔接（高优先级）、逻辑合理性（中优先级）、刻画丰富度（低优先级）
- 匹配失败：进入自由写作模式，内容只在对话框输出，不写入 output 目录
"""
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from core.config_manager import config_manager
from core.prompts import get_prompt, PRE_WRITING_PROMPT
from core.agent_logger import logger


class PreWritingReviewer:
    """写作前审查器，在写作前审查大纲质量或判断自由写作模式。"""
    
    def __init__(self):
        """初始化写作前审查器"""
        config = config_manager.get_llm_config()
        
        # 使用较低温度保证审查的严谨性
        self.llm = ChatOpenAI(
            api_key=config["api_key"],
            base_url=config["api_url"],
            model=config["model_name"],
            temperature=config.get("temperature", 0.3),
            max_tokens=8192
        )
        
        logger.debug("写作前审查器已初始化")
    
    def review(self, user_request: str, outline: str, previous_content: str = "") -> dict:
        """
        写作前审查
        
        Args:
            user_request: 用户的写作要求
            outline: 完整大纲内容
            previous_content: 前文内容（可选，用于检查衔接）
        
        Returns:
            审查结果字典：
            {
                "matched": bool,           # 是否匹配到大纲章节
                "passed": bool,            # 大纲审查是否通过（matched=true 时有效）
                "matched_chapter": str,    # 匹配到的章节（如"第1卷第2章"）
                "outline_section": str,    # 对应的大纲片段
                "feedback": str,           # 审查反馈
                "suggestions": list,       # 修改建议
                "warning": str,            # 自由写作警告（matched=false 时）
                "write_to_file": bool      # 是否写入文件
            }
        """
        review_prompt = self._build_review_prompt(user_request, outline, previous_content)
        
        messages = [
            SystemMessage(content=get_prompt(PRE_WRITING_PROMPT)),
            HumanMessage(content=review_prompt)
        ]
        
        response = self.llm.invoke(messages)
        feedback = response.content
        
        result = self._parse_review_result(feedback, outline)
        
        if result["matched"]:
            logger.debug(f"写作前审查: 匹配到 {result['matched_chapter']}, {'通过' if result['passed'] else '需要修改'}")
        else:
            logger.debug("写作前审查: 自由写作模式")
        
        return result
    
    def _build_review_prompt(self, user_request: str, outline: str, previous_content: str) -> str:
        """构建审查提示"""
        prompt_parts = ["请分析用户的写作要求，并与大纲进行匹配和审查。\n\n"]
        
        prompt_parts.append(f"【用户写作要求】\n{user_request}\n")
        prompt_parts.append(f"\n【完整大纲】\n{outline}\n")
        
        if previous_content:
            prompt_parts.append(f"\n【前文内容（最后一章）】\n{previous_content[:2000]}...\n")
        
        return '\n'.join(prompt_parts)
    
    def _parse_review_result(self, feedback: str, outline: str) -> dict:
        """
        解析审查结果。
        
        通过关键词判断是否匹配大纲、是否通过审查，提取建议列表。
        """
        # 判断是否匹配到大纲章节
        matched = "匹配成功" in feedback or "匹配到" in feedback
        if not matched:
            # 检查是否有明确的未匹配标记
            if "未匹配" in feedback or "自由写作" in feedback:
                matched = False
            else:
                # 默认尝试匹配
                matched = "第" in feedback and "章" in feedback
        
        if not matched:
            # 自由写作模式
            warning = ""
            if "警告" in feedback or "注意" in feedback:
                lines = feedback.split('\n')
                for line in lines:
                    if "警告" in line or "注意" in line:
                        warning = line.strip()
                        break
            
            return {
                "matched": False,
                "passed": False,
                "matched_chapter": "",
                "outline_section": "",
                "feedback": feedback,
                "suggestions": [],
                "warning": warning or "写作要求未匹配到大纲章节，内容将只在对话框输出，不写入文件",
                "write_to_file": False
            }
        
        # 匹配成功，解析审查结果
        passed = "通过" in feedback and "需要修改" not in feedback
        
        # 提取匹配到的章节
        matched_chapter = ""
        for line in feedback.split('\n'):
            if "匹配章节" in line or "匹配到" in line:
                matched_chapter = line.replace("匹配章节：", "").replace("匹配到：", "").strip()
                break
        
        # 提取大纲片段（如果 LLM 返回了）
        outline_section = ""
        if "大纲片段" in feedback:
            lines = feedback.split('\n')
            in_section = False
            for line in lines:
                if "大纲片段" in line:
                    in_section = True
                    continue
                if in_section:
                    if line.strip().startswith("【") or line.strip().startswith("---"):
                        break
                    outline_section += line + "\n"
        
        # 提取建议列表
        suggestions = []
        if "建议" in feedback:
            lines = feedback.split('\n')
            for line in lines:
                if line.strip().startswith('-') or line.strip().startswith('•'):
                    suggestions.append(line.strip())
        
        return {
            "matched": True,
            "passed": passed,
            "matched_chapter": matched_chapter,
            "outline_section": outline_section.strip(),
            "feedback": feedback,
            "suggestions": suggestions,
            "warning": "",
            "write_to_file": True
        }


if __name__ == '__main__':
    reviewer = PreWritingReviewer()
    
    test_request = "基于大纲第1章生成小说"
    test_outline = """
    # 测试小说
    
    ## 第1卷
    
    ### 第1章：初入江湖
    
    主角李明是一个普通的大学生，意外获得了一本武功秘籍。
    他决定离开家乡，踏入江湖。在途中遇到了第一位伙伴。
    
    ### 第2章：风云际会
    
    李明和伙伴一起前往京城，在路上遭遇了山贼...
    """
    
    result = reviewer.review(test_request, test_outline)
    print(f"匹配: {result['matched']}")
    print(f"通过: {result['passed']}")
    print(f"匹配章节: {result['matched_chapter']}")
    print(f"写入文件: {result['write_to_file']}")
    print(f"反馈:\n{result['feedback']}")
