"""
故事蓝图模型
定义小说的全局规划结构
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class Character(BaseModel):
    """角色基础模型"""
    name: str = Field(..., description="角色姓名")
    role: str = Field(..., description="角色定位（主角/配角/反派等）")
    age: Optional[int] = Field(None, description="年龄")
    personality: str = Field(..., description="性格特征")
    arc: str = Field(..., description="角色成长弧线")
    speech_style: str = Field("", description="说话风格")
    appearance: Optional[str] = Field(None, description="外貌描述")
    background: Optional[str] = Field(None, description="背景故事")


class Act(BaseModel):
    """幕结构模型"""
    name: str = Field(..., description="幕名称")
    chapters: List[int] = Field(..., description="包含的章节范围 [start, end]")
    summary: str = Field(..., description="本幕概要")
    key_events: List[str] = Field(default_factory=list, description="关键事件列表")


class StoryBlueprint(BaseModel):
    """
    故事蓝图模型
    包含小说的全局规划信息
    """
    title: str = Field(..., description="小说标题")
    genre: str = Field(..., description="题材类型")
    theme: str = Field(..., description="核心主题")
    target_word_count: int = Field(..., description="目标字数")
    structure: str = Field("三幕式", description="叙事结构")
    
    # 幕结构
    acts: List[Act] = Field(default_factory=list, description="幕列表")
    
    # 角色列表
    characters: List[Character] = Field(default_factory=list, description="角色列表")
    
    # 世界观设定
    world_setting: str = Field("", description="世界观/背景设定")
    
    # 风格相关
    tone: str = Field("", description="整体基调")
    pov: str = Field("第三人称", description="叙事视角")
    style_reference: str = Field("", description="风格参考")
    
    # 核心冲突
    main_conflict: str = Field("", description="主要冲突")
    sub_conflicts: List[str] = Field(default_factory=list, description="次要冲突")
    
    def get_character_by_name(self, name: str) -> Optional[Character]:
        """根据姓名获取角色"""
        for char in self.characters:
            if char.name == name:
                return char
        return None
    
    def get_act_for_chapter(self, chapter_id: int) -> Optional[Act]:
        """获取章节所属的幕"""
        for act in self.acts:
            if act.chapters[0] <= chapter_id <= act.chapters[1]:
                return act
        return None
    
    def to_prompt_string(self) -> str:
        """转换为提示词格式"""
        lines = [
            f"## 故事蓝图：{self.title}",
            f"- 题材：{self.genre}",
            f"- 主题：{self.theme}",
            f"- 目标字数：{self.target_word_count}",
            f"- 叙事结构：{self.structure}",
            f"- 叙事视角：{self.pov}",
            f"- 整体基调：{self.tone}",
            "",
            "### 世界观",
            self.world_setting,
            "",
            "### 主要角色",
        ]
        
        for char in self.characters:
            lines.append(f"#### {char.name}（{char.role}）")
            lines.append(f"- 性格：{char.personality}")
            lines.append(f"- 成长弧线：{char.arc}")
            if char.speech_style:
                lines.append(f"- 说话风格：{char.speech_style}")
            lines.append("")
        
        lines.append("### 故事结构")
        for act in self.acts:
            lines.append(f"#### {act.name}（第{act.chapters[0]}-{act.chapters[1]}章）")
            lines.append(act.summary)
            if act.key_events:
                lines.append("关键事件：")
                for event in act.key_events:
                    lines.append(f"  - {event}")
            lines.append("")
        
        return "\n".join(lines)
