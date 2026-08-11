"""
全局故事记忆
管理小说的世界观、核心设定、重要事件等全局信息
"""
import json
import os
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from core.logger import Logger


_logger = Logger("story_memory")


class WorldSetting(BaseModel):
    """世界观设定"""
    time_period: str = Field("", description="时代背景")
    location: str = Field("", description="主要地点")
    social_context: str = Field("", description="社会背景")
    rules: List[str] = Field(default_factory=list, description="世界规则（如魔法体系等）")
    atmosphere: str = Field("", description="整体氛围")


class ImportantEvent(BaseModel):
    """重要事件"""
    event_id: int = Field(..., description="事件ID")
    chapter: int = Field(..., description="发生章节")
    description: str = Field(..., description="事件描述")
    impact: str = Field("", description="对后续情节的影响")
    involved_characters: List[str] = Field(default_factory=list, description="涉及角色")


class StoryMemory:
    """
    全局故事记忆管理器
    
    负责维护：
    - 世界观设定
    - 核心冲突
    - 重要事件时间线
    - 全局规则
    """
    
    def __init__(self, project_dir: str):
        """
        初始化故事记忆
        
        Args:
            project_dir: 项目输出目录
        """
        self.project_dir = project_dir
        self.memory_dir = os.path.join(project_dir, "memory")
        os.makedirs(self.memory_dir, exist_ok=True)
        
        # 核心数据
        self.world_setting = WorldSetting()
        self.main_conflict = ""
        self.sub_conflicts: List[str] = []
        self.important_events: List[ImportantEvent] = []
        self.global_rules: List[str] = []
        
        # 文件路径
        self.state_file = os.path.join(self.memory_dir, "story_state.json")
        
        _logger.info("故事记忆管理器初始化完成")
    
    def set_world_setting(self, **kwargs):
        """
        设置世界观
        
        Args:
            **kwargs: 世界观字段
        """
        for key, value in kwargs.items():
            if hasattr(self.world_setting, key):
                setattr(self.world_setting, key, value)
        _logger.info("世界观设定已更新")
    
    def set_main_conflict(self, conflict: str):
        """设置主要冲突"""
        self.main_conflict = conflict
        _logger.info("主要冲突已更新")
    
    def add_sub_conflict(self, conflict: str):
        """添加次要冲突"""
        self.sub_conflicts.append(conflict)
        _logger.info(f"添加次要冲突: {conflict[:50]}...")
    
    def add_important_event(self, chapter: int, description: str, 
                           impact: str = "", involved_characters: List[str] = None):
        """
        添加重要事件
        
        Args:
            chapter: 发生章节
            description: 事件描述
            impact: 对后续的影响
            involved_characters: 涉及角色
        """
        event = ImportantEvent(
            event_id=len(self.important_events) + 1,
            chapter=chapter,
            description=description,
            impact=impact,
            involved_characters=involved_characters or [],
        )
        self.important_events.append(event)
        _logger.info(f"添加重要事件（第{chapter}章）: {description[:50]}...")
    
    def add_global_rule(self, rule: str):
        """添加全局规则"""
        self.global_rules.append(rule)
        _logger.info(f"添加全局规则: {rule[:50]}...")
    
    def get_events_before_chapter(self, chapter: int) -> List[ImportantEvent]:
        """获取某章之前发生的所有重要事件"""
        return [e for e in self.important_events if e.chapter < chapter]
    
    def get_events_in_chapter(self, chapter: int) -> List[ImportantEvent]:
        """获取某章发生的重要事件"""
        return [e for e in self.important_events if e.chapter == chapter]
    
    def to_prompt_string(self, max_length: int = 1000) -> str:
        """
        转换为提示词格式
        
        Args:
            max_length: 最大字符数
        """
        lines = [
            "## 故事背景",
            "",
        ]
        
        # 世界观
        if self.world_setting.time_period or self.world_setting.location:
            lines.append("### 世界观")
            if self.world_setting.time_period:
                lines.append(f"- 时代：{self.world_setting.time_period}")
            if self.world_setting.location:
                lines.append(f"- 地点：{self.world_setting.location}")
            if self.world_setting.social_context:
                lines.append(f"- 社会背景：{self.world_setting.social_context}")
            if self.world_setting.atmosphere:
                lines.append(f"- 氛围：{self.world_setting.atmosphere}")
            if self.world_setting.rules:
                lines.append("- 世界规则：")
                for rule in self.world_setting.rules:
                    lines.append(f"  - {rule}")
            lines.append("")
        
        # 核心冲突
        if self.main_conflict:
            lines.append("### 核心冲突")
            lines.append(f"主要冲突：{self.main_conflict}")
            if self.sub_conflicts:
                lines.append("次要冲突：")
                for conflict in self.sub_conflicts:
                    lines.append(f"  - {conflict}")
            lines.append("")
        
        # 全局规则
        if self.global_rules:
            lines.append("### 全局规则")
            for rule in self.global_rules:
                lines.append(f"- {rule}")
            lines.append("")
        
        result = "\n".join(lines)
        
        # 截断
        if len(result) > max_length:
            result = result[:max_length] + "\n...(已截断)"
        
        return result
    
    def save(self):
        """保存状态到文件"""
        state = {
            "world_setting": self.world_setting.model_dump(),
            "main_conflict": self.main_conflict,
            "sub_conflicts": self.sub_conflicts,
            "important_events": [e.model_dump() for e in self.important_events],
            "global_rules": self.global_rules,
        }
        
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        
        _logger.info(f"故事记忆已保存到: {self.state_file}")
    
    def load(self):
        """从文件加载状态"""
        if not os.path.exists(self.state_file):
            _logger.warning(f"故事记忆文件不存在: {self.state_file}")
            return
        
        with open(self.state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
        
        self.world_setting = WorldSetting(**state.get("world_setting", {}))
        self.main_conflict = state.get("main_conflict", "")
        self.sub_conflicts = state.get("sub_conflicts", [])
        self.important_events = [
            ImportantEvent(**e) for e in state.get("important_events", [])
        ]
        self.global_rules = state.get("global_rules", [])
        
        _logger.info(f"故事记忆已从文件加载: {self.state_file}")
