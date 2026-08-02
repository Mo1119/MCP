"""
MCP Server - 个人工具集（Cloud Edition）
基于 FastMCP，通过 Streamable HTTP 暴露服务
"""

import os
import base64
import json
import mimetypes
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

# ── MCP 实例 ──────────────────────────────
mcp = FastMCP(name="My MCP Server")

# ── 允许访问的目录（云服务器版）───────────
ALLOWED_DIRECTORIES = [
    "/opt/mcp",
    "/tmp",
    "/var/log",
    "/etc",
]

# ── 路径安全检查 ─────────────────────────
def _check_path(path: str) -> str:
    """检查路径是否在允许的目录内，返回绝对路径"""
    abs_path = os.path.abspath(os.path.expanduser(path))

    allowed = False
    for allowed_dir in ALLOWED_DIRECTORIES:
        allowed_abs = os.path.abspath(os.path.expanduser(allowed_dir))
        if abs_path == allowed_abs or abs_path.startswith(allowed_abs + os.sep):
            allowed = True
            break

    if not allowed:
        raise PermissionError(
            f"Access denied: '{path}' is outside allowed directories. "
            f"Allowed: {ALLOWED_DIRECTORIES}"
        )

    return abs_path

# ── 工具 1: get_time_info ────────────────
@mcp.tool()
def mcp__File__get_time_info() -> str:
    """获取当前日期和时间信息"""
    now = datetime.now()
    return json.dumps({
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "timestamp": int(now.timestamp()),
        "weekday": now.weekday(),
        "weekday_name": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()],
        "iso": now.isoformat(),
    }, ensure_ascii=False, indent=2)

# ── 工具read_file ─────────
@mcp.tool()
def mcp__File__read_file(path: str) -> str:
    """读取任意文件内容。文本文件返回原始文本，二进制文件返回 base64 编码"""
    abs_path = _check_path(path)

    if not os.path.exists(abs_path):
        return f"Error: file not found: {abs_path}"

    mime_type, _ = mimetypes.guess_type(abs_path)
    is_text = mime_type and (mime_type.startswith("text/") or mime_type in [
        "application/json", "application/xml", "application/javascript",
    ])

    if is_text:
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            is_text = False

    # 二进制文件 → base64
    with open(abs_path, "rb") as f:
        data = f.read()
    encoded = base64.b64encode(data).decode("ascii")
    return json.dumps({
        "type": "binary",
        "mime_type": mime_type or "application/octet-stream",
        "size": len(data),
        "base64": encoded,
    }, ensure_ascii=False)

# ── 工具read_text_file ────
@mcp.tool()
def mcp__File__read_text_file(path: str) -> str:
    """读取文本文件内容（仅文本文件）"""
    abs_path = _check_path(path)

    if not os.path.exists(abs_path):
        return f"Error: file not found: {abs_path}"

    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading text file: {e}"

# ── 工具read_media_file ────
@mcp.tool()
def mcp__File__read_media_file(path: str) -> str:
    """读取多媒体文件（图片、音频、视频等），返回 base64 编码及元信息"""
    abs_path = _check_path(path)

    if not os.path.exists(abs_path):
        return f"Error: file not found: {abs_path}"

    mime_type, _ = mimetypes.guess_type(abs_path)
    with open(abs_path, "rb") as f:
        data = f.read()

    encoded = base64.b64encode(data).decode("ascii")
    return json.dumps({
        "mime_type": mime_type or "application/octet-stream",
        "size": len(data),
        "base64": encoded,
    }, ensure_ascii=False)

# ── 工具read_multiple_files ─
@mcp.tool()
def mcp__File__read_multiple_files(paths: str) -> str:
    """批量读取多个文件。paths 为 JSON 数组字符串，如 '["/tmp/a.txt","/opt/mcp/b.txt"]'"""
    try:
        path_list = json.loads(paths)
    except json.JSONDecodeError:
        return "Error: paths must be a JSON array string"

    results = {}
    for p in path_list:
        try:
            abs_path = _check_path(p)
            if os.path.isfile(abs_path):
                with open(abs_path, "r", encoding="utf-8") as f:
                    results[p] = f.read()
            else:
                results[p] = f"Error: not a file or not found"
        except PermissionError as e:
            results[p] = str(e)
        except Exception as e:
            results[p] = f"Error: {e}"

    return json.dumps(results, ensure_ascii=False, indent=2)

# ── 工具write_file ─────────
@mcp.tool()
def mcp__File__write_file(path: str, content: str) -> str:
    """将内容写入文件（覆盖写入）。content 为要写入的文本内容"""
    abs_path = _check_path(path)

    parent_dir = os.path.dirname(abs_path)
    os.makedirs(parent_dir, exist_ok=True)

    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(content)

    return json.dumps({
        "success": True,
        "path": abs_path,
        "bytes_written": len(content.encode("utf-8")),
    }, ensure_ascii=False)

# ── 工具edit_file ──────────
@mcp.tool()
def mcp__File__edit_file(
    path: str,
    old_text: str,
    new_text: str,
    replace_all: bool = False,
) -> str:
    """编辑文件：将 old_text 替换为 new_text。replace_all=True 时替换全部匹配，否则仅替换第一处"""
    abs_path = _check_path(path)

    if not os.path.exists(abs_path):
        return f"Error: file not found: {abs_path}"

    with open(abs_path, "r", encoding="utf-8") as f:
        original = f.read()

    if old_text not in original:
        return f"Error: old_text not found in file"

    if replace_all:
        modified = original.replace(old_text, new_text)
    else:
        modified = original.replace(old_text, new_text, 1)

    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(modified)

    return json.dumps({
        "success": True,
        "path": abs_path,
        "replacements": original.count(old_text) if replace_all else 1,
    }, ensure_ascii=False)

# ── 工具create_directory ───
@mcp.tool()
def mcp__File__create_directory(path: str) -> str:
    """创建目录（自动创建所有父目录）"""
    abs_path = _check_path(path)

    os.makedirs(abs_path, exist_ok=True)

    return json.dumps({
        "success": True,
        "path": abs_path,
    }, ensure_ascii=False)

# ── 工具list_directory ─────
@mcp.tool()
def mcp__File__list_directory(path: str) -> str:
    """列出目录中的所有文件和子目录"""
    abs_path = _check_path(path)

    if not os.path.exists(abs_path):
        return f"Error: directory not found: {abs_path}"

    if not os.path.isdir(abs_path):
        return f"Error: not a directory: {abs_path}"

    entries = []
    try:
        for item in sorted(os.listdir(abs_path)):
            item_path = os.path.join(abs_path, item)
            entries.append({
                "name": item,
                "type": "directory" if os.path.isdir(item_path) else "file",
                "path": item_path,
            })
    except PermissionError:
        return f"Error: permission denied for: {abs_path}"

    return json.dumps(entries, ensure_ascii=False, indent=2)

# ── 工具list_directory_with_sizes ─
@mcp.tool()
def mcp__File__list_directory_with_sizes(path: str) -> str:
    """列出目录内容，包含每个文件的大小"""
    abs_path = _check_path(path)

    if not os.path.exists(abs_path):
        return f"Error: directory not found: {abs_path}"

    if not os.path.isdir(abs_path):
        return f"Error: not a directory: {abs_path}"

    entries = []
    try:
        for item in sorted(os.listdir(abs_path)):
            item_path = os.path.join(abs_path, item)
            stat = os.stat(item_path)
            entries.append({
                "name": item,
                "type": "directory" if os.path.isdir(item_path) else "file",
                "size": stat.st_size if os.path.isfile(item_path) else None,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "path": item_path,
            })
    except PermissionError:
        return f"Error: permission denied for: {abs_path}"

    return json.dumps(entries, ensure_ascii=False, indent=2)

# ── 工具directory_tree ────
@mcp.tool()
def mcp__File__directory_tree(
    path: str,
    max_depth: int = 3,
    show_hidden: bool = False,
) -> str:
    """生成目录树结构。max_depth 最大深度，show_hidden 是否显示隐藏文件"""
    abs_path = _check_path(path)

    if not os.path.exists(abs_path):
        return f"Error: directory not found: {abs_path}"

    if not os.path.isdir(abs_path):
        return f"Error: not a directory: {abs_path}"

    def _walk(dir_path: str, prefix: str = "", depth: int = 0) -> list[str]:
        if depth > max_depth:
            return [f"{prefix}..."]
        lines = []
        try:
            items = sorted(os.listdir(dir_path))
        except PermissionError:
            return [f"{prefix}[Permission denied]"]

        # 过滤隐藏文件
        if not show_hidden:
            items = [i for i in items if not i.startswith(".")]

        for i, item in enumerate(items):
            item_path = os.path.join(dir_path, item)
            is_last = (i == len(items) - 1)
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{item}")
            if os.path.isdir(item_path):
                extension_prefix = "    " if is_last else "│   "
                lines.extend(_walk(item_path, prefix + extension_prefix, depth + 1))
        return lines

    root_name = os.path.basename(abs_path) or abs_path
    tree_lines = [root_name] + _walk(abs_path)
    return "\n".join(tree_lines)

# ── 工具move_file ─────────
@mcp.tool()
def mcp__File__move_file(source: str, destination: str) -> str:
    """移动文件或目录（也可用于重命名）"""
    src_abs = _check_path(source)
    dst_abs = _check_path(destination)

    if not os.path.exists(src_abs):
        return f"Error: source not found: {src_abs}"

    dst_dir = os.path.dirname(dst_abs)
    os.makedirs(dst_dir, exist_ok=True)

    shutil.move(src_abs, dst_abs)

    return json.dumps({
        "success": True,
        "source": src_abs,
        "destination": dst_abs,
    }, ensure_ascii=False)

# ── 工具search_files ──────
@mcp.tool()
def mcp__File__search_files(
    path: str,
    pattern: str,
    case_sensitive: bool = False,
    max_depth: int = -1,
) -> str:
    """在目录中搜索匹配模式的文件。pattern 支持通配符（如 *.txt）"""
    abs_path = _check_path(path)

    if not os.path.exists(abs_path) or not os.path.isdir(abs_path):
        return f"Error: invalid directory: {abs_path}"

    results = []
    import fnmatch

    if case_sensitive:
        match = lambda name, pat: fnmatch.fnmatch(name, pat)
    else:
        match = lambda name, pat: fnmatch.fnmatch(name.lower(), pat.lower())

    for root, dirs, files in os.walk(abs_path):
        current_depth = root[len(abs_path):].count(os.sep)
        if max_depth >= 0 and current_depth > max_depth:
            continue

        # 过滤隐藏目录
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        for filename in files:
            if filename.startswith("."):
                continue
            if match(filename, pattern):
                full_path = os.path.join(root, filename)
                stat = os.stat(full_path)
                results.append({
                    "name": filename,
                    "path": full_path,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                })

    return json.dumps(results, ensure_ascii=False, indent=2)

# ── 工具get_file_info ─────
@mcp.tool()
def mcp__File__get_file_info(path: str) -> str:
    """获取文件或目录的详细信息"""
    abs_path = _check_path(path)

    if not os.path.exists(abs_path):
        return f"Error: path not found: {abs_path}"

    stat = os.stat(abs_path)
    mime_type, _ = mimetypes.guess_type(abs_path)

    info = {
        "path": abs_path,
        "name": os.path.basename(abs_path),
        "type": "directory" if os.path.isdir(abs_path) else "file",
        "size": stat.st_size if os.path.isfile(abs_path) else None,
        "mime_type": mime_type if os.path.isfile(abs_path) else None,
        "created": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "permissions": oct(stat.st_mode)[-3:],
    }

    return json.dumps(info, ensure_ascii=False, indent=2)

# ── 工具list_allowed_directories ─
@mcp.tool()
def mcp__File__list_allowed_directories() -> str:
    """列出当前允许访问的目录列表"""
    return json.dumps({
        "allowed_directories": [os.path.abspath(os.path.expanduser(d)) for d in ALLOWED_DIRECTORIES],
    }, ensure_ascii=False, indent=2)

# ── 入口 ──────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)