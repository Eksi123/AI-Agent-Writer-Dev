"""
情节线索追踪器
管理伏笔、线索、未解之谜等情节元素
"""
import json
import os
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum

from core.logger import Logger


_logger = Logger("plot_tracker")


class ForeshadowingStatus(str, Enum):
    """伏笔状态"""
    ACTIVE = "active"           # 活跃中
    RESOLVED = "resolved"       # 已回收
    ABANDONED = "abandoned"     # 已放弃


class Foreshadowing(BaseModel):
    """伏笔模型"""
    id: int = Field(..., description="伏笔ID")
    planted_chapter: int = Field(..., description="埋下伏笔的章节")
    description: str = Field(..., description="伏笔描述")
    expected_payoff_chapter: int = Field(..., description="预期回收章节")
    status: ForeshadowingStatus = Field(ForeshadowingStatus.ACTIVE, description="伏笔状态")
    resolved_chapter: Optional[int] = Field(None, description="实际回收章节")
    resolution: str = Field("", description="回收方式")
    related_characters: List[str] = Field(default_factory=list, description="相关角色")


class PlotThread(BaseModel):
    """情节线索"""
    thread_id: int = Field(..., description="线索ID")
    name: str = Field(..., description="线索名称")
    description: str = Field(..., description="线索描述")
    start_chapter: int = Field(..., description="起始章节")
    status: ForeshadowingStatus = Field(ForeshadowingStatus.ACTIVE, description="线索状态")
    related_events: List[int] = Field(default_factory=list, description="相关事件ID列表")


class PlotTracker:
    """
    情节线索追踪器
    
    负责：
    - 管理伏笔的埋下和回收
    - 追踪情节线索
    - 检查逾期未回收的伏笔
    """
    
    def __init__(self, project_dir: str):
        """
        初始化情节追踪器
        
        Args:
            project_dir: 项目输出目录
        """
        self.project_dir = project_dir
        self.memory_dir = os.path.join(project_dir, "memory")
        os.makedirs(self.memory_dir, exist_ok=True)
        
        # 伏笔列表
        self.foreshadowings: List[Foreshadowing] = []
        
        # 情节线索
        self.plot_threads: List[PlotThread] = []
        
        # 文件路径
        self.state_file = os.path.join(self.memory_dir, "plot_tracker.json")
        
        _logger.info("情节追踪器初始化完成")
    
    def plant_foreshadowing(self, chapter: int, description: str, 
                           expected_payoff: int, 
                           related_characters: List[str] = None) -> int:
        """
        埋下伏笔
        
        Args:
            chapter: 埋下伏笔的章节
            description: 伏笔描述
            expected_payoff: 预期回收章节
            related_characters: 相关角色
        
        Returns:
            伏笔ID
        """
        foreshadowing = Foreshadowing(
            id=len(self.foreshadowings) + 1,
            planted_chapter=chapter,
            description=description,
            expected_payoff_chapter=expected_payoff,
            related_characters=related_characters or [],
        )
        self.foreshadowings.append(foreshadowing)
        _logger.info(f"埋下伏笔 #{foreshadowing.id}（第{chapter}章）: {description[:50]}...")
        return foreshadowing.id
    
    def resolve_foreshadowing(self, foreshadowing_id: int, 
                             chapter: int, resolution: str = ""):
        """
        回收伏笔
        
        Args:
            foreshadowing_id: 伏笔ID
            chapter: 回收章节
            resolution: 回收方式
        """
        for f in self.foreshadowings:
            if f.id == foreshadowing_id:
                f.status = ForeshadowingStatus.RESOLVED
                f.resolved_chapter = chapter
                f.resolution = resolution
                _logger.info(f"回收伏笔 #{foreshadowing_id}（第{chapter}章）")
                return
        
        _logger.warning(f"伏笔 #{foreshadowing_id} 不存在")
    
    def abandon_foreshadowing(self, foreshadowing_id: int):
        """放弃伏笔"""
        for f in self.foreshadowings:
            if f.id == foreshadowing_id:
                f.status = ForeshadowingStatus.ABANDONED
                _logger.info(f"放弃伏笔 #{foreshadowing_id}")
                return
        
        _logger.warning(f"伏笔 #{foreshadowing_id} 不存在")
    
    def add_plot_thread(self, name: str, description: str, start_chapter: int) -> int:
        """
        添加情节线索
        
        Args:
            name: 线索名称
            description: 线索描述
            start_chapter: 起始章节
        
        Returns:
            线索ID
        """
        thread = PlotThread(
            thread_id=len(self.plot_threads) + 1,
            name=name,
            description=description,
            start_chapter=start_chapter,
        )
        self.plot_threads.append(thread)
        _logger.info(f"添加情节线索 #{thread.id}: {name}")
        return thread.thread_id
    
    def resolve_plot_thread(self, thread_id: int):
        """完结情节线索"""
        for t in self.plot_threads:
            if t.thread_id == thread_id:
                t.status = ForeshadowingStatus.RESOLVED
                _logger.info(f"完结情节线索 #{thread_id}: {t.name}")
                return
        
        _logger.warning(f"情节线索 #{thread_id} 不存在")
    
    def get_active_foreshadowings(self, chapter: int = None) -> List[Foreshadowing]:
        """
        获取活跃的伏笔
        
        Args:
            chapter: 如果指定，只返回在该章仍然活跃的伏笔
        
        Returns:
            活跃伏笔列表
        """
        active = [f for f in self.foreshadowings if f.status == ForeshadowingStatus.ACTIVE]
        
        if chapter is not None:
            # 只返回在该章之前埋下且预期在该章或之后回收的
            active = [
                f for f in active 
                if f.planted_chapter <= chapter and f.expected_payoff_chapter >= chapter
            ]
        
        return active
    
    def get_overdue_foreshadowings(self, current_chapter: int) -> List[Foreshadowing]:
        """
        获取逾期未回收的伏笔
        
        Args:
            current_chapter: 当前章节
        
        Returns:
            逾期伏笔列表
        """
        return [
            f for f in self.foreshadowings
            if f.status == ForeshadowingStatus.ACTIVE
            and f.expected_payoff_chapter < current_chapter
        ]
    
    def get_foreshadowings_for_chapter(self, chapter: int) -> List[Foreshadowing]:
        """
        获取某章需要关注的伏笔（埋下的 + 预期回收的）
        
        Args:
            chapter: 章节编号
        
        Returns:
            相关伏笔列表
        """
        planted = [
            f for f in self.foreshadowings
            if f.planted_chapter == chapter
        ]
        payoff = [
            f for f in self.foreshadowings
            if f.expected_payoff_chapter == chapter and f.status == ForeshadowingStatus.ACTIVE
        ]
        return planted + payoff
    
    def get_active_threads(self) -> List[PlotThread]:
        """获取活跃的情节线索"""
        return [t for t in self.plot_threads if t.status == ForeshadowingStatus.ACTIVE]
    
    def to_prompt_string(self, current_chapter: int) -> str:
        """
        转换为提示词格式
        
        Args:
            current_chapter: 当前章节
        """
        lines = ["## 情节线索追踪", ""]
        
        # 活跃伏笔
        active = self.get_active_foreshadowings(current_chapter)
        if active:
            lines.append("### 活跃伏笔")
            for f in active:
                lines.append(
                    f"- [#{f.id}] {f.description} "
                    f"（第{f.planted_chapter}章埋下，预期第{f.expected_payoff_chapter}章回收）"
                )
            lines.append("")
        
        # 逾期伏笔
        overdue = self.get_overdue_foreshadowings(current_chapter)
        if overdue:
            lines.append("### ⚠️ 逾期未回收的伏笔")
            for f in overdue:
                lines.append(
                    f"- [#{f.id}] {f.description} "
                    f"（第{f.planted_chapter}章埋下，预期第{f.expected_payoff_chapter}章回收）"
                )
            lines.append("")
        
        # 本章相关伏笔
        chapter_related = self.get_foreshadowings_for_chapter(current_chapter)
        if chapter_related:
            lines.append(f"### 第{current_chapter}章相关伏笔")
            for f in chapter_related:
                if f.planted_chapter == current_chapter:
                    lines.append(f"- 🔽 埋下: {f.description}")
                elif f.expected_payoff_chapter == current_chapter:
                    lines.append(f"- 🔼 回收: {f.description}")
            lines.append("")
        
        # 活跃线索
        threads = self.get_active_threads()
        if threads:
            lines.append("### 活跃情节线索")
            for t in threads:
                lines.append(f"- {t.name}: {t.description}")
            lines.append("")
        
        return "\n".join(lines)
    
    def save(self):
        """保存状态到文件"""
        state = {
            "foreshadowings": [f.model_dump() for f in self.foreshadowings],
            "plot_threads": [t.model_dump() for t in self.plot_threads],
        }
        
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        
        _logger.info(f"情节追踪数据已保存到: {self.state_file}")
    
    def load(self):
        """从文件加载状态"""
        if not os.path.exists(self.state_file):
            _logger.warning(f"情节追踪文件不存在: {self.state_file}")
            return
        
        with open(self.state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
        
        self.foreshadowings = [
            Foreshadowing(**f) for f in state.get("foreshadowings", [])
        ]
        self.plot_threads = [
            PlotThread(**t) for t in state.get("plot_threads", [])
        ]
        
        _logger.info(
            f"情节追踪数据已从文件加载: "
            f"{len(self.foreshadowings)} 个伏笔, "
            f"{len(self.plot_threads)} 条线索"
        )
