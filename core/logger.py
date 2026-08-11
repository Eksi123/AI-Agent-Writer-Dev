"""
日志模块
提供统一的日志记录功能，支持文件和控制台输出
"""
import logging
import os
import time
from typing import Optional


BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(BASE_PATH, "log")


class Logger:
    """
    日志记录器
    
    功能：
    - 同时输出到文件和控制台
    - 按日期自动分割日志文件
    - 支持不同级别的日志记录
    """
    
    _instances = {}  # 单例模式缓存
    
    def __new__(cls, name: str = "novel_writer"):
        """单例模式，确保同一名称的 logger 只创建一次"""
        if name not in cls._instances:
            instance = super().__new__(cls)
            instance._initialized = False
            cls._instances[name] = instance
        return cls._instances[name]
    
    def __init__(self, name: str = "novel_writer"):
        """
        初始化日志记录器
        
        Args:
            name: 日志记录器名称，用于区分不同模块的日志
        """
        if self._initialized:
            return
            
        # 确保日志目录存在
        if not os.path.exists(LOG_PATH):
            os.makedirs(LOG_PATH)
        
        # 日志文件名（按日期）
        self.log_name = os.path.join(LOG_PATH, f"{time.strftime('%Y%m%d')}.log")
        
        # 创建日志记录器
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 避免重复添加 handler
        if not self.logger.handlers:
            # 日志格式
            formatter = logging.Formatter(
                '[%(asctime)s][%(name)s][%(filename)s:%(lineno)d][%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # 文件处理器
            file_handler = logging.FileHandler(self.log_name, mode='a', encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            
            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            
            # 添加处理器
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
        
        self._initialized = True
    
    def debug(self, message: str):
        """记录 DEBUG 级别日志"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """记录 INFO 级别日志"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """记录 WARNING 级别日志"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """记录 ERROR 级别日志"""
        self.logger.error(message)
    
    def critical(self, message: str):
        """记录 CRITICAL 级别日志"""
        self.logger.critical(message)


# 全局默认 logger 实例
logger = Logger().logger


if __name__ == '__main__':
    # 测试日志记录
    logger.info("=== 日志系统测试开始 ===")
    logger.debug("这是一条 DEBUG 日志")
    logger.info("这是一条 INFO 日志")
    logger.warning("这是一条 WARNING 日志")
    logger.error("这是一条 ERROR 日志")
    logger.info("=== 日志系统测试结束 ===")



