"""删除前的最后防线：重解析点检测、受保护路径、目录大小统计。

设计原则：
- 只允许删除「白名单规则 / 用户明确选择的扫描范围」内的内容；
- 符号链接、目录联接一律不删、不深入，防止路径逃逸；
- 系统 Critical 目录（Windows / Program Files / ProgramData）绝不触碰。
"""
from __future__ import annotations

import os
import stat as stat_module
from pathlib import Path

from .platform import IS_WINDOWS, list_fixed_drives, system_drive, windows_dir

FILE_ATTRIBUTE_REPARSE_POINT = 0x400


def is_reparse_point(p: Path) -> bool:
    """符号链接 / Windows 目录联接 / 挂载点都视为重解析点。"""
    try:
        st = os.lstat(p)
    except OSError:
        return True  # 无法确认 → 按不安全处理
    if IS_WINDOWS:
        return bool(getattr(st, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT)
    return stat_module.S_ISLNK(st.st_mode)


def dir_size(p: Path, cancel=None) -> tuple[int, int]:
    """返回 (字节数, 文件数)，跳过链接与无法访问的内容。"""
    total = 0
    count = 0
    stack = [str(p)]
    while stack:
        if cancel is not None and cancel.is_set():
            break
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            full = Path(entry.path)
                            if not is_reparse_point(full):
                                stack.append(str(full))
                        elif entry.is_file(follow_symlinks=False):
                            total += entry.stat(follow_symlinks=False).st_size
                            count += 1
                    except OSError:
                        continue
        except OSError:
            continue
    return total, count


def is_within(child: Path, root: Path) -> bool:
    """child 是否位于 root 之内（含相等）。"""
    try:
        c = Path(os.path.abspath(child))
        r = Path(os.path.abspath(root))
    except OSError:
        return False
    return c == r or r in c.parents


def _critical_paths() -> tuple[list[Path], list[Path]]:
    """(连同子目录一起保护, 仅保护目录本身不删除)"""
    home = Path.home()
    children = [
        system_drive() / "Program Files",
        system_drive() / "Program Files (x86)",
        system_drive() / "ProgramData",
    ]
    exact = [
        *list_fixed_drives(),
        windows_dir(),
        system_drive() / "Users",
        home,
        home / "Desktop",
        home / "Documents",
        home / "Downloads",
        home / "Pictures",
        home / "Music",
        home / "Videos",
        home / "OneDrive",
    ]
    children = [Path(os.path.abspath(c)) for c in children]
    exact = [Path(os.path.abspath(c)) for c in exact]
    return children, exact


_CACHE: tuple[list[Path], list[Path]] | None = None


def is_protected(p: Path) -> bool:
    """True 表示这个路径绝对不允许被清风删除。"""
    global _CACHE
    if _CACHE is None:
        _CACHE = _critical_paths()
    try:
        ap = Path(os.path.abspath(p))
    except OSError:
        return True
    children, exact = _CACHE
    for root in children:
        if ap == root or root in ap.parents:
            return True
    for root in exact:
        if ap == root:
            return True
    return False


def guard_deletable(p: Path) -> None:
    """不可删除时抛 PermissionError，调用方捕获后跳过该条目。"""
    if is_reparse_point(p):
        raise PermissionError(f"跳过链接/联接点: {p}")
    if is_protected(p):
        raise PermissionError(f"受保护路径: {p}")
