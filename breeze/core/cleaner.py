"""执行清理：所有删除都先进回收站（send2trash），绝不永久删除。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from send2trash import send2trash

from . import platform
from .safety import guard_deletable


@dataclass
class CleanReport:
    freed_estimate: int = 0
    trashed: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def _trash(path: Path) -> None:
    guard_deletable(path)
    send2trash(str(path))


def clean_item(item, report: CleanReport) -> int:
    """清理单个条目，返回释放字节数。被占用/受保护的内容逐个跳过。"""
    p = item.path
    if item.mode == "contents":
        try:
            children = list(p.iterdir())
        except OSError:
            report.skipped += 1
            return 0
        ok = 0
        for child in children:
            try:
                _trash(child)
                ok += 1
            except Exception as e:
                report.skipped += 1
                if len(report.errors) < 20:
                    report.errors.append(f"{child.name}: {e}")
        report.trashed += ok
        return int(item.size * ok / len(children)) if children else 0
    # whole / file
    try:
        _trash(p)
        report.trashed += 1
        return item.size
    except Exception as e:
        report.skipped += 1
        if len(report.errors) < 20:
            report.errors.append(f"{p.name}: {e}")
        return 0


def clean_results(results, checked_ids: set[str], cancel=None, progress=None) -> CleanReport:
    report = CleanReport()
    for res in results:
        if res.rule_id not in checked_ids:
            continue
        if cancel is not None and cancel.is_set():
            break
        if progress:
            progress(f"正在清理：{res.name}")
        if res.special == "recycle_bin":
            try:
                platform.empty_recycle_bin()
                report.freed_estimate += res.size
                report.trashed += res.file_count
            except Exception as e:
                report.skipped += 1
                report.errors.append(f"回收站: {e}")
            continue
        for item in res.items:
            if cancel is not None and cancel.is_set():
                break
            report.freed_estimate += clean_item(item, report)
    return report


def delete_paths(paths, cancel=None, progress=None) -> dict:
    """把若干路径移入回收站（大文件/空文件夹工具用）。"""
    ok = failed = 0
    errors: list[str] = []
    total = len(paths)
    for i, p in enumerate(paths):
        if cancel is not None and cancel.is_set():
            break
        if progress:
            progress(f"移入回收站 ({i + 1}/{total})")
        try:
            guard_deletable(Path(p))
            send2trash(str(p))
            ok += 1
        except Exception as e:
            failed += 1
            if len(errors) < 10:
                errors.append(f"{Path(p).name}: {e}")
    return {"ok": ok, "failed": failed, "errors": errors}
