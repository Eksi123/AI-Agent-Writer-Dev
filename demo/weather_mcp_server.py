"""
自建 Weather MCP Server（仿照 demo-langchain.py 的 get_weather 工具）

核心概念：
- MCP Server：把「工具」独立成一个进程，通过 MCP 协议对外暴露
- FastMCP：官方高层封装，用 @mcp.tool() 装饰器把普通 Python 函数注册为 MCP 工具，
  函数签名（类型注解）+ docstring 会自动转换成 LLM 可读的 JSON Schema
- stdio 传输：Server 作为子进程启动，Client 通过标准输入/输出收发 JSON-RPC 消息

独立运行（手动验证协议握手）：
    python demo/weather_mcp_server.py

⚠️ stdio 模式下 stdout 被 MCP 协议独占，任何 print() 都会破坏 JSON-RPC 报文。
   因此日志一律输出到 stderr。
"""

import sys
import json
import logging

from mcp.server.fastmcp import FastMCP

# Windows 控制台默认 GBK，天气数据含中文与 emoji，统一切到 UTF-8 并容错，避免编码崩溃
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# 日志只能走 stderr（stdout 是 MCP 协议通道）
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="[weather-mcp] %(message)s",
)
logger = logging.getLogger("weather-mcp")

# 1. 创建 MCP Server 实例（name 会在握手时告知 Client）
mcp = FastMCP("self-built-weather-server")

# Mock 天气数据（与 demo-langchain.py 的 get_weather 保持一致）
MOCK_WEATHER = {
    "北京": {"天气": "晴", "温度": "25°C", "湿度": "40%", "风力": "微风"},
    "上海": {"天气": "多云", "温度": "22°C", "湿度": "65%", "风力": "东南风3级"},
    "广州": {"天气": "小雨", "温度": "28°C", "湿度": "80%", "风力": "南风2级"},
    "深圳": {"天气": "阴", "温度": "26°C", "湿度": "70%", "风力": "东风2级"},
}

UNKNOWN = {"天气": "未知", "温度": "N/A", "湿度": "N/A", "风力": "N/A"}


# 2. 注册工具：类型注解 -> 参数 Schema，docstring -> 工具描述
@mcp.tool()
def get_weather(city: str) -> str:
    """查询指定城市的天气信息（Mock 数据）。

    Args:
        city: 城市名称，如：北京、上海、广州、深圳
    """
    data = MOCK_WEATHER.get(city, UNKNOWN)
    result = {"城市": city, "数据源": "self-built-mcp(mock)", **data}
    logger.info("get_weather called: city=%s hit=%s", city, city in MOCK_WEATHER)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def list_supported_cities() -> str:
    """列出当前天气服务支持查询的所有城市名称。"""
    cities = list(MOCK_WEATHER.keys())
    logger.info("list_supported_cities called: %d cities", len(cities))
    return json.dumps(
        {"支持城市": cities, "数量": len(cities)},
        ensure_ascii=False,
    )


@mcp.tool()
def compare_weather(city_a: str, city_b: str) -> str:
    """对比两个城市的天气，返回温度更高、湿度更大的城市。

    Args:
        city_a: 第一个城市名称
        city_b: 第二个城市名称
    """
    a = MOCK_WEATHER.get(city_a)
    b = MOCK_WEATHER.get(city_b)

    if a is None or b is None:
        missing = [c for c, d in ((city_a, a), (city_b, b)) if d is None]
        return json.dumps(
            {"error": f"不支持的城市: {missing}", "支持城市": list(MOCK_WEATHER.keys())},
            ensure_ascii=False,
        )

    def _num(text: str) -> float:
        """从 '25°C' / '40%' 中取出数字部分"""
        digits = "".join(ch for ch in text if ch.isdigit() or ch == ".")
        return float(digits) if digits else 0.0

    hotter = city_a if _num(a["温度"]) >= _num(b["温度"]) else city_b
    wetter = city_a if _num(a["湿度"]) >= _num(b["湿度"]) else city_b

    logger.info("compare_weather called: %s vs %s", city_a, city_b)
    return json.dumps(
        {
            city_a: a,
            city_b: b,
            "更温暖": hotter,
            "更潮湿": wetter,
        },
        ensure_ascii=False,
    )


if __name__ == "__main__":
    logger.info("tools registered: get_weather, list_supported_cities, compare_weather")
    # 3. 以 stdio 模式启动：阻塞运行，等待 Client 通过标准输入发送 JSON-RPC 请求
    mcp.run(transport="stdio")
