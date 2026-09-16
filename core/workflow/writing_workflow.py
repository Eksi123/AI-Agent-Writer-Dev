"""
写作工作流控制器

协调完整的单章写作流程：写作前审查 → 章节写作 → 写作后审查（最多3次重试）→ 保存文件。
每个步骤由独立的审查器或 Agent 执行，工作流负责编排和状态管理。
"""
import time
from typing import Optional, List
from core.agents.novel_writer import NovelWriter
from core.workflow.pre_writing import PreWritingReviewer
from core.workflow.post_writing import PostWritingReviewer
from core.config_manager import config_manager
from core.validators import validate_volume_chapter, validate_user_request
from core.agent_logger import logger


class WritingWorkflow:
    """写作工作流控制器，协调写作前审查、章节写作和写作后审查三个阶段。"""
    
    def __init__(self, writer: NovelWriter, max_retries: int = 3):
        """
        初始化写作工作流
        
        Args:
            writer: NovelWriter 实例
            max_retries: post_writing 审查失败后的最大重试次数，默认 3 次
        """
        self.writer = writer
        self.pre_writing_reviewer = PreWritingReviewer()
        self.post_writing_reviewer = PostWritingReviewer()
        self.max_retries = max_retries
        
        self.current_volume = 1
        self.current_chapter = 1
        
        # 读取工作流超时配置
        robustness_config = config_manager.get_robustness_config()
        self.workflow_timeout = robustness_config['workflow_timeout']
        
        logger.info(f"写作工作流已初始化（最大重试次数: {max_retries}，工作流超时: {self.workflow_timeout}秒）")
    
    def write_chapter(self, volume: int, chapter: int, chapter_name: str = "", 
                     user_request: str = "") -> dict:
        """
        执行单章写作工作流
        
        流程：
        1. 写作前审查 - 理解用户要求，匹配大纲章节，审查大纲质量
        2. 章节写作 - 基于大纲完成写作
        3. 写作后审查 - 审查章节是否符合大纲、剧情合理、与前文衔接（最多重试3次）
        4. 保存文件 - 审查通过后保存章节到文件
        
        Args:
            volume: 卷号
            chapter: 章节号
            chapter_name: 章节名
            user_request: 用户的写作要求（可选，用于 pre_writing 审查）
        
        Returns:
            {
                "success": bool,              # 是否成功完成
                "chapter_content": str,       # 章节内容
                "pre_writing_review": dict,   # 写作前审查结果
                "post_writing_review": dict,  # 写作后审查结果
                "write_to_file": bool,        # 是否写入文件
                "retry_count": int,           # 重试次数
                "free_writing": bool          # 是否为自由写作模式
            }
        """
        logger.info(f"开始写作: 第{volume}卷 第{chapter}章")
        
        # 参数校验
        valid, error_msg = validate_volume_chapter(volume, chapter)
        if not valid:
            logger.error(f"参数校验失败: {error_msg}")
            return {
                "success": False,
                "chapter_content": "",
                "pre_writing_review": None,
                "post_writing_review": None,
                "write_to_file": False,
                "retry_count": 0,
                "free_writing": False,
                "error": error_msg
            }
        
        if user_request:
            valid, error_msg = validate_user_request(user_request)
            if not valid:
                logger.error(f"参数校验失败: {error_msg}")
                return {
                    "success": False,
                    "chapter_content": "",
                    "pre_writing_review": None,
                    "post_writing_review": None,
                    "write_to_file": False,
                    "retry_count": 0,
                    "free_writing": False,
                    "error": error_msg
                }
        
        # 记录工作流开始时间，用于超时检查
        workflow_start_time = time.time()
        
        result = {
            "success": False,
            "chapter_content": "",
            "pre_writing_review": None,
            "post_writing_review": None,
            "write_to_file": True,
            "retry_count": 0,
            "free_writing": False
        }
        
        # Step 1: 写作前审查
        logger.info("Step 1: 写作前审查")
        outline = self._get_full_outline()
        previous_content = self._get_previous_content()
        
        # 如果没有提供用户要求，使用默认格式
        if not user_request:
            user_request = f"基于大纲第{volume}卷第{chapter}章生成小说"
        
        pre_writing_review = self.pre_writing_reviewer.review(user_request, outline, previous_content)
        result["pre_writing_review"] = pre_writing_review
        
        # 判断是否为自由写作模式
        if not pre_writing_review["matched"]:
            logger.warning("自由写作模式：内容将只在对话框输出，不写入文件")
            result["free_writing"] = True
            result["write_to_file"] = False
            
            # 自由写作：生成内容但不保存
            chapter_content = self._write_free_content(user_request)
            result["chapter_content"] = chapter_content
            result["success"] = True
            return result
        
        # 匹配成功但审查未通过
        if not pre_writing_review["passed"]:
            logger.warning("大纲审查未通过，建议用户修改大纲")
            result["success"] = False
            return result
        
        # 使用审查器提取的大纲片段（如果有），否则使用默认提取
        outline_section = pre_writing_review.get("outline_section") or self._extract_outline_section(volume, chapter)
        
        # 工作流超时检查
        elapsed = time.time() - workflow_start_time
        if elapsed > self.workflow_timeout:
            logger.error(f"工作流超时: 写作前审查阶段已耗时 {elapsed:.1f}秒（限制: {self.workflow_timeout}秒）")
            result["success"] = False
            result["error"] = f"工作流超时（{elapsed:.1f}秒）"
            result["timeout"] = True
            return result
        
        # Step 2: 章节写作（带重试机制）
        logger.info("Step 2: 章节写作")
        chapter_content = self._write_chapter_content(volume, chapter, chapter_name, outline_section)
        result["chapter_content"] = chapter_content
        
        # 工作流超时检查
        elapsed = time.time() - workflow_start_time
        if elapsed > self.workflow_timeout:
            logger.error(f"工作流超时: 章节写作阶段已耗时 {elapsed:.1f}秒（限制: {self.workflow_timeout}秒）")
            result["success"] = False
            result["error"] = f"工作流超时（{elapsed:.1f}秒）"
            result["timeout"] = True
            return result
        
        # Step 3: 写作后审查（最多重试 max_retries 次）
        logger.info("Step 3: 写作后审查")
        previous_chapters = self._get_previous_three_chapters(volume, chapter)
        
        retry_count = 0
        while retry_count < self.max_retries:
            post_writing_review = self.post_writing_reviewer.review(
                chapter_content, outline_section, previous_chapters
            )
            result["post_writing_review"] = post_writing_review
            
            if post_writing_review["passed"]:
                logger.info("写作后审查通过")
                break
            
            if post_writing_review["should_regenerate"]:
                retry_count += 1
                result["retry_count"] = retry_count
                logger.warning(f"写作后审查未通过，第 {retry_count} 次重新生成")
                
                # 重新生成章节
                chapter_content = self._write_chapter_content(volume, chapter, chapter_name, outline_section)
                result["chapter_content"] = chapter_content
            else:
                # 不需要重新生成，标记为成功但有问题
                logger.warning("写作后审查发现问题，但不需要重新生成")
                break
        
        # 如果重试后仍未通过，标记失败
        if retry_count >= self.max_retries and not post_writing_review["passed"]:
            logger.error(f"重试 {self.max_retries} 次后仍未通过审查，标记失败待用户确认")
            result["success"] = False
            result["error"] = f"写作后审查重试 {self.max_retries} 次仍未通过"
            result["last_review_feedback"] = post_writing_review.get("feedback", "")
            return result
        
        # Step 4: 保存文件
        if result["write_to_file"] and self.writer.current_project:
            self.writer.current_project.write_chapter(volume, chapter, chapter_content, chapter_name)
            logger.info(f"章节已保存: 第{volume}卷 第{chapter}章")
        
        result["success"] = True
        logger.info(f"第{volume}卷 第{chapter}章 写作完成（重试次数: {retry_count}）")
        
        # 更新当前进度
        self.current_volume = volume
        self.current_chapter = chapter
        
        return result
    
    def _extract_outline_section(self, volume: int, chapter: int) -> str:
        """
        提取当前章节对应的大纲部分。
        通过匹配 "第X章" 或 "第X卷" 标记定位大纲段落，找不到则返回完整大纲。
        """
        if not self.writer.current_project:
            return ""
        
        outline = self.writer.current_project.read_outline()
        
        lines = outline.split('\n')
        section_lines = []
        in_section = False
        
        for line in lines:
            if f"第{chapter}章" in line or f"第{volume}卷" in line:
                in_section = True
            
            if in_section:
                section_lines.append(line)
                
                # 到达下一章或下一卷时截断
                if len(section_lines) > 1 and (f"第{chapter+1}章" in line or f"第{volume+1}卷" in line):
                    section_lines.pop()  # 移除下一章的标题
                    break
        
        return '\n'.join(section_lines) if section_lines else outline
    
    def _get_previous_content(self) -> str:
        """获取最后一章的内容，作为大纲审查的前文参考"""
        if not self.writer.current_project:
            return ""
        
        chapters = self.writer.current_project.list_chapters()
        
        if not chapters:
            return ""
        
        last_chapter_path = chapters[-1]
        with open(last_chapter_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _write_chapter_content(self, volume: int, chapter: int, 
                               chapter_name: str, outline_section: str) -> str:
        """调用 NovelWriter Agent 根据大纲生成章节内容"""
        # 构建写作提示，要求 3000-5000 字，Markdown 格式
        prompt = f"""请根据以下大纲写第{volume}卷第{chapter}章的内容。

            章节名：{chapter_name}

            大纲：
            {outline_section}

            要求：
            1. 严格按照大纲写作
            2. 字数 3000-5000 字
            3. 保持风格一致
            4. 直接输出正文，使用 Markdown 格式
            """
        
        # 调用写作 Agent，max_iterations=0 表示不限制循环次数
        result = self.writer.chat(prompt, max_iterations=0)
        
        return result['response']
    
    def _get_previous_three_chapters(self, volume: int, chapter: int) -> List[str]:
        """获取前面最多三章的内容，用于写作后审查时比对前文"""
        if not self.writer.current_project:
            return []
        
        chapters = self.writer.current_project.list_chapters()
        contents = []
        
        # 只取最后三章
        for chapter_path in chapters[-3:]:
            with open(chapter_path, 'r', encoding='utf-8') as f:
                contents.append(f.read())
        
        return contents
    
    def _get_full_outline(self) -> str:
        """获取完整大纲内容"""
        if not self.writer.current_project:
            return ""
        
        return self.writer.current_project.read_outline()
    
    def _write_free_content(self, user_request: str) -> str:
        """自由写作模式：生成内容但不写入文件"""
        prompt = f"""请根据用户的要求自由创作：

            用户要求：{user_request}

            要求：
            1. 直接输出正文
            2. 字数 1000-3000 字
            3. 使用 Markdown 格式
            """
        
        result = self.writer.chat(prompt, max_iterations=0)
        return result['response']

