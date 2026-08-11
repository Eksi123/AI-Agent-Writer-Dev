"""
总规划师 Agent
负责生成故事蓝图，规划整体故事线
"""
import json
import os
from typing import Optional

from core.agent_llm import AgentLLM, create_agent_llm
from core.chains.outline_chain import OutlineChain
from core.agent_llm import create_langchain_llm
from core.models.story_blueprint import StoryBlueprint
from core.logger import Logger


_logger = Logger("master_planner")


class MasterPlannerAgent:
    """
    总规划师 Agent
    
    职责：
    - 根据用户输入生成故事蓝图
    - 规划全局故事线、主题、结构
    - 设计角色体系和世界观
    """
    
    def __init__(self, llm: AgentLLM = None, project_dir: str = None):
        """
        初始化总规划师
        
        Args:
            llm: LLM 客户端
            project_dir: 项目输出目录
        """
        self.llm = llm or create_agent_llm()
        self.project_dir = project_dir
        
        # 创建 LangChain 兼容的 LLM
        self.lc_llm = create_langchain_llm()
        self.outline_chain = OutlineChain(self.lc_llm)
        
        _logger.info("总规划师 Agent 初始化完成")
    
    def generate_blueprint(self, genre: str, target_word_count: int,
                          style: str, premise: str,
                          reference: str = "", extra_requirements: str = "") -> StoryBlueprint:
        """
        生成故事蓝图
        
        Args:
            genre: 题材类型
            target_word_count: 目标字数
            style: 风格要求
            premise: 核心设定/前提
            reference: 参考作品
            extra_requirements: 其他要求
        
        Returns:
            StoryBlueprint 对象
        """
        _logger.info(f"开始生成故事蓝图: {genre}, {target_word_count}字")
        
        blueprint = self.outline_chain.generate_blueprint(
            genre=genre,
            target_word_count=target_word_count,
            style=style,
            premise=premise,
            reference=reference,
            extra_requirements=extra_requirements,
        )
        
        # 保存蓝图
        if self.project_dir:
            self._save_blueprint(blueprint)
        
        _logger.info(f"故事蓝图生成完成: 《{blueprint.title}》")
        return blueprint
    
    def refine_blueprint(self, blueprint: StoryBlueprint, feedback: str) -> StoryBlueprint:
        """
        根据反馈优化蓝图
        
        Args:
            blueprint: 当前蓝图
            feedback: 用户反馈
        
        Returns:
            优化后的蓝图
        """
        _logger.info("根据反馈优化故事蓝图")
        
        prompt = f"""请根据用户反馈修改故事蓝图。

## 当前蓝图
{blueprint.to_prompt_string()}

## 用户反馈
{feedback}

请输出修改后的完整故事蓝图（JSON 格式）。"""
        
        response = self.llm.chat(
            prompt=prompt,
            system_prompt="你是专业的小说策划大师。请根据反馈优化蓝图，保持 JSON 格式。",
            max_tokens=8000,
            temperature=0.5,
        )
        
        # 解析新蓝图
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                from core.models.story_blueprint import Act, Character
                from core.models.story_blueprint import StoryBlueprint as SB
                
                acts = [Act(**a) for a in data.get("acts", [])]
                characters = [Character(**c) for c in data.get("characters", [])]
                
                new_blueprint = SB(
                    title=data.get("title", blueprint.title),
                    genre=data.get("genre", blueprint.genre),
                    theme=data.get("theme", blueprint.theme),
                    target_word_count=data.get("target_word_count", blueprint.target_word_count),
                    structure=data.get("structure", blueprint.structure),
                    acts=acts,
                    characters=characters,
                    world_setting=data.get("world_setting", blueprint.world_setting),
                    tone=data.get("tone", blueprint.tone),
                    pov=data.get("pov", blueprint.pov),
                    style_reference=data.get("style_reference", blueprint.style_reference),
                    main_conflict=data.get("main_conflict", blueprint.main_conflict),
                    sub_conflicts=data.get("sub_conflicts", blueprint.sub_conflicts),
                )
                
                if self.project_dir:
                    self._save_blueprint(new_blueprint)
                
                _logger.info(f"蓝图优化完成: 《{new_blueprint.title}》")
                return new_blueprint
        except Exception as e:
            _logger.error(f"解析优化后的蓝图失败: {e}")
        
        _logger.warning("蓝图优化失败，返回原蓝图")
        return blueprint
    
    def _save_blueprint(self, blueprint: StoryBlueprint):
        """保存蓝图到文件"""
        os.makedirs(self.project_dir, exist_ok=True)
        filepath = os.path.join(self.project_dir, "blueprint.json")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(blueprint.model_dump_json(indent=2))
        
        _logger.info(f"蓝图已保存: {filepath}")
