"""
一致性校验链
负责检查新生成内容与已有设定的一致性
"""
import json
import re
from typing import List, Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from core.agent_llm import LangChainChatModel
from core.logger import Logger


_logger = Logger("consistency_chain")


CONSISTENCY_CHECK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是一位细致的小说一致性校验专家。

请检查新生成的章节内容是否与已有设定存在矛盾或不一致。

检查维度：
1. **角色一致性**：角色行为、对话是否符合其性格设定
2. **时间线一致性**：事件发生顺序是否合理
3. **设定一致性**：是否违反世界观设定或规则
4. **情节一致性**：是否与已知情节矛盾
5. **知识一致性**：角色是否知道了他们不应该知道的信息

请严格按照 JSON 格式输出检查结果。"""),
    ("human", """## 已有设定
{existing_settings}

## 角色卡片
{character_sheets}

## 前情摘要
{previous_summaries}

## 新生成的内容
{new_content}

请按以下 JSON 格式输出检查结果：
{{
    "consistent": 是否一致（true/false）,
    "issues": [
        {{
            "type": "问题类型（角色/时间线/设定/情节/知识）",
            "description": "问题描述",
            "detail": "具体矛盾点",
            "suggestion": "修正建议"
        }}
    ],
    "confidence": 一致性置信度（0-1）,
    "summary": "检查总结"
}}""")
])


class ConsistencyChain:
    """一致性校验链"""
    
    def __init__(self, llm: LangChainChatModel):
        """
        初始化一致性校验链
        
        Args:
            llm: LangChain 兼容的 LLM 实例
        """
        self.llm = llm
        self.output_parser = StrOutputParser()
        _logger.info("一致性校验链初始化完成")
    
    def check_consistency(self, new_content: str, existing_settings: str,
                         character_sheets: str, previous_summaries: str) -> Dict:
        """
        检查一致性
        
        Args:
            new_content: 新生成的内容
            existing_settings: 已有设定
            character_sheets: 角色卡片
            previous_summaries: 前情摘要
        
        Returns:
            检查结果字典
        """
        _logger.info("开始一致性校验")
        
        chain = CONSISTENCY_CHECK_PROMPT | self.llm | self.output_parser
        response = chain.invoke({
            "existing_settings": existing_settings or "暂无设定",
            "character_sheets": character_sheets or "暂无角色信息",
            "previous_summaries": previous_summaries or "暂无前情",
            "new_content": new_content,
        })
        
        # 解析结果
        result = self._parse_consistency_result(response)
        
        if result["consistent"]:
            _logger.info(f"一致性校验通过（置信度: {result['confidence']:.2f}）")
        else:
            _logger.warning(
                f"一致性校验发现 {len(result['issues'])} 个问题"
            )
        
        return result
    
    def _parse_consistency_result(self, response: str) -> Dict:
        """解析一致性检查结果"""
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "consistent": data.get("consistent", True),
                    "issues": data.get("issues", []),
                    "confidence": data.get("confidence", 0.8),
                    "summary": data.get("summary", ""),
                }
            else:
                raise ValueError("未找到 JSON 内容")
        except Exception as e:
            _logger.error(f"解析一致性检查结果失败: {e}")
            return {
                "consistent": True,  # 解析失败时默认通过
                "issues": [],
                "confidence": 0.5,
                "summary": "一致性检查解析失败，默认通过",
            }
