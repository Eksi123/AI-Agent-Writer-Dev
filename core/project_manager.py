"""
小说项目管理器
职责：
- 管理小说项目（创建、加载、列出）
- 管理大纲文件（outline.md）
- 管理章节文件（chapters/）
- 提供项目文件访问接口
"""
import os
from typing import List, Optional
from core.agent_logger import logger


class NovelProject:
    """
    小说项目类
    每个项目对应一个小说，包含大纲和章节文件
    """
    
    def __init__(self, project_name: str, base_dir: str):
        """
        初始化项目
        
        Args:
            project_name: 项目名称（小说名）
            base_dir: 项目根目录（output/{小说名}/）
        """
        self.name = project_name
        self.base_dir = base_dir
        self.outline_path = os.path.join(base_dir, "outline.md")
        self.chapters_dir = os.path.join(base_dir, "chapters")
    
    def ensure_dirs(self) -> None:
        """确保项目目录存在"""
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.chapters_dir, exist_ok=True)
    
    def has_outline(self) -> bool:
        """检查大纲文件是否存在"""
        return os.path.exists(self.outline_path)
    
    def read_outline(self) -> str:
        """读取大纲内容"""
        if not self.has_outline():
            return ""
        
        with open(self.outline_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def write_outline(self, content: str) -> None:
        """写入大纲内容"""
        with open(self.outline_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"大纲已更新: {self.outline_path}")
    
    def get_chapter_path(self, volume: int, chapter: int, chapter_name: str = "") -> str:
        """
        获取章节文件路径
        
        Args:
            volume: 卷号
            chapter: 章节号
            chapter_name: 章节名（可选）
        
        Returns:
            章节文件路径
        """
        # 确保卷目录存在
        vol_dir = os.path.join(self.chapters_dir, f"vol{volume}")
        os.makedirs(vol_dir, exist_ok=True)
        
        # 构建文件名
        if chapter_name:
            filename = f"vol{volume}_ch{chapter:02d}_{chapter_name}.md"
        else:
            filename = f"vol{volume}_ch{chapter:02d}.md"
        
        return os.path.join(vol_dir, filename)
    
    def read_chapter(self, volume: int, chapter: int, chapter_name: str = "") -> str:
        """读取章节内容"""
        chapter_path = self.get_chapter_path(volume, chapter, chapter_name)
        
        if not os.path.exists(chapter_path):
            return ""
        
        with open(chapter_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def write_chapter(self, volume: int, chapter: int, content: str, 
                     chapter_name: str = "") -> str:
        """
        写入章节内容
        
        Args:
            volume: 卷号
            chapter: 章节号
            content: 章节内容
            chapter_name: 章节名（可选）
        
        Returns:
            章节文件路径
        """
        chapter_path = self.get_chapter_path(volume, chapter, chapter_name)
        
        with open(chapter_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"章节已保存: {chapter_path}")
        return chapter_path
    
    def list_chapters(self) -> List[str]:
        """
        列出所有章节文件
        
        Returns:
            章节文件路径列表（按卷和章节排序）
        """
        if not os.path.exists(self.chapters_dir):
            return []
        
        chapters = []
        
        # 遍历所有卷目录
        for item in sorted(os.listdir(self.chapters_dir)):
            vol_path = os.path.join(self.chapters_dir, item)
            
            if os.path.isdir(vol_path) and item.startswith('vol'):
                # 遍历卷内的章节文件
                for chapter_file in sorted(os.listdir(vol_path)):
                    if chapter_file.endswith('.md'):
                        chapters.append(os.path.join(vol_path, chapter_file))
        
        return chapters


class ProjectManager:
    """
    项目管理器
    职责：
    - 创建新项目
    - 加载现有项目
    - 列出所有项目
    """
    
    def __init__(self, output_dir: str):
        """
        初始化项目管理器
        
        Args:
            output_dir: 输出目录（output/）
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def create_project(self, project_name: str) -> NovelProject:
        """
        创建新项目
        
        Args:
            project_name: 项目名称
        
        Returns:
            NovelProject 实例
        """
        project_dir = os.path.join(self.output_dir, project_name)
        project = NovelProject(project_name, project_dir)
        project.ensure_dirs()
        
        logger.info(f"项目已创建: {project_name}")
        return project
    
    def load_project(self, project_name: str) -> Optional[NovelProject]:
        """
        加载现有项目
        
        Args:
            project_name: 项目名称
        
        Returns:
            NovelProject 实例，项目不存在则返回 None
        """
        project_dir = os.path.join(self.output_dir, project_name)
        
        if not os.path.exists(project_dir):
            logger.warning(f"项目不存在: {project_name}")
            return None
        
        return NovelProject(project_name, project_dir)
    
    def list_projects(self) -> List[str]:
        """
        列出所有项目
        
        Returns:
            项目名称列表
        """
        if not os.path.exists(self.output_dir):
            return []
        
        projects = []
        
        for item in os.listdir(self.output_dir):
            item_path = os.path.join(self.output_dir, item)
            if os.path.isdir(item_path):
                projects.append(item)
        
        return sorted(projects)
    
    def project_exists(self, project_name: str) -> bool:
        """检查项目是否存在"""
        project_dir = os.path.join(self.output_dir, project_name)
        return os.path.exists(project_dir)


if __name__ == '__main__':
    # 测试代码
    from core.config import config_manager
    
    pm = ProjectManager(config_manager.get_output_dir())
    
    # 列出所有项目
    projects = pm.list_projects()
    print(f"现有项目: {projects}")
    
    # 创建新项目
    test_project = pm.create_project("测试小说")
    print(f"项目已创建: {test_project.name}")
    
    # 写入大纲
    test_project.write_outline("# 测试小说\n\n这是一个测试大纲。")
    
    # 写入章节
    test_project.write_chapter(1, 1, "# 第一章\n\n这是第一章的内容。", "初入江湖")
    
    # 列出章节
    chapters = test_project.list_chapters()
    print(f"章节列表: {chapters}")
