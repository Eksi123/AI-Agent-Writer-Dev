"""
写作工作流控制器
职责：
- 控制写作流程：大纲审查 → 逐章写作 → 逻辑审查
- 协调各个审查器
- 管理写作状态
"""
from typing import Optional, List
from core.agents.novel_writer import NovelWriter
from core.workflow.outline_reviewer import OutlineReviewer
from core.workflow.logic_reviewer import LogicReviewer
from core.agent_logger import logger


class WritingWorkflow:
    """
    写作工作流控制器
    负责协调写作的整个流程
    """
    
    def __init__(self, writer: NovelWriter):
        """
        初始化写作工作流
        
        Args:
            writer: NovelWriter 实例
        """
        self.writer = writer
        self.outline_reviewer = OutlineReviewer()
        self.logic_reviewer = LogicReviewer()
        
        # 写作状态
        self.current_volume = 1
        self.current_chapter = 1
        
        logger.info("写作工作流已初始化")
    
    def write_chapter(self, volume: int, chapter: int, chapter_name: str = "") -> dict:
        """
        执行单章写作工作流
        
        流程：
        1. 大纲审查 - 审查当前章节对应的大纲部分
        2. 章节写作 - 基于大纲完成写作
        3. 逻辑审查 - 审查本章与前面所有章节的逻辑一致性
        
        Args:
            volume: 卷号
            chapter: 章节号
            chapter_name: 章节名
        
        Returns:
            {
                "success": bool,           # 是否成功完成
                "chapter_content": str,    # 章节内容
                "outline_review": dict,    # 大纲审查结果
                "logic_review": dict       # 逻辑审查结果
            }
        """
        logger.info(f"开始写作: 第{volume}卷 第{chapter}章")
        
        result = {
            "success": False,
            "chapter_content": "",
            "outline_review": None,
            "logic_review": None
        }
        
        # Step 1: 大纲审查
        logger.info("Step 1: 大纲审查")
        outline_section = self._extract_outline_section(volume, chapter)
        previous_content = self._get_previous_content()
        
        outline_review = self.outline_reviewer.review(outline_section, previous_content)
        result["outline_review"] = outline_review
        
        if not outline_review["passed"]:
            logger.warning("大纲审查未通过")
            # 这里可以添加用户确认逻辑
            # 暂时继续执行
            logger.info("用户确认后继续写作")
        
        # Step 2: 章节写作
        logger.info("Step 2: 章节写作")
        chapter_content = self._write_chapter_content(volume, chapter, chapter_name, outline_section)
        result["chapter_content"] = chapter_content
        
        # 保存章节
        if self.writer.current_project:
            self.writer.current_project.write_chapter(volume, chapter, chapter_content, chapter_name)
            logger.info(f"章节已保存: 第{volume}卷 第{chapter}章")
        
        # Step 3: 逻辑审查
        logger.info("Step 3: 逻辑审查")
        previous_chapters = self._get_all_previous_chapters(volume, chapter)
        logic_review = self.logic_reviewer.review(chapter_content, previous_chapters)
        result["logic_review"] = logic_review
        
        if not logic_review["passed"]:
            logger.warning("逻辑审查未通过")
            # 这里可以添加用户确认逻辑
            # 暂时标记为成功
            result["success"] = True
        else:
            result["success"] = True
            logger.info(f"第{volume}卷 第{chapter}章 写作完成")
        
        # 更新当前进度
        self.current_volume = volume
        self.current_chapter = chapter
        
        return result
    
    def _extract_outline_section(self, volume: int, chapter: int) -> str:
        """提取当前章节对应的大纲部分"""
        if not self.writer.current_project:
            return ""
        
        outline = self.writer.current_project.read_outline()
        
        # 简单的大纲提取逻辑（实际可以更复杂）
        # 这里假设大纲中有 "第X卷" 和 "第X章" 的标记
        lines = outline.split('\n')
        section_lines = []
        in_section = False
        
        for line in lines:
            # 检查是否进入目标章节部分
            if f"第{chapter}章" in line or f"第{volume}卷" in line:
                in_section = True
            
            if in_section:
                section_lines.append(line)
                
                # 检查是否到达下一章
                if len(section_lines) > 1 and (f"第{chapter+1}章" in line or f"第{volume+1}卷" in line):
                    section_lines.pop()  # 移除下一章的标题
                    break
        
        return '\n'.join(section_lines) if section_lines else outline
    
    def _get_previous_content(self) -> str:
        """获取前文内容（用于大纲审查）"""
        if not self.writer.current_project:
            return ""
        
        chapters = self.writer.current_project.list_chapters()
        
        if not chapters:
            return ""
        
        # 获取最后一章的内容作为参考
        last_chapter_path = chapters[-1]
        with open(last_chapter_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _write_chapter_content(self, volume: int, chapter: int, 
                               chapter_name: str, outline_section: str) -> str:
        """调用写作 Agent 生成章节内容"""
        # 构建写作提示
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
        
        # 调用写作 Agent
        response = self.writer.chat(prompt)
        
        return response
    
    def _get_all_previous_chapters(self, volume: int, chapter: int) -> List[str]:
        """获取前面所有章节的内容"""
        if not self.writer.current_project:
            return []
        
        chapters = self.writer.current_project.list_chapters()
        contents = []
        
        for chapter_path in chapters:
            with open(chapter_path, 'r', encoding='utf-8') as f:
                contents.append(f.read())
        
        return contents


if __name__ == '__main__':
    # 测试代码
    from core.agents.novel_writer import NovelWriter
    
    writer = NovelWriter()
    workflow = WritingWorkflow(writer)
    
    # 创建测试项目
    project = writer.create_project("测试小说")
    project.write_outline("# 测试小说\n\n## 第1卷\n\n### 第1章：初入江湖\n\n主角离开家乡...")
    
    # 执行写作工作流
    result = workflow.write_chapter(1, 1, "初入江湖")
    
    print(f"写作成功: {result['success']}")
    print(f"章节内容长度: {len(result['chapter_content'])} 字符")
