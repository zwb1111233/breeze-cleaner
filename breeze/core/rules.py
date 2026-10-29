"""清理规则加载：规则来自 rules/*.yaml，用户可以自己添加新规则。"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml


def rules_dir() -> Path:
    """开发时指向项目 rules/ 目录；PyInstaller 打包后指向解包目录。"""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return base / "rules"
    return Path(__file__).resolve().parents[2] / "rules"


@dataclass
class TargetSpec:
    base: Path
    mode: str = "contents"   # contents=清空目录内容 | whole=整目录 | pattern=按通配符
    patterns: list[str] = field(default_factory=list)


@dataclass
class Rule:
    id: str
    name: str
    description: str = ""
    category: str = "system"   # system | browser | dev
    risk: str = "low"          # low=默认勾选 | medium=默认不勾选，提示用户
    note: str = ""
    targets: list[TargetSpec] = field(default_factory=list)


def _expand(p: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(p)))


def _parse_rule(raw: dict) -> Rule | None:
    rid = str(raw.get("id", "")).strip()
    if not rid:
        return None
    targets = []
    for t in raw.get("targets", []):
        base = str(t.get("base", "")).strip()
        if not base:
            continue
        targets.append(TargetSpec(
            base=_expand(base),
            mode=str(t.get("mode", "contents")),
            patterns=[str(x) for x in t.get("patterns", [])],
        ))
    return Rule(
        id=rid,
        name=str(raw.get("name", rid)),
        description=str(raw.get("description", "")),
        category=str(raw.get("category", "system")),
        risk=str(raw.get("risk", "low")),
        note=str(raw.get("note", "")),
        targets=targets,
    )


def load_rules(extra_dir: Path | None = None) -> list[Rule]:
    rules: list[Rule] = []
    seen: set[str] = set()
    dirs = [rules_dir()]
    if extra_dir and extra_dir != rules_dir():
        dirs.append(extra_dir)
    for d in dirs:
        if not d.is_dir():
            continue
        for yml in sorted([*d.glob("*.yaml"), *d.glob("*.yml")]):
            try:
                data = yaml.safe_load(yml.read_text(encoding="utf-8")) or {}
            except Exception:
                continue
            for raw in data.get("rules", []) or []:
                try:
                    rule = _parse_rule(raw)
                except Exception:
                    continue
                if rule and rule.id not in seen:
                    seen.add(rule.id)
                    rules.append(rule)
    return rules
