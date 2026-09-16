"""
降级管理器

当主 LLM 服务连续失败达到阈值时，自动降级到 Ollama 本地模型。
提供连续失败计数、降级触发判断和状态重置功能。
"""
from core.config_manager import config_manager
from core.agent_logger import logger


class FallbackManager:
    """
    降级管理器，跟踪连续失败次数并在达到阈值时触发降级。

    使用方式：
    - 每次 LLM 调用失败后调用 record_failure()
    - 每次 LLM 调用成功后调用 record_success()
    - 通过 should_fallback() 判断是否需要降级
    - 通过 get_fallback_config() 获取 Ollama 配置
    """

    def __init__(self):
        robustness = config_manager.get_robustness_config()
        self._threshold = robustness['fallback_threshold']
        self._consecutive_failures = 0
        self._is_degraded = False
        logger.debug(f"降级管理器已初始化（阈值: {self._threshold}）")

    def record_failure(self) -> None:
        """记录一次失败，累加连续失败计数"""
        self._consecutive_failures += 1
        logger.warning(
            f"LLM 调用失败（连续第 {self._consecutive_failures} 次，"
            f"阈值: {self._threshold}）"
        )

    def record_success(self) -> None:
        """记录一次成功，重置连续失败计数和降级状态"""
        if self._consecutive_failures > 0:
            logger.info(
                f"LLM 调用恢复，重置失败计数（之前连续失败 "
                f"{self._consecutive_failures} 次）"
            )
        self._consecutive_failures = 0
        self._is_degraded = False

    def should_fallback(self) -> bool:
        """判断是否应该降级到 Ollama"""
        return self._consecutive_failures >= self._threshold

    def activate_fallback(self) -> dict:
        """
        激活降级，返回 Ollama 配置

        Returns:
            Ollama 配置字典（与 get_llm_config() 返回格式一致）
        """
        self._is_degraded = True
        self._consecutive_failures = 0
        fallback_config = config_manager.get_ollama_config()
        logger.warning(
            f"降级已激活：切换到 Ollama 本地模型 "
            f"({fallback_config['model_name']})"
        )
        return fallback_config

    @property
    def is_degraded(self) -> bool:
        """当前是否处于降级状态"""
        return self._is_degraded

    def reset(self) -> None:
        """重置所有状态（用于用户手动切换模型后）"""
        self._consecutive_failures = 0
        self._is_degraded = False
        logger.debug("降级管理器已重置")


# 全局降级管理器实例
fallback_manager = FallbackManager()
