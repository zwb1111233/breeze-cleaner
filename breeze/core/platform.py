"""平台相关工具：安全路径、磁盘、回收站、进程检测。"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"


def app_support_dir() -> Path:
    """清风自己的配置/历史目录（不属于任何清理目标）。"""
    if IS_WINDOWS:
        base = os.environ.get("APPDATA") or str(Path.home())
        return Path(base) / "Breeze"
    return Path.home() / ".breeze"


def local_appdata() -> Path:
    if IS_WINDOWS:
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base)
    return Path.home() / "AppData" / "Local"


def windows_dir() -> Path:
    return Path(os.environ.get("WINDIR", r"C:\Windows"))


def system_drive() -> Path:
    anchor = windows_dir().anchor
    return Path(anchor) if anchor else Path("C:\\")


def user_temp_dir() -> Path:
    t = os.environ.get("TEMP") or os.environ.get("TMP")
    return Path(t) if t else local_appdata() / "Temp"


def list_fixed_drives() -> list[Path]:
    """所有固定磁盘（不含 U 盘/移动硬盘，避免误碰可拔插设备）。"""
    drives: list[Path] = []
    if IS_WINDOWS:
        kernel32 = ctypes.windll.kernel32
        buf = ctypes.create_unicode_buffer(512)
        kernel32.GetLogicalDriveStringsW(512, buf)
        for part in buf.value.split("\x00"):
            if part and kernel32.GetDriveTypeW(ctypes.c_wchar_p(part)) == 3:  # DRIVE_FIXED
                drives.append(Path(part))
    else:
        drives.append(Path("/"))
    return drives


def is_process_running(image_names: set[str]) -> set[str]:
    """返回正在运行的进程名（不含 .exe，仅 Windows）。"""
    if not IS_WINDOWS or not image_names:
        return set()
    try:
        flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
        out = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=15, creationflags=flags,
        )
        running = set()
        for line in (out.stdout or "").lower().splitlines():
            if not line.startswith('"'):
                continue
            name = line.split('","', 1)[0].strip('"')
            stem = name[:-4] if name.endswith(".exe") else name
            if stem in image_names:
                running.add(stem)
        return running
    except Exception:
        return set()


if IS_WINDOWS:

    class _SHQUERYRBINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_ulong),
            ("i64Size", ctypes.c_longlong),
            ("i64NumItems", ctypes.c_longlong),
        ]


def query_recycle_bin() -> tuple[int, int]:
    """返回 (文件数, 总字节数)。非 Windows 返回 (0, 0)。"""
    if not IS_WINDOWS:
        return 0, 0
    shell32 = ctypes.windll.shell32
    total_items = 0
    total_size = 0
    for drive in list_fixed_drives():
        info = _SHQUERYRBINFO()
        info.cbSize = ctypes.sizeof(_SHQUERYRBINFO)
        try:
            if shell32.SHQueryRecycleBinW(ctypes.c_wchar_p(str(drive)), ctypes.byref(info)) == 0:
                total_items += info.i64NumItems
                total_size += info.i64Size
        except Exception:
            continue
    return total_items, total_size


_SHERB_FLAGS = 0x0001 | 0x0002 | 0x0004  # 无确认弹窗、无进度窗、无声音


def empty_recycle_bin() -> None:
    """清空所有盘的回收站。注意：这一步不可恢复，调用方需自行确认。"""
    if not IS_WINDOWS:
        raise NotImplementedError("仅支持 Windows")
    shell32 = ctypes.windll.shell32
    res = shell32.SHEmptyRecycleBinW(None, None, _SHERB_FLAGS)
    code = res & 0xFFFFFFFF
    if code not in (0, 0x8000FFFF):  # 回收站本来就空时返回 E_UNEXPECTED，视为成功
        raise OSError(f"清空回收站失败: 0x{code:08X}")
