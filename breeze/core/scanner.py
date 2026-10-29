"""扫描引擎：把规则变成「可清理项」。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import platform
from .rules import Rule, TargetSpec
from .safety import dir_size, is_reparse_point


@dataclass
class CleanItem:
    path: Path
    mode: str                 # contents | whole | file
    size: int = 0
    file_count: int = 0


@dataclass
class RuleResult:
    rule_id: str
    name: str
    description: str = ""
    category: str = "system"
    risk: str = "low"
    note: str = ""
    special: str = ""         # recycle_bin
    items: list[CleanItem] = field(default_factory=list)
    size: int = 0
    file_count: int = 0


def _scan_target(t: TargetSpec, cancel=None, progress=None) -> list[CleanItem]:
    items: list[CleanItem] = []
    base = t.base
    if not base.exists():
        return items
    if t.mode in ("contents", "whole"):
        size, files = dir_size(base, cancel=cancel)
        items.append(CleanItem(base, "contents" if t.mode == "contents" else "whole", size, files))
        return items
    # pattern 模式
    matched = 0
    for pat in t.patterns:
        if cancel is not None and cancel.is_set():
            break
        try:
            matches = list(base.glob(pat))
        except OSError:
            continue
        for m in matches:
            if cancel is not None and cancel.is_set():
                break
            matched += 1
            if progress and matched % 50 == 0:
                progress(f"扫描 {base.name}: 已发现 {matched} 项")
            try:
                if is_reparse_point(m):
                    continue
                if m.is_dir():
                    size, files = dir_size(m, cancel=cancel)
                    # 匹配到的目录按「清空内容」处理：目录本身保留，浏览器等应用可继续使用
                    items.append(CleanItem(m, "contents", size, files))
                elif m.is_file():
                    items.append(CleanItem(m, "file", m.stat().st_size, 1))
            except OSError:
                continue
    return items


def scan_rule(rule: Rule, cancel=None, progress=None) -> RuleResult:
    res = RuleResult(rule.id, rule.name, rule.description, rule.category, rule.risk, rule.note)
    for t in rule.targets:
        res.items.extend(_scan_target(t, cancel=cancel, progress=progress))
    res.size = sum(i.size for i in res.items)
    res.file_count = sum(i.file_count for i in res.items)
    return res


def recycle_bin_result() -> RuleResult:
    count, size = platform.query_recycle_bin()
    res = RuleResult(
        "recycle_bin", "回收站",
        "清空回收站立即释放空间",
        "system", "low",
        "注意：这一步是彻底删除，不会再次进入回收站",
        special="recycle_bin",
    )
    res.size = size
    res.file_count = count
    return res


def scan_all(rules: list[Rule], cancel=None, progress=None) -> list[RuleResult]:
    results: list[RuleResult] = []
    total = len(rules)
    for i, rule in enumerate(rules):
        if cancel is not None and cancel.is_set():
            break
        if progress:
            progress(f"({i + 1}/{total}) {rule.name}")
        results.append(scan_rule(rule, cancel=cancel, progress=progress))
    if not (cancel is not None and cancel.is_set()) and platform.IS_WINDOWS:
        if progress:
            progress("回收站")
        results.append(recycle_bin_result())
    results = [r for r in results if r.size > 0]
    results.sort(key=lambda r: r.size, reverse=True)
    return results
