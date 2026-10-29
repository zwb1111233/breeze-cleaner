"""清理页：逐类勾选、查看详情、确认后清理（全部进回收站）。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QCheckBox, QDialog, QHBoxLayout, QLabel, QListWidget,
                               QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget)

from ..core import platform
from ..core.cleaner import clean_results
from ..workers import Worker
from .widgets import Card, chip, human, page_header, pill, run_with_progress

CATEGORY_ICONS = {"system": "⚙️", "browser": "🌐", "dev": "🛠️"}


class CleanPage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self._worker = None
        self._checks: dict[str, QCheckBox] = {}

        v = QVBoxLayout(self)
        v.setContentsMargins(30, 6, 30, 16)
        v.setSpacing(14)
        v.addWidget(page_header(
            "清理",
            "勾选要清理的项目。扫描可见、删除可逆 —— 所有文件都先进回收站。"))

        host_widget = QWidget()
        self.list_host = QVBoxLayout(host_widget)
        self.list_host.setContentsMargins(0, 0, 0, 0)
        self.list_host.setSpacing(10)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(host_widget)
        v.addWidget(scroll, 1)

        footer = Card(spacing=10, margins=14)
        f = QHBoxLayout()
        self.summary = QLabel("还没有体检数据")
        self.summary.setObjectName("Secondary")
        f.addWidget(self.summary)
        f.addStretch(1)
        self.btn_rescan = pill("重新体检", "secondary")
        self.btn_rescan.clicked.connect(self._rescan)
        self.btn_clean = pill("清理选中项", "primary")
        self.btn_clean.setEnabled(False)
        self.btn_clean.clicked.connect(self._do_clean)
        f.addWidget(self.btn_rescan)
        f.addWidget(self.btn_clean)
        footer.body.addLayout(f)
        v.addWidget(footer)

    def on_show(self):
        self._rebuild()

    def _rescan(self):
        self.ctx.main_window.show_page("dashboard")
        self.ctx.main_window._pages["dashboard"].start_scan()

    def _rebuild(self):
        while self.list_host.count():
            item = self.list_host.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._checks = {}

        results = getattr(self.ctx, "scan_results", [])
        if not results:
            empty = Card(spacing=8)
            t = QLabel("还没有体检数据")
            t.setObjectName("HeroTitle")
            d = QLabel("先去「体检」页做一次扫描，这里就会出现可以清理的项目。")
            d.setObjectName("Secondary")
            d.setWordWrap(True)
            b = pill("去体检", "primary")
            b.clicked.connect(lambda: self.ctx.main_window.show_page("dashboard"))
            empty.body.addWidget(t)
            empty.body.addWidget(d)
            empty.body.addWidget(b)
            self.list_host.addWidget(empty)
            self._update_footer()
            return

        for r in results:
            row = Card(spacing=8, margins=14)
            h = QHBoxLayout()
            h.setSpacing(12)
            cb = QCheckBox()
            cb.setChecked(r.risk == "low")
            cb.toggled.connect(self._update_footer)
            self._checks[r.rule_id] = cb
            h.addWidget(cb, 0)
            icon = QLabel("🗑️" if r.special == "recycle_bin" else CATEGORY_ICONS.get(r.category, "🧹"))
            icon.setStyleSheet("font-size:18px;")
            h.addWidget(icon, 0)
            mid = QVBoxLayout()
            mid.setSpacing(2)
            name = QLabel(r.name)
            name.setStyleSheet("font-weight:600;font-size:14px;")
            note = r.description + (f" · {r.note}" if r.note else "")
            sub = QLabel(note)
            sub.setObjectName("Secondary")
            sub.setWordWrap(True)
            mid.addWidget(name)
            mid.addWidget(sub)
            h.addLayout(mid, 1)
            size = QLabel(human(r.size))
            size.setStyleSheet("font-size:15px;font-weight:700;")
            h.addWidget(size, 0)
            cnt = QLabel(f"{r.file_count} 项")
            cnt.setObjectName("Secondary")
            h.addWidget(cnt, 0)
            h.addWidget(chip("需注意" if r.risk == "medium" else "安全", r.risk), 0)
            btn = QPushButton("详情")
            btn.setObjectName("SecondaryButton")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(30)
            btn.clicked.connect(lambda _=False, rr=r: self._show_detail(rr))
            h.addWidget(btn, 0)
            row.body.addLayout(h)
            self.list_host.addWidget(row)
        self._update_footer()

    def _checked_results(self):
        return [r for r in getattr(self.ctx, "scan_results", [])
                if self._checks.get(r.rule_id) is not None and self._checks[r.rule_id].isChecked()]

    def _update_footer(self):
        results = getattr(self.ctx, "scan_results", [])
        if not results:
            self.summary.setText("还没有体检数据")
            self.btn_clean.setEnabled(False)
            return
        checked = self._checked_results()
        total = sum(r.size for r in checked)
        self.summary.setText(f"已选 {len(checked)} 类 · 预计释放 {human(total)}")
        self.btn_clean.setEnabled(bool(checked))

    def _show_detail(self, r):
        dlg = QDialog(self)
        dlg.setWindowTitle(f"{r.name} · 详情")
        dlg.resize(680, 480)
        v = QVBoxLayout(dlg)
        info = QLabel(f"{r.file_count} 项 · 共 {human(r.size)} · 删除后进入回收站")
        info.setObjectName("Secondary")
        v.addWidget(info)
        lst = QListWidget()
        for item in r.items[:400]:
            lst.addItem(f"{human(item.size):>10}   {item.path}")
        v.addWidget(lst, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        copy_btn = pill("复制路径", "secondary")

        def copy():
            QGuiApplication.clipboard().setText("\n".join(str(i.path) for i in r.items[:400]))

        copy_btn.clicked.connect(copy)
        close_btn = pill("关闭", "primary")
        close_btn.clicked.connect(dlg.accept)
        row.addWidget(copy_btn)
        row.addWidget(close_btn)
        v.addLayout(row)
        dlg.exec()

    def _do_clean(self):
        results = self._checked_results()
        if not results or self._worker is not None:
            return
        total = sum(r.size for r in results)
        running = platform.is_process_running({"chrome", "msedge", "firefox"})
        confirm_on = bool(self.ctx.settings.value("confirm_before_clean", True, type=bool))
        has_recycle = any(r.special == "recycle_bin" for r in results)
        if confirm_on or has_recycle or running:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Question)
            box.setWindowTitle("确认清理")
            box.setText(f"将清理 {len(results)} 类项目，预计释放 {human(total)}。")
            text = "\n".join(f"· {r.name}" for r in results)
            text += "\n\n所有文件都会先进入回收站，误删可以恢复。"
            if has_recycle:
                text += "\n⚠ 「回收站」将被彻底清空，这一步无法恢复。"
            if running:
                text += "\n⚠ 检测到浏览器正在运行（" + "、".join(sorted(running)) + "），部分缓存可能被占用而自动跳过。"
            box.setInformativeText(text)
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
            box.button(QMessageBox.Yes).setText("开始清理")
            box.button(QMessageBox.Cancel).setText("取消")
            if box.exec() != QMessageBox.Yes:
                return

        ids = {r.rule_id for r in results}
        worker = Worker(clean_results, results, ids, parent=self)
        self._worker = worker

        def done(rep):
            self._worker = None
            for r in getattr(self.ctx, "scan_results", []):
                if r.rule_id in ids:
                    r.size = 0
                    r.file_count = 0
                    r.items = []
            self.ctx.results_dirty = True
            self._rebuild()
            msg = f"✅ 已释放约 {human(rep.freed_estimate)}，{rep.trashed} 项移入回收站。"
            if rep.skipped:
                msg += f"\n跳过 {rep.skipped} 个被占用或受保护的文件。"
            QMessageBox.information(self, "清理完成", msg)

        run_with_progress(self, "正在清理", worker, done)
