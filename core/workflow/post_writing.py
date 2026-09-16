"""
写作后审查器 (Post-Writing Reviewer)

在章节生成完成后审查：
1. 是否按照大纲设计的剧情写作
2. 小说剧情本身是否合理
3. 与前 3 章（或已有章节）的剧情衔接是否合理

存在严重问题时触发重新生成（最多 3 次）。
"""
from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from core.config_manager import config_manager
from core.prompts import get_prompt, POST_WRITING_PROMPT
from core.agent_logger import logger


class PostWritingReviewer:
    """写作后审查器，审查生成的章节是否符合大纲、剧情合理、与前文衔接。"""
    
    def __init__(self):
        """初始化写作后审查器"""
        config = config_manager.get_llm_config()
        robustness_config = config_manager.get_robustness_config()
        
        # 使用较低温度保证审查的严谨性，加入超时控制
        self.llm = ChatOpenAI(
            api_key=config["api_key"],
            base_url=config["api_url"],
            model=config["model_name"],
            temperature=config.get("temperature", 0.3),
            max_tokens=8192,
            timeout=robustness_config['request_timeout']
        )
        
        self._max_retries = robustness_config['max_retries']
        self._retry_base_delay = robustness_config['retry_base_delay']
        
        logger.debug("写作后审查器已初始化")
    
    def review(self, chapter_content: str, outline_section: str, 
               previous_chapters: List[str]) -> dict:
        """
        写作后审查
        
        Args:
            chapter_content: 生成的章节内容
            outline_section: 对应的大纲片段
            previous_chapters: 前 3 章（或已有章节）的内容列表
        
        Returns:
            审查结果字典：
            {
                "passed": bool,               # 审查是否通过
                "issues": list,               # 发现的问题
                "should_regenerate": bool,    # 是否需要重新生成
                "feedback": str               # 详细反馈
            }
        """
        review_prompt = self._build_review_prompt(chapter_content, outline_section, previous_chapters)
        
        messages = [
            SystemMessage(content=get_prompt(POST_WRITING_PROMPT)),
            HumanMessage(content=review_prompt)
        ]
        
        # 带重试机制的 LLM 调用
        response = self._invoke_with_retry(messages)
        feedback = response.content
        
        result = self._parse_review_result(feedback)
        
        logger.debug(f"写作后审查完成: {'通过' if result['passed'] else '需要重新生成'}")
        
        return result
    
    def _invoke_with_retry(self, messages: list):
        """
        带重试机制的 LLM 调用
        
        重试策略：
        - 仅对 ConnectionError 和 TimeoutError 重试
        - 认证错误（401）和其他异常不重试，直接抛出
        """
        @retry(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=self._retry_base_delay, max=60),
            retry=retry_if_exception_type((ConnectionError, TimeoutError)),
            reraise=True
        )
        def _invoke():
            return self.llm.invoke(messages)
        return _invoke()
    
    def _build_review_prompt(self, chapter_content: str, outline_section: str, 
                             previous_chapters: List[str]) -> str:
        """构建审查提示"""
        prompt_parts = ["请审查以下章节是否符合大纲设计、剧情合理、与前文衔接自然。\n\n"]
        
        # 添加大纲片段
        prompt_parts.append(f"【对应大纲】\n{outline_section}\n")
        
        # 添加前 3 章内容，每章截取前 1500 字符避免超出 token 限制
        if previous_chapters:
            prompt_parts.append("\n【前面章节内容（最多前3章）】\n")
            for i, chapter in enumerate(previous_chapters[:3], 1):
                chapter_preview = chapter[:1500] + "..." if len(chapter) > 1500 else chapter
                prompt_parts.append(f"\n--- 第{i}章 ---\n{chapter_preview}\n")
        
        # 添加当前章节内容
        prompt_parts.append(f"\n\n【当前章节内容】\n{chapter_content}\n")
        
        return '\n'.join(prompt_parts)
    
    def _parse_review_result(self, feedback: str) -> dict:
        """
        解析审查结果：通过关键词判断是否通过，提取问题列表，判断是否需要重新生成。
        """
        passed = "通过" in feedback and "需要重新生成" not in feedback
        
        # 判断是否需要重新生成（存在严重问题时）
        should_regenerate = not passed and ("严重问题" in feedback or "重新生成" in feedback)
        
        # 提取问题列表
        issues = []
        if "问题" in feedback:
            lines = feedback.split('\n')
            in_issues_section = False
            for line in lines:
                if "问题" in line and ("发现" in line or "存在" in line):
                    in_issues_section = True
                    continue
                if in_issues_section and (line.strip().startswith('-') or line.strip().startswith('•')):
                    issues.append(line.strip())
                elif in_issues_section and line.strip() and not line.strip().startswith('-'):
                    if "建议" in line or "修改" in line or "重新生成" in line:
                        break
        
        return {
            "passed": passed,
            "issues": issues,
            "should_regenerate": should_regenerate,
            "feedback": feedback
        }
