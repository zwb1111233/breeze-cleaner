"""体检页：系统盘概览 + 一键扫描 + 结果总览。"""
from __future__ import annotations

import shutil
import time
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QScrollArea,
                               QVBoxLayout, QWidget)

from ..core import platform
from ..core.devjunk import HOME_EXCLUDES, dev_result, scan_dev_junk
from ..core.rules import load_rules
from ..core.scanner import scan_all
from ..workers import Worker
from .widgets import Card, Ring, human, page_header, pill

CATEGORY_ICONS = {"system": "⚙️", "browser": "🌐", "dev": "🛠️", "recycle": "🗑️"}


class DashboardPage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self._worker = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        outer.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        v = QVBoxLayout(body)
        v.setContentsMargins(30, 6, 30, 22)
        v.setSpacing(16)

        hour = time.localtime().tm_hour
        greet = ("凌晨好" if hour < 6 else "早上好" if hour < 11 else "中午好"
                 if hour < 13 else "下午好" if hour < 18 else "晚上好")
        v.addWidget(page_header(f"{greet} 👋", "让电脑保持清爽，像刚拆封那天一样。"))

        hero = Card(spacing=14)
        h = QHBoxLayout()
        h.setSpacing(26)
        self.ring = Ring(150, 13)
        h.addWidget(self.ring, 0, Qt.AlignVCenter)
        right = QVBoxLayout()
        right.setSpacing(6)
        t = QLabel("为你的电脑做个体检")
        t.setObjectName("HeroTitle")
        s = QLabel("扫描临时文件 · 浏览器缓存 · 开发垃圾 · 回收站")
        s.setObjectName("PageSubtitle")
        right.addWidget(t)
        right.addWidget(s)
        right.addSpacing(10)
        row = QHBoxLayout()
        row.setSpacing(12)
        self.btn_scan = pill("开始体检", "primary")
        self.btn_scan.clicked.connect(self.start_scan)
        self.status = QLabel("")
        self.status.setObjectName("Secondary")
        self.status.setWordWrap(True)
        row.addWidget(self.btn_scan)
        row.addWidget(self.status, 1)
        right.addLayout(row)
        h.addLayout(right, 1)
        hero.body.addLayout(h)
        v.addWidget(hero)

        self.dirty_label = QLabel("上一次体检之后有过清理，建议重新体检获取最新结果。")
        self.dirty_label.setObjectName("Secondary")
        self.dirty_label.hide()
        v.addWidget(self.dirty_label)

        self.summary_card = Card(spacing=12)
        sv = QVBoxLayout()
        row2 = QHBoxLayout()
        left = QVBoxLayout()
        left.setSpacing(2)
        l1 = QLabel("预计可释放")
        l1.setObjectName("Secondary")
        self.total_label = QLabel("0 B")
        self.total_label.setObjectName("BigNumber")
        left.addWidget(l1)
        left.addWidget(self.total_label)
        row2.addLayout(left)
        row2.addStretch(1)
        self.btn_go_clean = pill("去清理", "primary")
        self.btn_go_clean.clicked.connect(lambda: self.ctx.main_window.show_page("clean"))
        row2.addWidget(self.btn_go_clean, 0, Qt.AlignBottom)
        sv.addLayout(row2)
        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(10)
        sv.addWidget(self.grid_host)
        self.summary_card.body.addLayout(sv)
        self.summary_card.hide()
        v.addWidget(self.summary_card)

        quick = Card(spacing=10)
        qt = QLabel("快捷操作")
        qt.setObjectName("CardTitle")
        quick.body.addWidget(qt)
        qrow = QHBoxLayout()
        qrow.setSpacing(10)
        b1 = pill("📂  整理下载文件夹", "secondary")
        b1.clicked.connect(lambda: self.ctx.main_window.show_page("organize"))
        b2 = pill("🧰  查找大文件", "secondary")
        b2.clicked.connect(lambda: self.ctx.main_window.show_page("tools"))
        qrow.addWidget(b1)
        qrow.addWidget(b2)
        qrow.addStretch(1)
        quick.body.addLayout(qrow)
        v.addWidget(quick)
        v.addStretch(1)

        self.refresh_disk()

    def refresh_disk(self):
        try:
            drive = platform.system_drive()
            du = shutil.disk_usage(str(drive))
            pct = du.used / du.total if du.total else 0
            self.ring.set_value(pct, f"{pct * 100:.0f}%", "系统盘已用")
        except Exception:
            self.ring.set_value(0, "--", "系统盘")

    def on_show(self):
        self.refresh_disk()
        self.dirty_label.setVisible(bool(getattr(self.ctx, "results_dirty", False)))

    def start_scan(self):
        if self._worker is not None:
            return
        include_appdata = bool(self.ctx.settings.value("scan_appdata", False, type=bool))
        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("扫描中…")
        self.dirty_label.hide()
        self.status.setText("正在准备…")
        rules = load_rules()

        def job(cancel, progress):
            results = scan_all(rules, cancel=cancel, progress=progress)
            if not (cancel and cancel.is_set()):
                progress("正在扫描开发垃圾（node_modules / __pycache__ …）")
                excludes = HOME_EXCLUDES - ({"AppData"} if include_appdata else set())
                items = scan_dev_junk(Path.home(), excludes=excludes,
                                      cancel=cancel, progress=progress)
                if items:
                    results.append(dev_result(items))
            results = [r for r in results if r.size > 0]
            results.sort(key=lambda r: r.size, reverse=True)
            return results

        self._worker = Worker(job, parent=self)
        self._worker.progress.connect(self.status.setText)
        self._worker.done.connect(self._on_scanned)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_scanned(self, results):
        cancelled = self._worker is not None and self._worker.cancel_event.is_set()
        self._worker = None
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("重新体检")
        self.ctx.scan_results = results
        self.ctx.results_dirty = False
        self.total_label.setText(human(sum(r.size for r in results)))

        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        for i, r in enumerate(results[:6]):
            card = Card(spacing=6, margins=14)
            icon_name = "recycle" if r.special else r.category
            icon = QLabel(CATEGORY_ICONS.get(icon_name, "🧹") + "  " + r.name)
            icon.setObjectName("CardTitle")
            icon.setWordWrap(True)
            size = QLabel(human(r.size))
            size.setStyleSheet("font-size:17px;font-weight:700;")
            meta = QLabel(f"{r.file_count} 项" + (" · 需注意" if r.risk == "medium" else ""))
            meta.setObjectName("Secondary")
            card.body.addWidget(icon)
            card.body.addWidget(size)
            card.body.addWidget(meta)
            self.grid.addWidget(card, i // 3, i % 3)
        self.summary_card.setVisible(bool(results))
        if cancelled:
            self.status.setText("已取消，下面是已完成部分的结果。")
        else:
            self.status.setText(f"体检完成，共发现 {len(results)} 类可清理项目。")

    def _on_failed(self, msg):
        self._worker = None
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("开始体检")
        self.status.setText(f"扫描失败：{msg}")
