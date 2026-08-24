"""
配置管理模块

提供 INI 配置文件的读取、解析和运行时修改功能。
支持 LLM 配置（包括云端和本地模型）、Web 服务器配置等。
"""
import os
from configparser import ConfigParser
from typing import Optional
from core.agent_logger import logger


# 项目根目录和配置文件路径
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_PATH, "config.ini")


class ConfigManager:
    """
    配置管理器，封装 ConfigParser 提供类型安全的配置访问接口。
    支持运行时动态修改配置并持久化到文件。
    """
    
    def __init__(self, config_path: str = CONFIG_PATH):
        self.config_path = config_path
        self.config = ConfigParser()
        self._load_config()
    
    def _load_config(self) -> None:
        """加载配置文件"""
        if os.path.exists(self.config_path):
            self.config.read(self.config_path, encoding='utf-8')
            logger.debug(f"配置文件已加载: {self.config_path}")
        else:
            logger.warning(f"配置文件不存在: {self.config_path}")
    
    def get_llm_config(self) -> dict:
        """
        获取 LLM 配置。优先使用 Ollama 本地模型（当 [Ollama] enabled = true 时），
        否则使用 [LLM] 云端配置。API Key 从环境变量 LLM_API_KEY 读取。
        
        Returns:
            配置字典，包含 api_url、model_name、provider、temperature、top_p、api_key
        """
        ollama_config = self.get_ollama_config()
        ollama_config = self.get_ollama_config()
        if ollama_config.get('enabled', False):
            logger.info(f"使用 Ollama 本地模型: {ollama_config['model_name']}")
            return ollama_config
        
        # 从环境变量读取 API Key（安全考虑，不在配置文件中存储）
        api_key = os.environ.get("LLM_API_KEY")
        if not api_key:
            logger.warning("环境变量 LLM_API_KEY 未设置")
        
        # 读取配置文件中的 LLM 配置
        if 'LLM' in self.config:
            api_url = self.config.get('LLM', 'api_url')
            model_name = self.config.get('LLM', 'model_name')
            provider = self.config.get('LLM', 'provider', fallback='openai_compatible')
            temperature = self.config.getfloat('LLM', 'temperature', fallback=0.7)
            top_p = self.config.getfloat('LLM', 'top_p', fallback=0.9)
        else:
            # 默认配置
            api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
            model_name = "qwen-plus"
            provider = "openai_compatible"
            temperature = 0.7
            top_p = 0.9
        
        return {
            "api_url": api_url,
            "model_name": model_name,
            "provider": provider,
            "temperature": temperature,
            "top_p": top_p,
            "api_key": api_key or ""
        }
    
    def get_ollama_config(self) -> dict:
        """
        获取 Ollama 本地模型配置
        
        Ollama 不需要真实的 API Key，使用 "ollama" 作为占位符。
        Ollama 的 API 兼容 OpenAI 格式，通过 http://localhost:11434/v1 提供服务。
        
        Returns:
            配置字典，包含 api_url、model_name、provider、temperature、top_p、enabled、api_key
        """
        if 'Ollama' in self.config:
            api_url = self.config.get('Ollama', 'api_url', fallback='http://localhost:11434/v1')
            model_name = self.config.get('Ollama', 'model_name', fallback='qwen2.5')
            temperature = self.config.getfloat('Ollama', 'temperature', fallback=0.7)
            top_p = self.config.getfloat('Ollama', 'top_p', fallback=0.9)
            enabled = self.config.getboolean('Ollama', 'enabled', fallback=False)
        else:
            api_url = "http://localhost:11434/v1"
            model_name = "qwen2.5"
            temperature = 0.7
            top_p = 0.9
            enabled = False
        
        return {
            "api_url": api_url,
            "model_name": model_name,
            "provider": "ollama",
            "temperature": temperature,
            "top_p": top_p,
            "enabled": enabled,
            "api_key": "ollama"
        }
    
    def get_server_config(self) -> dict:
        """
        获取 Web 服务器配置
        
        Returns:
            配置字典，包含 port（端口号）和 auto_open_browser（是否自动打开浏览器）
        """
        if 'Web Server' in self.config:
            port = self.config.getint('Web Server', 'port', fallback=8000)
            auto_open_browser = self.config.getboolean('Web Server', 'auto_open_browser', fallback=True)
        else:
            port = 8000
            auto_open_browser = True
        
        return {
            "port": port,
            "auto_open_browser": auto_open_browser
        }
    
    def update_llm_config(self, api_url: Optional[str] = None, 
                          model_name: Optional[str] = None,
                          provider: Optional[str] = None,
                          temperature: Optional[float] = None,
                          top_p: Optional[float] = None) -> None:
        """
        运行时更新 LLM 配置，修改后立即持久化到 config.ini。
        仅更新传入的参数，未传入的保持不变。
        """
        if 'LLM' not in self.config:
            self.config.add_section('LLM')
        
        if api_url:
            self.config.set('LLM', 'api_url', api_url)
        if model_name:
            self.config.set('LLM', 'model_name', model_name)
        if provider:
            self.config.set('LLM', 'provider', provider)
        if temperature is not None:
            self.config.set('LLM', 'temperature', str(temperature))
        if top_p is not None:
            self.config.set('LLM', 'top_p', str(top_p))
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            self.config.write(f)
        
        logger.info("LLM 配置已更新")
    
    def update_server_config(self, port: Optional[int] = None,
                             auto_open_browser: Optional[bool] = None) -> None:
        """
        运行时更新 Web 服务器配置，修改后立即持久化到 config.ini。
        仅更新传入的参数，未传入的保持不变。
        """
        if 'Web Server' not in self.config:
            self.config.add_section('Web Server')
        
        if port is not None:
            self.config.set('Web Server', 'port', str(port))
        if auto_open_browser is not None:
            self.config.set('Web Server', 'auto_open_browser', str(auto_open_browser).lower())
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            self.config.write(f)
        
        logger.info("Web Server 配置已更新")
    
    def get_output_dir(self) -> str:
        """获取输出目录路径"""
        return os.path.join(BASE_PATH, "output")


# 全局配置管理器实例
config_manager = ConfigManager()


if __name__ == '__main__':
    # 测试代码
    config = config_manager.get_llm_config()
    print(f"LLM 配置: {config}")
