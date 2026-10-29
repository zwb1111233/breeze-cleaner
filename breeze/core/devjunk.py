"""开发垃圾识别：node_modules、__pycache__、虚拟环境等可重建目录。

「智能」之处：笼统的名字（build / dist / target / venv）必须先验证项目标记文件
（如 Cargo.toml、package.json、pyvenv.cfg）才会被认定，避免误伤普通文件夹。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .safety import dir_size, is_reparse_point
from .scanner import CleanItem, RuleResult

# 目录名 → 需要在父目录确认的标记文件（None 表示目录名本身已足够明确）
DEV_DIRS: dict[str, tuple[str, ...] | None] = {
    "node_modules": None,
    "__pycache__": None,
    ".pytest_cache": None,
    ".mypy_cache": None,
    ".ruff_cache": None,
    ".tox": None,
    ".venv": None,
    ".next": None,
    ".nuxt": None,
    ".turbo": None,
    ".parcel-cache": None,
    ".gradle": None,
    "target": ("Cargo.toml",),
    "build": ("pyproject.toml", "setup.py", "package.json", "Cargo.toml", "CMakeLists.txt", "meson.build"),
    "dist": ("pyproject.toml", "setup.py", "package.json", "Cargo.toml"),
    "obj": ("*.csproj", "*.vcxproj", "*.sln"),
}

# venv / env 这类目录必须在自己内部找到 pyvenv.cfg 才算虚拟环境
_INSIDE_MARKER = {"venv": "pyvenv.cfg", "env": "pyvenv.cfg"}

# 扫描整个用户目录时跳过的顶层目录
HOME_EXCLUDES = {
    "AppData", "Windows", "Program Files", "Program Files (x86)",
    "ProgramData", "$Recycle.Bin", "System Volume Information",
    "OneDriveTemp", "Recovery", "PerfLogs",
}


def is_dev_dir(d: Path) -> bool:
    name = d.name
    if name in _INSIDE_MARKER:
        return (d / _INSIDE_MARKER[name]).exists()
    markers = DEV_DIRS.get(name)
    if markers is None:
        return name in DEV_DIRS
    parent = d.parent
    for m in markers:
        if m.startswith("*."):
            try:
                if any(parent.glob(m)):
                    return True
            except OSError:
                pass
        elif (parent / m).exists():
            return True
    return False


@dataclass
class DevJunkItem:
    path: Path
    kind: str
    size: int
    file_count: int


def scan_dev_junk(root: Path, max_depth: int = 6, excludes: set[str] | None = None,
                  cancel=None, progress=None, skip_hidden_root: bool = True) -> list[DevJunkItem]:
    found: list[DevJunkItem] = []
    scanned = 0
    excludes = excludes or set()
    stack: list[tuple[Path, int]] = [(root, 0)]
    while stack:
        cur, depth = stack.pop()
        if cancel is not None and cancel.is_set():
            break
        try:
            entries = list(os.scandir(cur))
        except OSError:
            continue
        for e in entries:
            scanned += 1
            if progress and scanned % 500 == 0:
                progress(f"开发垃圾：已检查 {scanned} 个目录")
            try:
                if not e.is_dir(follow_symlinks=False):
                    continue
            except OSError:
                continue
            full = Path(e.path)
            if is_reparse_point(full):
                continue
            if cur == root:
                # 根目录下的隐藏目录（.cache、.vscode 等）多为工具自身的运行时/配置，
                # 里面的 node_modules、dist 不应被当成垃圾，跳过
                if e.name in excludes:
                    continue
                if skip_hidden_root and e.name.startswith("."):
                    continue
            if is_dev_dir(full):
                size, files = dir_size(full, cancel=cancel)
                found.append(DevJunkItem(full, e.name, size, files))
                continue  # 命中后不再深入
            if depth + 1 < max_depth:
                stack.append((full, depth + 1))
    found.sort(key=lambda x: x.size, reverse=True)
    return found


def dev_result(items: list[DevJunkItem]) -> RuleResult:
    res = RuleResult(
        "dev_junk", "开发垃圾",
        "node_modules、__pycache__、虚拟环境等可重建目录",
        "dev", "low",
        "只删依赖与缓存，不碰源代码；需要时可由包管理器重新生成",
    )
    for it in items:
        res.items.append(CleanItem(it.path, "whole", it.size, it.file_count))
    res.size = sum(i.size for i in res.items)
    res.file_count = sum(i.file_count for i in res.items)
    return res
