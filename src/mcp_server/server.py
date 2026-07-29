"""
MCP Server - 个人工具集
基于 FastMCP，通过 Streamable HTTP 暴露服务
"""

from datetime import datetime

from fastmcp import FastMCP

# 创建 MCP 实例
mcp = FastMCP(name="My MCP Server")


# ── 工具定义 ──────────────────────────────

@mcp.tool()
def get_current_time() -> str:
    """获取当前日期和时间，返回 ISO 格式的时间字符串"""
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


# ── 入口 ──────────────────────────────────

if __name__ == "__main__":
    # Streamable HTTP 模式，监听所有网卡
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
