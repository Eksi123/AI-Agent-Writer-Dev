"""自建天气 MCP 服务端（本地，stdio 传输）"""

import logging
import sys
from datetime import date

from pydantic import BaseModel

from mcp.server import MCPServer

# stdio 模式下 stdout 被 JSON-RPC 报文独占，任何 print() 都会破坏协议，日志一律写 stderr
# Windows 下 stdout 默认 GBK，中文会写坏报文，必须切 UTF-8
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")
logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="[weather-server] %(message)s")
logger = logging.getLogger("weather-server")

# 1. 创建 Server（name / version 会在握手时告诉客户端）
mcp = MCPServer("local-weather-server", version="1.0.0")

MOCK_WEATHER = {
    "北京": ("晴", 25, 40),
    "上海": ("多云", 22, 65),
}


class Weather(BaseModel):
    """返回类型声明成 Pydantic 模型，客户端就能直接拿到 structured_content。"""

    city: str
    date: str
    condition: str
    temp_c: int
    humidity_pct: int


# 2. 注册工具
@mcp.tool()
def get_weather(city: str) -> Weather:
    """查询指定城市当天的天气信息。

    Args:
        city: 城市名称，如：北京、上海
    """
    logger.info("get_weather called: city=%s", city)
    condition, temp, humidity = MOCK_WEATHER.get(city, ("未知", 0, 0))
    return Weather(city=city, date=date.today().isoformat(), condition=condition,
                   temp_c=temp, humidity_pct=humidity)


@mcp.tool()
def list_supported_cities() -> list[str]:
    """列出当前服务支持查询的所有城市。"""
    return list(MOCK_WEATHER)


# 3. 以 stdio 方式对外服务
if __name__ == "__main__":
    mcp.run(transport="stdio")
