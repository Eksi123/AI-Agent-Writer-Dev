"""
章节大纲模型
定义单章的详细规划结构
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class Scene(BaseModel):
    """场景模型"""
    scene_id: str = Field(..., description="场景ID，如 '1-1'")
    location: str = Field(..., description="场景地点")
    characters_present: List[str] = Field(default_factory=list, description="出场角色")
    goal: str = Field(..., description="场景目标")
    conflict: str = Field("", description="场景冲突")
    outcome: str = Field("", description="场景结果")
    mood: str = Field("", description="场景氛围")


class ChapterOutline(BaseModel):
    """
    章节大纲模型
    包含单章的详细规划信息
    """
    chapter_id: int = Field(..., description="章节编号")
    title: str = Field(..., description="章节标题")
    act: int = Field(..., description="所属幕编号")
    pov_character: str = Field(..., description="视角角色")
    timeline: str = Field("", description="时间线描述")
    location: str = Field("", description="主要地点")
    
    # 场景列表
    scenes: List[Scene] = Field(default_factory=list, description="场景列表")
    
    # 伏笔和钩子
    foreshadowing: List[str] = Field(default_factory=list, description="本章埋下的伏笔")
    chapter_hook: str = Field("", description="章末钩子")
    
    # 写作目标
    word_count_target: int = Field(5000, description="目标字数")
    emotional_arc: str = Field("", description="情绪曲线")
    
    # 与前后章的衔接
    previous_chapter_connection: str = Field("", description="与上一章的衔接点")
    next_chapter_setup: str = Field("", description="为下一章做的铺垫")
    
    def to_prompt_string(self) -> str:
        """转换为提示词格式"""
        lines = [
            f"## 第{self.chapter_id}章：{self.title}",
            f"- 所属幕：第{self.act}幕",
            f"- 视角角色：{self.pov_character}",
            f"- 时间线：{self.timeline}",
            f"- 主要地点：{self.location}",
            f"- 目标字数：{self.word_count_target}",
            f"- 情绪曲线：{self.emotional_arc}",
            "",
            "### 场景列表",
        ]
        
        for scene in self.scenes:
            lines.append(f"#### 场景 {scene.scene_id}：{scene.location}")
            lines.append(f"- 出场角色：{', '.join(scene.characters_present)}")
            lines.append(f"- 场景目标：{scene.goal}")
            if scene.conflict:
                lines.append(f"- 场景冲突：{scene.conflict}")
            if scene.outcome:
                lines.append(f"- 场景结果：{scene.outcome}")
            if scene.mood:
                lines.append(f"- 场景氛围：{scene.mood}")
            lines.append("")
        
        if self.foreshadowing:
            lines.append("### 本章伏笔")
            for f in self.foreshadowing:
                lines.append(f"- {f}")
            lines.append("")
        
        if self.chapter_hook:
            lines.append(f"### 章末钩子")
            lines.append(self.chapter_hook)
            lines.append("")
        
        return "\n".join(lines)
