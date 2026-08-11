"""
中短篇小说写作 Agent 系统
主入口和编排器

使用 LangGraph 状态机编排四大 Agent 的工作流程
"""
import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from langgraph.graph import StateGraph, END

from core.agents.master_planner import MasterPlannerAgent
from core.agents.chapter_architect import ChapterArchitectAgent
from core.agents.chapter_writer import ChapterWriterAgent
from core.agents.review_editor import ReviewEditorAgent
from core.memory.story_memory import StoryMemory
from core.memory.character_sheet import CharacterManager
from core.memory.plot_tracker import PlotTracker
from core.memory.summary_chain import SummaryManager
from core.models.story_blueprint import StoryBlueprint
from core.models.chapter_outline import ChapterOutline
from core.logger import Logger, setup_logger


_logger = Logger("main")


@dataclass
class WritingState:
    """写作状态"""
    # 当前阶段
    phase: str = "init"  # init, planning, outlining, writing, reviewing, revising, completed
    
    # 故事蓝图
    blueprint: Optional[StoryBlueprint] = None
    
    # 章节大纲
    current_chapter_id: int = 1
    chapter_outlines: Dict[int, ChapterOutline] = field(default_factory=dict)
    
    # 章节正文
    chapter_texts: Dict[int, str] = field(default_factory=dict)
    
    # 审校信息
    review_reports: Dict[int, Any] = field(default_factory=dict)
    revision_counts: Dict[int, int] = field(default_factory=dict)
    
    # 记忆系统
    story_memory: Optional[StoryMemory] = None
    character_manager: Optional[CharacterManager] = None
    plot_tracker: Optional[PlotTracker] = None
    summary_manager: Optional[SummaryManager] = None
    
    # 用户输入
    user_input: Dict[str, Any] = field(default_factory=dict)
    
    # 项目配置
    project_dir: str = ""
    max_revisions: int = 3
    
    # 错误信息
    error: Optional[str] = None


class NovelWriterOrchestrator:
    """
    小说写作编排器
    
    使用 LangGraph 状态机编排四大 Agent 的工作流程
    """
    
    def __init__(self, project_dir: str, max_revisions: int = 3):
        """
        初始化编排器
        
        Args:
            project_dir: 项目输出目录
            max_revisions: 最大修改轮次
        """
        self.project_dir = project_dir
        self.max_revisions = max_revisions
        
        # 创建项目目录
        os.makedirs(project_dir, exist_ok=True)
        
        # 初始化四大 Agent
        self.master_planner = MasterPlannerAgent(project_dir=project_dir)
        self.chapter_architect = ChapterArchitectAgent(project_dir=project_dir)
        self.chapter_writer = ChapterWriterAgent(project_dir=project_dir)
        self.review_editor = ReviewEditorAgent(project_dir=project_dir)
        
        # 初始化日志
        log_dir = os.path.join(project_dir, "logs")
        setup_logger(log_dir=log_dir, log_level="INFO")
        
        _logger.info(f"小说写作编排器初始化完成，项目目录: {project_dir}")
    
    def run(self, genre: str, target_word_count: int, style: str,
           premise: str, reference: str = "", extra_requirements: str = "") -> bool:
        """
        运行完整的写作流程
        
        Args:
            genre: 题材类型
            target_word_count: 目标字数
            style: 风格要求
            premise: 核心设定/前提
            reference: 参考作品
            extra_requirements: 其他要求
        
        Returns:
            是否成功完成
        """
        _logger.info("=" * 60)
        _logger.info("开始小说写作流程")
        _logger.info("=" * 60)
        
        # 初始化状态
        state = WritingState(
            phase="init",
            user_input={
                "genre": genre,
                "target_word_count": target_word_count,
                "style": style,
                "premise": premise,
                "reference": reference,
                "extra_requirements": extra_requirements,
            },
            project_dir=self.project_dir,
            max_revisions=self.max_revisions,
        )
        
        # 初始化记忆系统
        self._init_memory_system(state)
        
        # 构建工作流图
        workflow = self._build_workflow()
        
        # 运行工作流
        try:
            final_state = workflow.invoke(state)
            
            if final_state.phase == "completed":
                _logger.info("=" * 60)
                _logger.info("小说写作流程完成")
                _logger.info("=" * 60)
                return True
            else:
                _logger.error(f"写作流程异常结束，阶段: {final_state.phase}")
                return False
                
        except Exception as e:
            _logger.error(f"写作流程异常: {e}", exc_info=True)
            return False
    
    def _init_memory_system(self, state: WritingState):
        """初始化记忆系统"""
        memory_dir = os.path.join(self.project_dir, "memory")
        os.makedirs(memory_dir, exist_ok=True)
        
        state.story_memory = StoryMemory(save_dir=memory_dir)
        state.character_manager = CharacterManager(save_dir=memory_dir)
        state.plot_tracker = PlotTracker(save_dir=memory_dir)
        state.summary_manager = SummaryManager(save_dir=memory_dir)
        
        _logger.info("记忆系统初始化完成")
    
    def _build_workflow(self) -> StateGraph:
        """构建工作流图"""
        workflow = StateGraph(WritingState)
        
        # 添加节点
        workflow.add_node("generate_blueprint", self._node_generate_blueprint)
        workflow.add_node("generate_outlines", self._node_generate_outlines)
        workflow.add_node("write_chapter", self._node_write_chapter)
        workflow.add_node("review_chapter", self._node_review_chapter)
        workflow.add_node("revise_chapter", self._node_revise_chapter)
        workflow.add_node("finalize", self._node_finalize)
        
        # 设置入口
        workflow.set_entry_point("generate_blueprint")
        
        # 添加边
        workflow.add_edge("generate_blueprint", "generate_outlines")
        workflow.add_edge("generate_outlines", "write_chapter")
        workflow.add_edge("write_chapter", "review_chapter")
        
        # 条件边：审校后决定是否修改
        workflow.add_conditional_edges(
            "review_chapter",
            self._should_revise,
            {
                "revise": "revise_chapter",
                "next_chapter": "write_chapter",
                "finalize": "finalize",
            }
        )
        
        workflow.add_edge("revise_chapter", "review_chapter")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    def _node_generate_blueprint(self, state: WritingState) -> WritingState:
        """生成故事蓝图节点"""
        _logger.info("【节点】生成故事蓝图")
        state.phase = "planning"
        
        user_input = state.user_input
        blueprint = self.master_planner.generate_blueprint(
            genre=user_input["genre"],
            target_word_count=user_input["target_word_count"],
            style=user_input["style"],
            premise=user_input["premise"],
            reference=user_input.get("reference", ""),
            extra_requirements=user_input.get("extra_requirements", ""),
        )
        
        state.blueprint = blueprint
        
        # 更新记忆系统
        state.story_memory.world_setting = blueprint.world_setting
        state.story_memory.main_conflict = blueprint.main_conflict
        state.story_memory.sub_conflicts = blueprint.sub_conflicts
        
        # 添加角色到角色管理器
        for char in blueprint.characters:
            state.character_manager.add_character(
                name=char.name,
                role=char.role,
                personality=char.personality,
                arc=char.arc,
                speech_style=char.speech_style,
                appearance=char.appearance,
                background=char.background,
            )
        
        # 保存记忆
        state.story_memory.save()
        state.character_manager.save()
        
        _logger.info(f"故事蓝图生成完成: 《{blueprint.title}》")
        return state
    
    def _node_generate_outlines(self, state: WritingState) -> WritingState:
        """生成章节大纲节点"""
        _logger.info("【节点】生成章节大纲")
        state.phase = "outlining"
        
        # 计算总章节数
        total_chapters = sum(a.chapters[1] - a.chapters[0] + 1 for a in state.blueprint.acts)
        
        # 计算每章目标字数
        word_count_per_chapter = state.blueprint.target_word_count // total_chapters
        
        # 生成所有章节大纲
        outlines = self.chapter_architect.generate_all_outlines(
            blueprint=state.blueprint,
            word_count_per_chapter=word_count_per_chapter,
        )
        
        # 存储大纲
        for outline in outlines:
            state.chapter_outlines[outline.chapter_id] = outline
        
        _logger.info(f"章节大纲生成完成，共 {len(outlines)} 章")
        return state
    
    def _node_write_chapter(self, state: WritingState) -> WritingState:
        """写作章节节点"""
        chapter_id = state.current_chapter_id
        _logger.info(f"【节点】写作第{chapter_id}章")
        state.phase = "writing"
        
        outline = state.chapter_outlines[chapter_id]
        
        # 准备上下文
        story_background = state.blueprint.to_prompt_string()
        previous_context = self._get_previous_context(state, chapter_id)
        plot_tracking = self._get_plot_tracking(state)
        last_chapter_ending = self._get_last_chapter_ending(state, chapter_id)
        character_sheets = state.character_manager.generate_prompt_string()
        style_guide = f"风格：{state.blueprint.tone}\n参考：{state.blueprint.style_reference}"
        
        # 写作
        chapter_text = self.chapter_writer.write_chapter(
            outline=outline,
            blueprint=state.blueprint,
            story_background=story_background,
            previous_context=previous_context,
            plot_tracking=plot_tracking,
            last_chapter_ending=last_chapter_ending,
            character_sheets=character_sheets,
            style_guide=style_guide,
        )
        
        state.chapter_texts[chapter_id] = chapter_text
        
        # 生成章节摘要
        summary = state.summary_manager.generate_chapter_summary(
            chapter_id=chapter_id,
            chapter_text=chapter_text,
        )
        
        _logger.info(f"第{chapter_id}章写作完成")
        return state
    
    def _node_review_chapter(self, state: WritingState) -> WritingState:
        """审校章节节点"""
        chapter_id = state.current_chapter_id
        _logger.info(f"【节点】审校第{chapter_id}章")
        state.phase = "reviewing"
        
        outline = state.chapter_outlines[chapter_id]
        chapter_text = state.chapter_texts[chapter_id]
        revision_count = state.revision_counts.get(chapter_id, 0)
        
        # 准备上下文
        character_sheets = state.character_manager.generate_prompt_string()
        style_guide = f"风格：{state.blueprint.tone}\n参考：{state.blueprint.style_reference}"
        previous_context = self._get_previous_context(state, chapter_id)
        existing_settings = state.story_memory.to_prompt_string()
        
        # 审校
        review_report = self.review_editor.review_chapter(
            chapter_text=chapter_text,
            outline=outline,
            character_sheets=character_sheets,
            style_guide=style_guide,
            previous_context=previous_context,
            existing_settings=existing_settings,
            revision_count=revision_count,
        )
        
        state.review_reports[chapter_id] = review_report
        
        _logger.info(f"第{chapter_id}章审校完成: 总分 {review_report.scores.total_score}/10")
        return state
    
    def _node_revise_chapter(self, state: WritingState) -> WritingState:
        """修改章节节点"""
        chapter_id = state.current_chapter_id
        _logger.info(f"【节点】修改第{chapter_id}章")
        state.phase = "revising"
        
        outline = state.chapter_outlines[chapter_id]
        original_text = state.chapter_texts[chapter_id]
        review_report = state.review_reports[chapter_id]
        
        # 更新修改计数
        state.revision_counts[chapter_id] = state.revision_counts.get(chapter_id, 0) + 1
        
        # 准备上下文
        character_sheets = state.character_manager.generate_prompt_string()
        style_guide = f"风格：{state.blueprint.tone}\n参考：{state.blueprint.style_reference}"
        
        # 修改
        revised_text = self.chapter_writer.revise_chapter(
            original_text=original_text,
            outline=outline,
            review_report=review_report.to_prompt_string(),
            blueprint=state.blueprint,
            character_sheets=character_sheets,
            style_guide=style_guide,
        )
        
        state.chapter_texts[chapter_id] = revised_text
        
        _logger.info(f"第{chapter_id}章修改完成（第{state.revision_counts[chapter_id]}轮）")
        return state
    
    def _node_finalize(self, state: WritingState) -> WritingState:
        """完成节点"""
        _logger.info("【节点】完成写作流程")
        state.phase = "completed"
        
        # 保存所有记忆
        state.story_memory.save()
        state.character_manager.save()
        state.plot_tracker.save()
        state.summary_manager.save()
        
        # 生成最终合并文件
        self._merge_chapters(state)
        
        _logger.info("小说写作流程完成")
        return state
    
    def _should_revise(self, state: WritingState) -> str:
        """判断是否需要修改"""
        chapter_id = state.current_chapter_id
        review_report = state.review_reports.get(chapter_id)
        revision_count = state.revision_counts.get(chapter_id, 0)
        
        if review_report.passed:
            # 审校通过，进入下一章
            total_chapters = sum(a.chapters[1] - a.chapters[0] + 1 for a in state.blueprint.acts)
            if chapter_id < total_chapters:
                state.current_chapter_id += 1
                return "next_chapter"
            else:
                return "finalize"
        elif revision_count >= state.max_revisions:
            # 达到最大修改次数，强制进入下一章
            _logger.warning(f"第{chapter_id}章达到最大修改次数，强制进入下一章")
            total_chapters = sum(a.chapters[1] - a.chapters[0] + 1 for a in state.blueprint.acts)
            if chapter_id < total_chapters:
                state.current_chapter_id += 1
                return "next_chapter"
            else:
                return "finalize"
        else:
            # 需要修改
            return "revise"
    
    def _get_previous_context(self, state: WritingState, chapter_id: int) -> str:
        """获取前情上下文"""
        if chapter_id == 1:
            return ""
        
        # 使用滑动窗口摘要
        context = state.summary_manager.assemble_context_with_sliding_window(
            current_chapter=chapter_id,
            window_size=3,
        )
        
        return context
    
    def _get_plot_tracking(self, state: WritingState) -> str:
        """获取情节追踪信息"""
        # 获取活跃的伏笔和情节线
        active_foreshadowing = [f for f in state.plot_tracker.foreshadowings if f.status == "planted"]
        active_threads = [t for t in state.plot_tracker.plot_threads if t.status == "active"]
        
        if not active_foreshadowing and not active_threads:
            return ""
        
        tracking_info = "## 活跃伏笔\n"
        for f in active_foreshadowing[:5]:  # 最多显示5个
            tracking_info += f"- {f.description}（第{f.plant_chapter}章埋下）\n"
        
        tracking_info += "\n## 活跃情节线\n"
        for t in active_threads[:3]:  # 最多显示3个
            tracking_info += f"- {t.name}: {t.description}\n"
        
        return tracking_info
    
    def _get_last_chapter_ending(self, state: WritingState, chapter_id: int) -> str:
        """获取上一章结尾"""
        if chapter_id == 1:
            return ""
        
        last_chapter_text = state.chapter_texts.get(chapter_id - 1, "")
        if not last_chapter_text:
            return ""
        
        # 返回最后500字
        return last_chapter_text[-500:] if len(last_chapter_text) > 500 else last_chapter_text
    
    def _merge_chapters(self, state: WritingState):
        """合并所有章节到最终文件"""
        _logger.info("合并所有章节")
        
        output_file = os.path.join(self.project_dir, f"{state.blueprint.title}.txt")
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"《{state.blueprint.title}》\n\n")
            f.write(f"题材：{state.blueprint.genre}\n")
            f.write(f"主题：{state.blueprint.theme}\n")
            f.write(f"总字数：约{state.blueprint.target_word_count}字\n\n")
            f.write("=" * 60 + "\n\n")
            
            for chapter_id in sorted(state.chapter_texts.keys()):
                chapter_text = state.chapter_texts[chapter_id]
                outline = state.chapter_outlines.get(chapter_id)
                
                f.write(f"\n{'=' * 40}\n")
                if outline:
                    f.write(f"{outline.title}\n")
                else:
                    f.write(f"第{chapter_id}章\n")
                f.write(f"{'=' * 40}\n\n")
                f.write(chapter_text)
                f.write("\n\n")
        
        _logger.info(f"小说已合并到: {output_file}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="中短篇小说写作 Agent 系统")
    parser.add_argument("--output", "-o", required=True, help="项目输出目录")
    parser.add_argument("--genre", "-g", required=True, help="题材类型")
    parser.add_argument("--words", "-w", type=int, required=True, help="目标字数")
    parser.add_argument("--style", "-s", required=True, help="风格要求")
    parser.add_argument("--premise", "-p", required=True, help="核心设定/前提")
    parser.add_argument("--reference", "-r", default="", help="参考作品")
    parser.add_argument("--extra", "-e", default="", help="其他要求")
    parser.add_argument("--max-revisions", type=int, default=3, help="最大修改轮次")
    
    args = parser.parse_args()
    
    # 创建编排器
    orchestrator = NovelWriterOrchestrator(
        project_dir=args.output,
        max_revisions=args.max_revisions,
    )
    
    # 运行写作流程
    success = orchestrator.run(
        genre=args.genre,
        target_word_count=args.words,
        style=args.style,
        premise=args.premise,
        reference=args.reference,
        extra_requirements=args.extra,
    )
    
    if success:
        print("\n✓ 小说写作完成！")
        print(f"输出目录: {args.output}")
    else:
        print("\n✗ 小说写作失败，请查看日志")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
