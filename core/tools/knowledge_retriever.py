"""
知识库检索工具
从本地知识库检索风格样本、类型模板等
"""
import os
from typing import List, Optional

from core.logger import Logger


_logger = Logger("knowledge_retriever")

# 知识库根目录
BASE_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOWLEDGE_DIR = os.path.join(BASE_PATH, "knowledge")


def knowledge_retriever(query: str, category: str = "style_samples", 
                       max_results: int = 3) -> str:
    """
    知识库检索工具函数
    
    Args:
        query: 检索关键词
        category: 知识库类别（style_samples/genre_templates/reference_works）
        max_results: 最大结果数
    
    Returns:
        检索到的文本内容
    """
    _logger.info(f"知识库检索: [{category}] {query}")
    
    category_dir = os.path.join(KNOWLEDGE_DIR, category)
    
    if not os.path.exists(category_dir):
        _logger.warning(f"知识库目录不存在: {category_dir}")
        return f"【知识库】类别 '{category}' 不存在，请先添加相关文件。"
    
    # 简单文件检索（基于文件名匹配）
    results = []
    
    for filename in os.listdir(category_dir):
        filepath = os.path.join(category_dir, filename)
        if os.path.isfile(filepath):
            # 检查文件名是否包含关键词
            if any(keyword in filename.lower() for keyword in query.lower().split()):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        results.append({
                            "filename": filename,
                            "content": content[:1000],  # 限制长度
                        })
                except Exception as e:
                    _logger.error(f"读取文件失败 {filepath}: {e}")
                
                if len(results) >= max_results:
                    break
    
    if not results:
        return f"【知识库】未找到与 '{query}' 相关的内容。"
    
    # 格式化输出
    output = [f"【知识库检索结果】查询: {query}\n"]
    for i, result in enumerate(results, 1):
        output.append(f"### 结果 {i}: {result['filename']}")
        output.append(result['content'])
        output.append("")
    
    return "\n".join(output)


def get_style_sample(style_name: str) -> str:
    """
    获取风格样本
    
    Args:
        style_name: 风格名称（如 "冷硬派"、"浪漫主义"）
    
    Returns:
        风格样本文本
    """
    return knowledge_retriever(style_name, "style_samples")


def get_genre_template(genre: str) -> str:
    """
    获取类型模板
    
    Args:
        genre: 类型名称（如 "悬疑"、"言情"、"科幻"）
    
    Returns:
        类型模板文本
    """
    return knowledge_retriever(genre, "genre_templates")


def get_reference_work(work_name: str) -> str:
    """
    获取参考作品摘要
    
    Args:
        work_name: 作品名称
    
    Returns:
        作品摘要文本
    """
    return knowledge_retriever(work_name, "reference_works")


def list_knowledge_files(category: str = None) -> List[str]:
    """
    列出知识库中的文件
    
    Args:
        category: 指定类别，None 表示所有类别
    
    Returns:
        文件名列表
    """
    files = []
    
    if category:
        dirs = [os.path.join(KNOWLEDGE_DIR, category)]
    else:
        dirs = [
            os.path.join(KNOWLEDGE_DIR, d)
            for d in os.listdir(KNOWLEDGE_DIR)
            if os.path.isdir(os.path.join(KNOWLEDGE_DIR, d))
        ]
    
    for dir_path in dirs:
        if os.path.exists(dir_path):
            for filename in os.listdir(dir_path):
                if os.path.isfile(os.path.join(dir_path, filename)):
                    files.append(filename)
    
    return files


if __name__ == '__main__':
    # 测试
    print("=== 知识库文件列表 ===")
    print(list_knowledge_files())
    
    print("\n=== 检索风格样本 ===")
    print(knowledge_retriever("冷硬派"))
