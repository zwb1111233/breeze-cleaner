"""文件整理：按类型 / 月份归类，先预览后执行，全程可撤销。"""
from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .platform import app_support_dir

CATEGORY_ICONS = {
    "图片": "🖼️", "文档": "📄", "视频": "🎬", "音频": "🎵",
    "压缩包": "🗜️", "安装包": "📦", "代码": "💻", "字体": "🔤", "其他": "📁",
}

CATEGORIES: dict[str, tuple[str, ...]] = {
    "图片": (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".heic", ".svg",
             ".ico", ".tif", ".tiff", ".raw", ".psd", ".ai"),
    "文档": (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt",
             ".md", ".csv", ".rtf", ".odt", ".epub", ".xlsx"),
    "视频": (".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".ts"),
    "音频": (".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".wma"),
    "压缩包": (".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso"),
    "安装包": (".exe", ".msi", ".apk", ".dmg", ".appx", ".msix"),
    "代码": (".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".java", ".c",
             ".cpp", ".h", ".hpp", ".go", ".rs", ".json", ".xml", ".yml", ".yaml",
             ".sh", ".bat", ".ps1", ".sql", ".php", ".rb", ".ipynb", ".cs"),
    "字体": (".ttf", ".otf", ".woff", ".woff2"),
    "其他": (),
}

EXT_TO_CATEGORY = {ext: cat for cat, exts in CATEGORIES.items() for ext in exts}


def category_of(ext: str) -> str:
    return EXT_TO_CATEGORY.get(ext.lower(), "其他")


@dataclass
class MoveOp:
    src: Path
    dst: Path


@dataclass
class OrganizePlan:
    root: Path
    mode: str                # type | type_date | date
    groups: dict[str, list[MoveOp]] = field(default_factory=dict)
    skipped: int = 0

    @property
    def total(self) -> int:
        return sum(len(v) for v in self.groups.values())


def _unique_dst(dst: Path) -> Path:
    if not dst.exists():
        return dst
    stem, suffix = dst.stem, dst.suffix
    for i in range(1, 1000):
        cand = dst.with_name(f"{stem} ({i}){suffix}")
        if not cand.exists():
            return cand
    return dst.with_name(f"{stem} ({time.time():.0f}){suffix}")


def _dest_for(root: Path, f: Path, mode: str) -> Path:
    cat = category_of(f.suffix)
    if mode == "date":
        sub = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m")
        return root / sub / f.name
    if mode == "type_date":
        sub = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m")
        return root / cat / sub / f.name
    return root / cat / f.name


def plan_organization(root: Path, mode: str = "type", include_hidden: bool = False,
                      cancel=None, progress=None) -> OrganizePlan:
    """只扫描根目录下的直接文件（不递归），生成移动计划。"""
    plan = OrganizePlan(root=root, mode=mode)
    try:
        entries = list(os.scandir(root))
    except OSError:
        return plan
    for e in entries:
        if cancel is not None and cancel.is_set():
            break
        try:
            if not e.is_file(follow_symlinks=False):
                continue
            f = Path(e.path)
            if not include_hidden and f.name.startswith("."):
                plan.skipped += 1
                continue
            dst = _dest_for(root, f, mode)
            if dst == f:
                plan.skipped += 1
                continue
            plan.groups.setdefault(category_of(f.suffix), []).append(MoveOp(f, _unique_dst(dst)))
        except OSError:
            plan.skipped += 1
    return plan


def execute_plan(plan: OrganizePlan, cancel=None, progress=None) -> dict:
    moved = failed = 0
    done_ops: list[dict] = []
    total = plan.total
    done = 0
    for ops in plan.groups.values():
        for op in ops:
            done += 1
            if progress:
                progress(f"移动文件 ({done}/{total})")
            if cancel is not None and cancel.is_set():
                break
            try:
                dst = op.dst
                if dst.exists():
                    dst = _unique_dst(dst)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(op.src), str(dst))
                moved += 1
                done_ops.append({"src": str(op.src), "dst": str(dst)})
            except Exception:
                failed += 1
    if done_ops:
        _save_history({
            "time": datetime.now().isoformat(timespec="seconds"),
            "root": str(plan.root),
            "mode": plan.mode,
            "moves": done_ops,
        })
    return {"moved": moved, "failed": failed, "total": total}


def _history_file() -> Path:
    d = app_support_dir() / "history"
    d.mkdir(parents=True, exist_ok=True)
    return d / "organize.json"


def _save_history(session: dict) -> None:
    try:
        f = _history_file()
        data = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
        data.append(session)
        f.write_text(json.dumps(data[-50:], ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def last_session() -> dict | None:
    try:
        data = json.loads(_history_file().read_text(encoding="utf-8"))
        return data[-1] if data else None
    except Exception:
        return None


def clear_history() -> None:
    try:
        _history_file().unlink(missing_ok=True)
    except Exception:
        pass


def undo_last_session(cancel=None, progress=None) -> dict:
    session = last_session()
    if not session:
        return {"found": False, "restored": 0, "failed": 0}
    restored = failed = 0
    moves = session.get("moves", [])
    total = len(moves)
    for i, m in enumerate(reversed(moves)):
        if cancel is not None and cancel.is_set():
            break
        if progress:
            progress(f"移回文件 ({i + 1}/{total})")
        src, dst = Path(m["src"]), Path(m["dst"])
        try:
            if dst.exists():
                src.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dst), str(src))
                restored += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    try:
        f = _history_file()
        data = json.loads(f.read_text(encoding="utf-8"))
        if data and data[-1].get("time") == session.get("time"):
            data.pop()
            f.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass
    return {"found": True, "restored": restored, "failed": failed}
