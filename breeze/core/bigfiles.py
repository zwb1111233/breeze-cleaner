"""大文件与空文件夹扫描。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .safety import is_reparse_point

# 扫描盘符/用户目录时默认跳过的顶层目录（用户显式选择某个目录时仍可进入）
DEFAULT_SCAN_EXCLUDES = {
    "Windows", "Program Files", "Program Files (x86)", "ProgramData",
    "$Recycle.Bin", "System Volume Information", "AppData", "Recovery",
}


@dataclass
class LargeFile:
    path: Path
    size: int
    mtime: float


def scan_large_files(root: Path, min_size_mb: float = 100, excludes: set[str] | None = None,
                     cancel=None, progress=None) -> list[LargeFile]:
    excludes = excludes if excludes is not None else DEFAULT_SCAN_EXCLUDES
    min_bytes = int(min_size_mb * 1024 * 1024)
    out: list[LargeFile] = []
    stack = [root]
    scanned = 0
    while stack:
        cur = stack.pop()
        if cancel is not None and cancel.is_set():
            break
        try:
            entries = list(os.scandir(cur))
        except OSError:
            continue
        for e in entries:
            scanned += 1
            if progress and scanned % 300 == 0:
                progress(f"大文件：已检查 {scanned} 个项目")
            try:
                if e.is_dir(follow_symlinks=False):
                    full = Path(e.path)
                    if is_reparse_point(full):
                        continue
                    if cur == root and e.name in excludes:
                        continue
                    stack.append(full)
                elif e.is_file(follow_symlinks=False):
                    st = e.stat(follow_symlinks=False)
                    if st.st_size >= min_bytes:
                        out.append(LargeFile(Path(e.path), st.st_size, st.st_mtime))
            except OSError:
                continue
    out.sort(key=lambda f: f.size, reverse=True)
    return out[:500]


def scan_empty_dirs(root: Path, excludes: set[str] | None = None,
                    cancel=None, progress=None) -> list[Path]:
    """返回「整个目录树里没有任何文件」的目录，按层级从深到浅排序。

    只有整棵子树都没有文件才算空目录（只删空目录，绝不碰有文件的目录）。
    """
    excludes = excludes if excludes is not None else DEFAULT_SCAN_EXCLUDES
    result: list[Path] = []

    def walk(d: Path, is_root: bool) -> bool:
        """返回 True 表示 d 里（递归地）没有任何文件。"""
        if cancel is not None and cancel.is_set():
            return False
        has_file = False
        child_dirs: list[Path] = []
        try:
            entries = list(os.scandir(d))
        except OSError:
            return False
        for e in entries:
            try:
                if e.is_dir(follow_symlinks=False):
                    full = Path(e.path)
                    if is_reparse_point(full):
                        has_file = True  # 联接点内部无法判定，保守处理
                    elif not is_root and e.name in excludes:
                        has_file = True
                    else:
                        child_dirs.append(full)
                elif e.is_file(follow_symlinks=False):
                    has_file = True
            except OSError:
                has_file = True
        if progress:
            progress(f"空文件夹：正在检查 {d}")
        all_empty = not has_file
        for c in child_dirs:
            if not walk(c, False):
                all_empty = False
        if all_empty and not is_root:
            result.append(d)
            return True
        return all_empty and not is_root

    walk(root, True)
    result.sort(key=lambda p: len(p.parts), reverse=True)
    return result
