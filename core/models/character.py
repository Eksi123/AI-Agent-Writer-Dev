"""
角色卡片模型
用于追踪角色的状态和变化
"""
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class CharacterState(BaseModel):
    """角色当前状态"""
    current_location: str = Field("", description="当前位置")
    current_knowledge: List[str] = Field(default_factory=list, description="当前已知信息")
    emotional_state: str = Field("", description="当前情绪状态")
    relationships: Dict[str, str] = Field(default_factory=dict, description="与其他角色的关系")
    goals: List[str] = Field(default_factory=list, description="当前目标")
    secrets: List[str] = Field(default_factory=list, description="隐藏的秘密")


class CharacterChange(BaseModel):
    """角色在某一章的变化"""
    chapter: int = Field(..., description="章节编号")
    changes: List[str] = Field(default_factory=list, description="变化内容")


class CharacterSheet(BaseModel):
    """
    角色卡片模型
    包含角色的完整信息和状态追踪
    """
    # 基础档案
    name: str = Field(..., description="角色姓名")
    role: str = Field(..., description="角色定位")
    age: Optional[int] = Field(None, description="年龄")
    occupation: str = Field("", description="职业")
    appearance: str = Field("", description="外貌描述")
    personality: str = Field(..., description="性格特征")
    background: str = Field("", description="背景故事")
    
    # 语言习惯
    speech_style: str = Field("", description="说话风格")
    catchphrases: List[str] = Field(default_factory=list, description="口头禅")
    inner_monologue_style: str = Field("", description="内心独白风格")
    
    # 成长弧线
    character_arc: str = Field("", description="角色成长弧线")
    
    # 状态追踪
    state: CharacterState = Field(default_factory=CharacterState, description="当前状态")
    state_history: List[CharacterChange] = Field(default_factory=list, description="状态变化历史")
    
    def update_state(self, chapter: int, changes: List[str], new_state: Optional[Dict] = None):
        """
        更新角色状态
        
        Args:
            chapter: 章节编号
            changes: 变化内容列表
            new_state: 新的状态字典（可选）
        """
        # 记录变化历史
        self.state_history.append(CharacterChange(chapter=chapter, changes=changes))
        
        # 更新当前状态
        if new_state:
            for key, value in new_state.items():
                if hasattr(self.state, key):
                    setattr(self.state, key, value)
    
    def get_state_at_chapter(self, chapter: int) -> CharacterState:
        """获取角色在某一章的状态"""
        # 简单实现：返回当前状态
        # 可以扩展为根据历史状态重建某一章的状态
        return self.state
    
    def to_prompt_string(self, include_history: bool = False) -> str:
        """
        转换为提示词格式
        
        Args:
            include_history: 是否包含状态变化历史
        """
        lines = [
            f"### {self.name}（{self.role}）",
            f"- 年龄：{self.age}" if self.age else "",
            f"- 职业：{self.occupation}" if self.occupation else "",
            f"- 外貌：{self.appearance}" if self.appearance else "",
            f"- 性格：{self.personality}",
            f"- 背景：{self.background}" if self.background else "",
            "",
            "#### 语言习惯",
            f"- 说话风格：{self.speech_style}" if self.speech_style else "",
        ]
        
        if self.catchphrases:
            lines.append(f"- 口头禅：{', '.join(self.catchphrases)}")
        
        if self.inner_monologue_style:
            lines.append(f"- 内心独白：{self.inner_monologue_style}")
        
        lines.append("")
        lines.append("#### 当前状态")
        lines.append(f"- 位置：{self.state.current_location}" if self.state.current_location else "")
        lines.append(f"- 情绪：{self.state.emotional_state}" if self.state.emotional_state else "")
        
        if self.state.current_knowledge:
            lines.append(f"- 已知信息：{', '.join(self.state.current_knowledge)}")
        
        if self.state.relationships:
            lines.append("- 关系：")
            for name, relation in self.state.relationships.items():
                lines.append(f"  - {name}：{relation}")
        
        if self.state.goals:
            lines.append(f"- 当前目标：{', '.join(self.state.goals)}")
        
        if include_history and self.state_history:
            lines.append("")
            lines.append("#### 状态变化历史")
            for change in self.state_history:
                lines.append(f"第{change.chapter}章：{', '.join(change.changes)}")
        
        # 过滤空行
        lines = [line for line in lines if line]
        
        return "\n".join(lines)
