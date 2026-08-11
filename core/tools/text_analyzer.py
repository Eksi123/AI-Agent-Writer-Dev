"""
文本分析工具
提供字数统计、可读性分析等功能
"""
import re
from typing import Dict, List

from core.logger import Logger


_logger = Logger("text_analyzer")


class TextAnalyzer:
    """
    文本分析器
    
    功能：
    - 字数统计
    - 对话占比分析
    - 段落分析
    - 可读性评估
    """
    
    @staticmethod
    def count_words(text: str) -> Dict[str, int]:
        """
        统计字数
        
        Args:
            text: 待分析文本
        
        Returns:
            字数统计结果
        """
        # 去除空白字符
        text = text.strip()
        
        # 总字符数（含标点）
        total_chars = len(text)
        
        # 中文字符数
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        
        # 英文单词数
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        
        # 数字
        numbers = len(re.findall(r'\d+', text))
        
        # 标点符号
        punctuation = len(re.findall(r'[^\w\s]', text))
        
        # 估算字数（中文 + 英文单词）
        estimated_words = chinese_chars + english_words
        
        return {
            "total_chars": total_chars,
            "chinese_chars": chinese_chars,
            "english_words": english_words,
            "numbers": numbers,
            "punctuation": punctuation,
            "estimated_words": estimated_words,
        }
    
    @staticmethod
    def count_paragraphs(text: str) -> int:
        """
        统计段落数
        
        Args:
            text: 待分析文本
        
        Returns:
            段落数
        """
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        return len(paragraphs)
    
    @staticmethod
    def analyze_dialogue(text: str) -> Dict[str, float]:
        """
        分析对话占比
        
        Args:
            text: 待分析文本
        
        Returns:
            对话分析结果
        """
        # 匹配对话（中文引号）
        dialogues = re.findall(r'[""](.*?)[""]', text, re.DOTALL)
        dialogue_text = ' '.join(dialogues)
        
        total_chars = len(text)
        dialogue_chars = len(dialogue_text)
        
        dialogue_ratio = dialogue_chars / total_chars if total_chars > 0 else 0
        
        return {
            "dialogue_count": len(dialogues),
            "dialogue_chars": dialogue_chars,
            "total_chars": total_chars,
            "dialogue_ratio": round(dialogue_ratio, 3),
        }
    
    @staticmethod
    def analyze_sentence_length(text: str) -> Dict[str, float]:
        """
        分析句子长度
        
        Args:
            text: 待分析文本
        
        Returns:
            句子长度分析结果
        """
        # 按句号、问号、感叹号分割
        sentences = re.split(r'[。！？]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return {"avg_length": 0, "max_length": 0, "min_length": 0}
        
        lengths = [len(s) for s in sentences]
        
        return {
            "sentence_count": len(sentences),
            "avg_length": round(sum(lengths) / len(lengths), 2),
            "max_length": max(lengths),
            "min_length": min(lengths),
        }
    
    @staticmethod
    def full_analysis(text: str) -> Dict:
        """
        完整文本分析
        
        Args:
            text: 待分析文本
        
        Returns:
            完整分析结果
        """
        word_stats = TextAnalyzer.count_words(text)
        dialogue_stats = TextAnalyzer.analyze_dialogue(text)
        sentence_stats = TextAnalyzer.analyze_sentence_length(text)
        paragraph_count = TextAnalyzer.count_paragraphs(text)
        
        return {
            "word_stats": word_stats,
            "dialogue_stats": dialogue_stats,
            "sentence_stats": sentence_stats,
            "paragraph_count": paragraph_count,
        }
    
    @staticmethod
    def format_analysis_report(analysis: Dict) -> str:
        """
        格式化分析报告
        
        Args:
            analysis: 分析结果字典
        
        Returns:
            格式化的报告文本
        """
        word = analysis["word_stats"]
        dialogue = analysis["dialogue_stats"]
        sentence = analysis["sentence_stats"]
        
        lines = [
            "## 文本分析报告",
            "",
            "### 字数统计",
            f"- 总字符数: {word['total_chars']}",
            f"- 中文字符: {word['chinese_chars']}",
            f"- 英文单词: {word['english_words']}",
            f"- 估算字数: {word['estimated_words']}",
            "",
            "### 对话分析",
            f"- 对话次数: {dialogue['dialogue_count']}",
            f"- 对话占比: {dialogue['dialogue_ratio']*100:.1f}%",
            "",
            "### 句子分析",
            f"- 句子数量: {sentence['sentence_count']}",
            f"- 平均句长: {sentence['avg_length']}字",
            f"- 最长句子: {sentence['max_length']}字",
            f"- 最短句子: {sentence['min_length']}字",
            "",
            "### 段落统计",
            f"- 段落数量: {analysis['paragraph_count']}",
        ]
        
        return "\n".join(lines)


def word_counter(text: str) -> str:
    """
    字数统计工具函数（供 Agent 调用）
    
    Args:
        text: 待统计文本
    
    Returns:
        统计结果文本
    """
    analysis = TextAnalyzer.full_analysis(text)
    return TextAnalyzer.format_analysis_report(analysis)


if __name__ == '__main__':
    # 测试
    sample_text = """
    林渊推开房门，一股冷风扑面而来。他裹紧了外套，快步走向停车场。
    
    "林队，早啊！"苏晴从后面追上来，手里拿着一杯咖啡。
    
    "嗯。"林渊接过咖啡，喝了一口，"案件有新进展吗？"
    
    "第三个受害者的身份确认了，"苏晴压低声音，"是市公安局的副局长。"
    
    林渊的手顿了一下，咖啡差点洒出来。
    """
    
    print(word_counter(sample_text))
