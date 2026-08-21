"""
配置管理模块
职责：
- 读取和管理 config.ini 配置
- 支持运行时动态修改 LLM 配置
- 管理环境变量（如 API Key）
"""
import os
from configparser import ConfigParser
from typing import Optional
from core.agent_logger import logger


# 配置文件路径
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_PATH, "config.ini")


class ConfigManager:
    """
    配置管理器
    职责：
    - 读取配置文件
    - 提供配置访问接口
    - 支持运行时修改配置
    """
    
    def __init__(self, config_path: str = CONFIG_PATH):
        self.config_path = config_path
        self.config = ConfigParser()
        self._load_config()
    
    def _load_config(self) -> None:
        """加载配置文件"""
        if os.path.exists(self.config_path):
            self.config.read(self.config_path, encoding='UTF-8')
            logger.debug(f"配置文件已加载: {self.config_path}")
        else:
            logger.warning(f"配置文件不存在: {self.config_path}")
    
    def get_llm_config(self) -> dict:
        """
        获取 LLM 配置
        
        Returns:
            {
                "base_url": str,
                "model": str,
                "api_key": str,
                "temperature": float
            }
        """
        # 从环境变量读取 API Key（安全考虑，不在配置文件中存储）
        api_key = os.environ.get("LLM_API_KEY")
        if not api_key:
            logger.warning("环境变量 LLM_API_KEY 未设置")
        
        # 读取配置文件中的 LLM 配置
        # 兼容旧的配置格式（llm_api_aliyun section）
        if 'llm_api_aliyun' in self.config:
            base_url = self.config.get('llm_api_aliyun', 'base_url')
            model = self.config.get('llm_api_aliyun', 'model')
        elif 'LLM' in self.config:
            base_url = self.config.get('LLM', 'api_url')
            model = self.config.get('LLM', 'model_name')
        else:
            # 默认配置
            base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
            model = "qwen-plus"
        
        # 读取 temperature（如果有）
        temperature = 0.7
        if 'LLM' in self.config and self.config.has_option('LLM', 'temperature'):
            temperature = self.config.getfloat('LLM', 'temperature')
        
        return {
            "base_url": base_url,
            "model": model,
            "api_key": api_key or "",
            "temperature": temperature
        }
    
    def update_llm_config(self, base_url: Optional[str] = None, 
                          model: Optional[str] = None,
                          temperature: Optional[float] = None) -> None:
        """
        更新 LLM 配置（运行时修改）
        
        Args:
            base_url: 新的 API URL
            model: 新的模型名称
            temperature: 新的温度参数
        """
        if 'LLM' not in self.config:
            self.config.add_section('LLM')
        
        if base_url:
            self.config.set('LLM', 'api_url', base_url)
        if model:
            self.config.set('LLM', 'model_name', model)
        if temperature is not None:
            self.config.set('LLM', 'temperature', str(temperature))
        
        # 保存到文件
        with open(self.config_path, 'w', encoding='UTF-8') as f:
            self.config.write(f)
        
        logger.info("LLM 配置已更新")
    
    def get_output_dir(self) -> str:
        """获取输出目录路径"""
        return os.path.join(BASE_PATH, "output")


# 全局配置管理器实例
config_manager = ConfigManager()


if __name__ == '__main__':
    # 测试代码
    config = config_manager.get_llm_config()
    print(f"LLM 配置: {config}")
