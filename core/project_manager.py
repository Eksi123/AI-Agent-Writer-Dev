"""
小说项目管理器

管理小说项目的创建、加载和文件操作。
每个项目包含大纲文件（{小说名}.md）和章节目录（chapters/第一卷-xxx/）。

卷-章命名规则：
- 卷目录：第一卷-xxx（xxx为卷名，中划线分隔）
- 章节文件：第一卷_第1章_yyy.md（yyy为章节名，下划线分隔）
"""
import os
import re
import shutil
from typing import List, Optional, Tuple, Dict
from core.agent_logger import logger
from core.config_manager import config_manager


# 数字转中文
CN_NUMBERS = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
def num_to_cn(n: int) -> str:
    """将数字转换为中文（支持1-99）"""
    if n <= 10:
        return CN_NUMBERS[n]
    elif n < 20:
        return '十' + (CN_NUMBERS[n - 10] if n > 10 else '')
    elif n < 100:
        tens = n // 10
        ones = n % 10
        result = CN_NUMBERS[tens] + '十'
        if ones > 0:
            result += CN_NUMBERS[ones]
        return result
    return str(n)


# 命名规则校验
INVALID_CHARS = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '-', '_']
INVALID_CHARS_DESC = '/ \\ : * ? " < > | - _'

def validate_name(name: str, name_type: str = "名称") -> tuple:
    """
    校验卷名或章节名是否符合命名规则
    
    Args:
        name: 要校验的名称
        name_type: 名称类型（用于错误提示，如"卷名"或"章节名"）
    
    Returns:
        (is_valid, error_message): 校验是否通过，以及错误信息（如果失败）
    """
    if not name:
        return True, ""  # 空名称允许（使用默认命名）
    
    # 检查是否包含非法字符
    for char in INVALID_CHARS:
        if char in name:
            return False, f"{name_type}不能包含特殊字符：{INVALID_CHARS_DESC}"
    
    # 检查长度
    if len(name) > 50:
        return False, f"{name_type}长度不能超过50个字符"
    
    # 检查是否只包含空白字符
    if name.strip() == "":
        return False, f"{name_type}不能只包含空白字符"
    
    return True, ""


class NovelProject:
    """小说项目，管理大纲和章节文件的读写操作。"""
    
    def __init__(self, project_name: str, base_dir: str):
        """
        初始化项目
        
        Args:
            project_name: 项目名称（小说名）
            base_dir: 项目根目录（output/{小说名}/）
        """
        self.name = project_name
        self.base_dir = base_dir
        self.outline_path = os.path.join(base_dir, f"{project_name}.md")
        self.chapters_dir = os.path.join(base_dir, "chapters")
    
    @staticmethod
    def _vol_dir_name(volume: int, vol_name: str = "") -> str:
        """
        生成卷目录名
        
        固定格式：第x卷-yyyy
        x: 中文数字（一二三...）
        yyyy: 卷名
        """
        cn_num = num_to_cn(volume)
        
        if vol_name:
            return f"第{cn_num}卷-{vol_name}"
        else:
            return f"第{cn_num}卷"
    
    @staticmethod
    def _chapter_filename(volume: int, chapter: int, chapter_name: str = "") -> str:
        """
        生成章节文件名
        
        固定格式：第x章-zzz.md
        x: 阿拉伯数字（1,2,3...）
        zzz: 章节名
        """
        if chapter_name:
            return f"第{chapter}章-{chapter_name}.md"
        else:
            return f"第{chapter}章.md"
    
    @staticmethod
    def _parse_vol_dir(dir_name: str) -> Tuple[int, str]:
        """
        解析卷目录名，返回 (卷号, 卷名)
        
        固定格式：第x卷-yyyy
        x: 中文数字（一二三...）
        yyyy: 卷名（可选）
        
        兼容旧格式：
        - 第X卷_xxx（_分隔）
        - vol1
        """
        # 固定格式：第X卷-xxx（-分隔）
        match = re.match(r'第([一二三四五六七八九十百]+)卷(?:-(.*))?', dir_name)
        if match:
            cn_num = match.group(1)
            vol_name = match.group(2) or ""
            vol_num = NovelProject._cn_to_num(cn_num)
            return vol_num, vol_name
        
        # 兼容旧格式：第X卷_xxx（_分隔）
        match = re.match(r'第([一二三四五六七八九十百]+)卷(?:_(.*))?', dir_name)
        if match:
            cn_num = match.group(1)
            vol_name = match.group(2) or ""
            vol_num = NovelProject._cn_to_num(cn_num)
            return vol_num, vol_name
        
        # 兼容旧格式：vol1
        match = re.match(r'vol(\d+)', dir_name)
        if match:
            return int(match.group(1)), ""
        
        return 0, ""
    
    @staticmethod
    def _parse_chapter_file(filename: str) -> Tuple[int, str]:
        """
        解析章节文件名，返回 (章节号, 章节名)
        
        固定格式：第x章-yyyy.md
        x: 阿拉伯数字（1,2,3...）
        yyyy: 章节名（可选）
        
        兼容旧格式：
        - 第X卷_第Y章_xxx.md
        - vol1_ch01_xxx.md
        """
        name = filename.replace('.md', '')
        
        # 固定格式：第X章_xxx（-分隔）
        match = re.match(r'第(\d+)章(?:-(.*))?', name)
        if match:
            ch_num = int(match.group(1))
            ch_name = match.group(2) or ""
            return ch_num, ch_name
        
        # 兼容旧格式：第X卷_第Y章_xxx
        match = re.match(r'第[一二三四五六七八九十百]+卷_第(\d+)章(?:[_-](.*))?', name)
        if match:
            ch_num = int(match.group(1))
            ch_name = match.group(2) or ""
            return ch_num, ch_name
        
        # 兼容旧格式：vol1_ch01_xxx
        match = re.match(r'vol\d+_ch(\d+)(?:[_-](.*))?', name)
        if match:
            ch_num = int(match.group(1))
            ch_name = match.group(2) or ""
            return ch_num, ch_name
        
        return 0, ""
    
    @staticmethod
    def _cn_to_num(cn: str) -> int:
        """中文数字转阿拉伯数字"""
        # 简单的中文数字转换，支持1-99
        cn_map = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, 
                  '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
        
        if cn in cn_map:
            return cn_map[cn]
        
        # 处理十几
        if cn.startswith('十'):
            if len(cn) == 1:
                return 10
            return 10 + cn_map.get(cn[1], 0)
        
        # 处理几十几
        if '十' in cn:
            parts = cn.split('十')
            tens = cn_map.get(parts[0], 0) * 10
            ones = cn_map.get(parts[1], 0) if len(parts) > 1 else 0
            return tens + ones
        
        return 0
    
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
    
    def _find_vol_dir(self, volume: int) -> Optional[str]:
        """查找指定卷号的目录路径，无论其命名格式如何"""
        if not os.path.exists(self.chapters_dir):
            return None
        for vol_dir_name in os.listdir(self.chapters_dir):
            vol_path = os.path.join(self.chapters_dir, vol_dir_name)
            if os.path.isdir(vol_path):
                vol_num, _ = self._parse_vol_dir(vol_dir_name)
                if vol_num == volume:
                    return vol_path
        return None
    
    def get_chapter_path(self, volume: int, chapter: int, chapter_name: str = "") -> str:
        """
        获取章节文件路径，自动创建卷目录。
        
        新命名规则：
        - 卷目录：第一卷-xxx（中划线分隔）
        - 章节文件：第一卷_第1章_yyy.md（下划线分隔）
        
        优先使用已存在的卷目录（保留卷名），找不到时才创建裸目录。
        
        Args:
            volume: 卷号
            chapter: 章节号
            chapter_name: 章节名（可选）
        
        Returns:
            章节文件的完整路径
        """
        # 优先使用已存在的卷目录
        vol_path = self._find_vol_dir(volume)
        if vol_path is None:
            vol_path = os.path.join(self.chapters_dir, self._vol_dir_name(volume, ""))
            os.makedirs(vol_path, exist_ok=True)
        
        filename = self._chapter_filename(volume, chapter, chapter_name)
        return os.path.join(vol_path, filename)
    
    def find_chapter_path(self, volume: int, chapter: int) -> Optional[str]:
        """
        查找已存在的章节文件（不依赖章节名）
        
        Args:
            volume: 卷号
            chapter: 章节号
        
        Returns:
            章节文件路径，不存在返回 None
        """
        # 遍历 chapters 目录，查找匹配的卷和章节
        if not os.path.exists(self.chapters_dir):
            return None
        
        for vol_dir_name in os.listdir(self.chapters_dir):
            vol_path = os.path.join(self.chapters_dir, vol_dir_name)
            if not os.path.isdir(vol_path):
                continue
            
            vol_num, _ = self._parse_vol_dir(vol_dir_name)
            if vol_num != volume:
                continue
            
            # 在该卷目录下查找匹配的章节
            for ch_file in os.listdir(vol_path):
                if not ch_file.endswith('.md'):
                    continue
                
                ch_num, _ = self._parse_chapter_file(ch_file)
                if ch_num == chapter:
                    return os.path.join(vol_path, ch_file)
        
        return None
    
    def read_chapter(self, volume: int, chapter: int, chapter_name: str = "") -> str:
        """读取章节内容"""
        # 先尝试查找已存在的文件
        chapter_path = self.find_chapter_path(volume, chapter)
        if chapter_path and os.path.exists(chapter_path):
            with open(chapter_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        # 如果不存在，使用 get_chapter_path 生成路径
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
        列出所有章节文件路径，按卷号和章节号排序。
        """
        if not os.path.exists(self.chapters_dir):
            return []
        
        chapters = []
        
        for vol_dir_name in sorted(os.listdir(self.chapters_dir)):
            vol_path = os.path.join(self.chapters_dir, vol_dir_name)
            
            if os.path.isdir(vol_path):
                for chapter_file in sorted(os.listdir(vol_path)):
                    if chapter_file.endswith('.md'):
                        chapters.append(os.path.join(vol_path, chapter_file))
        
        return chapters
    
    def get_chapter_tree(self) -> List[Dict]:
        """
        获取章节目录树，按卷分组，包含每个章节的前100字预览
        
        Returns:
            [
                {
                    "volume": 1,
                    "volume_name": "命运的邂逅",
                    "volume_dir": "第一卷_命运的邂逅",
                    "chapters": [
                        {
                            "chapter": 1,
                            "chapter_name": "初入江湖",
                            "file": "第一卷_命运的邂逅/第一卷_第1章_初入江湖.md",
                            "preview": "..."
                        }
                    ]
                }
            ]
        """
        tree = []
        
        if not os.path.exists(self.chapters_dir):
            return tree
        
        # 收集所有卷
        volumes = []
        for vol_dir_name in os.listdir(self.chapters_dir):
            vol_path = os.path.join(self.chapters_dir, vol_dir_name)
            if not os.path.isdir(vol_path):
                continue
            
            vol_num, vol_name = self._parse_vol_dir(vol_dir_name)
            if vol_num > 0:
                volumes.append((vol_num, vol_name, vol_dir_name, vol_path))
        
        # 按卷号排序
        volumes.sort(key=lambda x: x[0])
        
        for vol_num, vol_name, vol_dir_name, vol_path in volumes:
            chapters = []
            
            # 收集该卷下的所有章节
            for ch_file in os.listdir(vol_path):
                if not ch_file.endswith('.md'):
                    continue
                
                ch_num, ch_name = self._parse_chapter_file(ch_file)
                
                # 读取前100字作为预览
                ch_path = os.path.join(vol_path, ch_file)
                preview = ''
                try:
                    with open(ch_path, 'r', encoding='utf-8') as f:
                        preview = f.read(100)
                except Exception:
                    pass
                
                chapters.append({
                    'chapter': ch_num,
                    'chapter_name': ch_name,
                    'file': f"{vol_dir_name}/{ch_file}",
                    'preview': preview
                })
            
            # 按章节号排序
            chapters.sort(key=lambda x: x['chapter'])
            
            tree.append({
                'volume': vol_num,
                'volume_name': vol_name,
                'volume_dir': vol_dir_name,
                'chapters': chapters
            })
        
        return tree
    
    def create_volume(self, vol_name: str = "", volume: int = None) -> int:
        """
        创建新卷
        
        Args:
            vol_name: 卷名（可选）
            volume: 卷序号（可选，如果不指定则自动递增）
        
        Returns:
            新卷的卷号
        
        Raises:
            ValueError: 卷名不符合命名规则
        """
        # 验证卷名
        is_valid, error_msg = validate_name(vol_name, "卷名")
        if not is_valid:
            raise ValueError(error_msg)
        
        # 如果用户指定了卷序号，使用该序号
        if volume is not None:
            new_vol = volume
        else:
            # 否则获取当前最大卷号并递增
            max_vol = 0
            if os.path.exists(self.chapters_dir):
                for vol_dir_name in os.listdir(self.chapters_dir):
                    vol_path = os.path.join(self.chapters_dir, vol_dir_name)
                    if os.path.isdir(vol_path):
                        vol_num, _ = self._parse_vol_dir(vol_dir_name)
                        if vol_num > max_vol:
                            max_vol = vol_num
            
            new_vol = max_vol + 1
        
        vol_dir_name = self._vol_dir_name(new_vol, vol_name)
        vol_path = os.path.join(self.chapters_dir, vol_dir_name)
        os.makedirs(vol_path, exist_ok=True)
        
        logger.info(f"已创建卷: {vol_dir_name}")
        return new_vol
    
    def delete_volume(self, volume: int) -> bool:
        """
        删除指定卷及其所有章节
        
        Args:
            volume: 卷号
        
        Returns:
            是否成功删除
        """
        if not os.path.exists(self.chapters_dir):
            return False
        
        # 查找对应的卷目录
        for vol_dir_name in os.listdir(self.chapters_dir):
            vol_path = os.path.join(self.chapters_dir, vol_dir_name)
            if not os.path.isdir(vol_path):
                continue
            
            vol_num, _ = self._parse_vol_dir(vol_dir_name)
            if vol_num == volume:
                shutil.rmtree(vol_path)
                logger.info(f"已删除卷: {vol_dir_name}")
                return True
        
        return False
    
    def rename_volume(self, volume: int, new_name: str) -> bool:
        """
        重命名卷
        
        Args:
            volume: 卷号
            new_name: 新卷名
        
        Returns:
            是否成功重命名
        
        Raises:
            ValueError: 卷名不符合命名规则
        """
        # 验证卷名
        is_valid, error_msg = validate_name(new_name, "卷名")
        if not is_valid:
            raise ValueError(error_msg)
        
        if not os.path.exists(self.chapters_dir):
            return False
        
        # 查找对应的卷目录
        for vol_dir_name in os.listdir(self.chapters_dir):
            vol_path = os.path.join(self.chapters_dir, vol_dir_name)
            if not os.path.isdir(vol_path):
                continue
            
            vol_num, _ = self._parse_vol_dir(vol_dir_name)
            if vol_num == volume:
                new_dir_name = self._vol_dir_name(volume, new_name)
                new_vol_path = os.path.join(self.chapters_dir, new_dir_name)
                
                if vol_path != new_vol_path:
                    os.rename(vol_path, new_vol_path)
                    logger.info(f"已重命名卷: {vol_dir_name} → {new_dir_name}")
                
                return True
        
        return False
    
    def create_chapter(self, volume: int, chapter_name: str = "", chapter: int = None) -> int:
        """
        在指定卷下创建新章节
        
        Args:
            volume: 卷号
            chapter_name: 章节名（可选）
            chapter: 章节序号（可选，如果不指定则自动递增）
        
        Returns:
            新章节的章节号
        
        Raises:
            ValueError: 章节名不符合命名规则
        """
        # 验证章节名
        is_valid, error_msg = validate_name(chapter_name, "章节名")
        if not is_valid:
            raise ValueError(error_msg)
        
        # 如果用户指定了章节序号，使用该序号
        if chapter is not None:
            new_ch = chapter
        else:
            # 否则获取该卷下当前最大章节号并递增
            max_ch = 0
            
            if os.path.exists(self.chapters_dir):
                for vol_dir_name in os.listdir(self.chapters_dir):
                    vol_path = os.path.join(self.chapters_dir, vol_dir_name)
                    if not os.path.isdir(vol_path):
                        continue
                    
                    vol_num, _ = self._parse_vol_dir(vol_dir_name)
                    if vol_num != volume:
                        continue
                    
                    for ch_file in os.listdir(vol_path):
                        if not ch_file.endswith('.md'):
                            continue
                        
                        ch_num, _ = self._parse_chapter_file(ch_file)
                        if ch_num > max_ch:
                            max_ch = ch_num
            
            new_ch = max_ch + 1
        
        # 确保卷目录存在：优先使用已有目录，找不到时再创建
        vol_path = None
        if os.path.exists(self.chapters_dir):
            for vol_dir_name in os.listdir(self.chapters_dir):
                candidate = os.path.join(self.chapters_dir, vol_dir_name)
                if os.path.isdir(candidate):
                    vol_num, _ = self._parse_vol_dir(vol_dir_name)
                    if vol_num == volume:
                        vol_path = candidate
                        break
        
        if vol_path is None:
            vol_dir_name = self._vol_dir_name(volume, "")
            vol_path = os.path.join(self.chapters_dir, vol_dir_name)
            os.makedirs(vol_path, exist_ok=True)
        
        # 创建空的章节文件
        filename = self._chapter_filename(volume, new_ch, chapter_name)
        ch_path = os.path.join(vol_path, filename)
        with open(ch_path, 'w', encoding='utf-8') as f:
            f.write(f"# 第{new_ch}章 {chapter_name}\n\n")
        
        logger.info(f"已创建章节: {filename}")
        return new_ch
    
    def delete_chapter(self, volume: int, chapter: int) -> bool:
        """
        删除指定章节
        
        Args:
            volume: 卷号
            chapter: 章节号
        
        Returns:
            是否成功删除
        """
        ch_path = self.find_chapter_path(volume, chapter)
        if ch_path and os.path.exists(ch_path):
            os.remove(ch_path)
            logger.info(f"已删除章节: {ch_path}")
            return True
        
        return False
    
    def rename_chapter(self, volume: int, chapter: int, new_name: str) -> bool:
        """
        重命名章节
        
        Args:
            volume: 卷号
            chapter: 章节号
            new_name: 新章节名
        
        Returns:
            是否成功重命名
        
        Raises:
            ValueError: 章节名不符合命名规则
        """
        # 验证章节名
        is_valid, error_msg = validate_name(new_name, "章节名")
        if not is_valid:
            raise ValueError(error_msg)
        
        ch_path = self.find_chapter_path(volume, chapter)
        if not ch_path or not os.path.exists(ch_path):
            return False
        
        vol_dir = os.path.dirname(ch_path)
        new_filename = self._chapter_filename(volume, chapter, new_name)
        new_ch_path = os.path.join(vol_dir, new_filename)
        
        if ch_path != new_ch_path:
            os.rename(ch_path, new_ch_path)
            logger.info(f"已重命名章节: {os.path.basename(ch_path)} → {new_filename}")
        
        return True


class ProjectManager:
    """项目管理器，提供项目的创建、加载和列出操作。"""
    
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
