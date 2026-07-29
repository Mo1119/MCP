# MCP Server Collection

我的个人 MCP 工具集，基于 [FastMCP](https://github.com/jlowin/fastmcp) 构建。

## 安装

```bash
pip install -e .
```

## 工具列表

| 工具名 | 描述 |
|--------|------|
| `get_current_time` | 获取当前日期和时间 |

## 在 Operit 中使用

配置类型选择 **Streamable HTTP**，运行服务后填入地址即可。

## 运行

```bash
python -m mcp_server.server
```

服务默认监听 `http://0.0.0.0:8000/mcp`。
