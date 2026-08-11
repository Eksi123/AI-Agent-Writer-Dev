"""
角色卡片管理器
管理所有角色的状态和变化
"""
import json
import os
from typing import List, Optional, Dict

from core.models.character import CharacterSheet, CharacterState
from core.models.story_blueprint import Character as BlueprintCharacter
from core.logger import Logger


_logger = Logger("character_manager")


class CharacterManager:
    """
    角色卡片管理器
    
    负责：
    - 管理所有角色卡片
    - 追踪角色状态变化
    - 提供角色信息查询
    """
    
    def __init__(self, project_dir: str):
        """
        初始化角色管理器
        
        Args:
            project_dir: 项目输出目录
        """
        self.project_dir = project_dir
        self.memory_dir = os.path.join(project_dir, "memory")
        os.makedirs(self.memory_dir, exist_ok=True)
        
        # 角色卡片字典 {name: CharacterSheet}
        self.characters: Dict[str, CharacterSheet] = {}
        
        # 文件路径
        self.state_file = os.path.join(self.memory_dir, "characters.json")
        
        _logger.info("角色管理器初始化完成")
    
    def add_character(self, blueprint_char: BlueprintCharacter):
        """
        从蓝图角色创建角色卡片
        
        Args:
            blueprint_char: 蓝图中的角色定义
        """
        sheet = CharacterSheet(
            name=blueprint_char.name,
            role=blueprint_char.role,
            age=blueprint_char.age,
            personality=blueprint_char.personality,
            character_arc=blueprint_char.arc,
            speech_style=blueprint_char.speech_style,
            appearance=blueprint_char.appearance or "",
            background=blueprint_char.background or "",
        )
        
        self.characters[sheet.name] = sheet
        _logger.info(f"添加角色卡片: {sheet.name}（{sheet.role}）")
    
    def add_character_sheet(self, sheet: CharacterSheet):
        """直接添加角色卡片"""
        self.characters[sheet.name] = sheet
        _logger.info(f"添加角色卡片: {sheet.name}（{sheet.role}）")
    
    def get_character(self, name: str) -> Optional[CharacterSheet]:
        """获取角色卡片"""
        return self.characters.get(name)
    
    def get_characters_by_names(self, names: List[str]) -> List[CharacterSheet]:
        """批量获取角色卡片"""
        return [self.characters[name] for name in names if name in self.characters]
    
    def update_character_state(self, name: str, chapter: int, 
                               changes: List[str], new_state: Optional[Dict] = None):
        """
        更新角色状态
        
        Args:
            name: 角色姓名
            chapter: 章节编号
            changes: 变化内容
            new_state: 新的状态字段
        """
        if name not in self.characters:
            _logger.warning(f"角色不存在: {name}")
            return
        
        self.characters[name].update_state(chapter, changes, new_state)
        _logger.info(f"更新角色状态: {name}（第{chapter}章）")
    
    def get_character_prompt(self, names: List[str], include_history: bool = False) -> str:
        """
        生成角色卡片的提示词
        
        Args:
            names: 角色姓名列表
            include_history: 是否包含状态历史
        
        Returns:
            格式化的角色信息字符串
        """
        chars = self.get_characters_by_names(names)
        if not chars:
            return ""
        
        sections = ["## 出场角色"]
        for char in chars:
            sections.append(char.to_prompt_string(include_history=include_history))
            sections.append("")
        
        return "\n".join(sections)
    
    def get_all_characters_prompt(self, include_history: bool = False) -> str:
        """生成所有角色卡片的提示词"""
        return self.get_character_prompt(list(self.characters.keys()), include_history)
    
    def save(self):
        """保存所有角色卡片到文件"""
        state = {
            name: sheet.model_dump() 
            for name, sheet in self.characters.items()
        }
        
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        
        _logger.info(f"角色卡片已保存到: {self.state_file}")
    
    def load(self):
        """从文件加载角色卡片"""
        if not os.path.exists(self.state_file):
            _logger.warning(f"角色卡片文件不存在: {self.state_file}")
            return
        
        with open(self.state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
        
        self.characters = {
            name: CharacterSheet(**data)
            for name, data in state.items()
        }
        
        _logger.info(f"角色卡片已从文件加载: {self.state_file}，共 {len(self.characters)} 个角色")
