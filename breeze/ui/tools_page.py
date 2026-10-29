"""工具页：大文件扫描与空文件夹清理。"""
from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QAbstractItemView, QDoubleSpinBox, QFileDialog, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMessageBox, QTabWidget, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from ..core import platform
from ..core.bigfiles import scan_empty_dirs, scan_large_files
from ..core.cleaner import delete_paths
from ..core.safety import is_within
from ..workers import Worker
from .widgets import Card, human, page_header, pill, run_with_progress


def _open_location(path: Path):
    if platform.IS_WINDOWS:
        try:
            subprocess.Popen(["explorer", f"/select,{path}"])
            return
        except Exception:
            pass
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))


def _prune_nested(paths: list[Path]) -> list[Path]:
    """如果选中了父子嵌套的目录，只保留最外层的，避免重复操作。"""
    out: list[Path] = []
    for p in sorted(paths, key=lambda q: len(q.parts)):
        if not any(is_within(p, q) for q in out):
            out.append(p)
    return out


class ToolsPage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self._worker = None
        v = QVBoxLayout(self)
        v.setContentsMargins(30, 6, 30, 16)
        v.setSpacing(14)
        v.addWidget(page_header(
            "工具",
            "大文件与空文件夹 —— 每一项都由你确认，删除同样先进回收站。"))
        self.tabs = QTabWidget()
        v.addWidget(self.tabs, 1)
        self.tabs.addTab(self._build_large(), "大文件")
        self.tabs.addTab(self._build_empty(), "空文件夹")

    # ---------- 大文件 ----------
    def _build_large(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 12, 0, 0)
        v.setSpacing(12)
        card = Card(spacing=12)
        h = QHBoxLayout()
        h.setSpacing(10)
        self.lf_path = QLineEdit(str(Path.home()))
        btn_pick = pill("选择文件夹", "secondary")
        btn_pick.clicked.connect(self._pick_large)
        h.addWidget(QLabel("扫描位置"), 0)
        h.addWidget(self.lf_path, 1)
        h.addWidget(btn_pick, 0)
        card.body.addLayout(h)
        h2 = QHBoxLayout()
        h2.setSpacing(10)
        h2.addWidget(QLabel("找出大于"), 0)
        self.lf_min = QDoubleSpinBox()
        self.lf_min.setRange(1, 10240)
        self.lf_min.setValue(100)
        self.lf_min.setSuffix(" MB")
        h2.addWidget(self.lf_min, 0)
        h2.addStretch(1)
        self.lf_scan = pill("开始扫描", "primary")
        self.lf_scan.clicked.connect(self._scan_large)
        h2.addWidget(self.lf_scan, 0)
        card.body.addLayout(h2)
        v.addWidget(card)

        self.lf_summary = QLabel(" ")
        self.lf_summary.setObjectName("Secondary")
        v.addWidget(self.lf_summary)
        self.lf_table = QTableWidget(0, 4)
        self.lf_table.setHorizontalHeaderLabels(["文件", "大小", "修改时间", "操作"])
        self.lf_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.lf_table.verticalHeader().setVisible(False)
        self.lf_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        v.addWidget(self.lf_table, 1)
        return w

    def _pick_large(self):
        d = QFileDialog.getExistingDirectory(self, "选择扫描位置", self.lf_path.text())
        if d:
            self.lf_path.setText(d)

    def _scan_large(self):
        if self._worker is not None:
            return
        root = Path(self.lf_path.text().strip())
        if not root.is_dir():
            QMessageBox.warning(self, "无效文件夹", "请选择真实存在的文件夹。")
            return
        self.lf_scan.setEnabled(False)
        worker = Worker(scan_large_files, root, float(self.lf_min.value()), parent=self)
        self._worker = worker

        def done(files):
            self._worker = None
            self.lf_scan.setEnabled(True)
            self._show_large(files)

        run_with_progress(self, "正在扫描大文件", worker, done)

    def _show_large(self, files):
        self.lf_table.setRowCount(0)
        total = sum(f.size for f in files)
        self.lf_summary.setText(
            f"找到 {len(files)} 个大文件，共 {human(total)}。" if files else "没有找到超过阈值的大文件。")
        for f in files:
            r = self.lf_table.rowCount()
            self.lf_table.insertRow(r)
            self.lf_table.setItem(r, 0, QTableWidgetItem(str(f.path)))
            self.lf_table.setItem(r, 1, QTableWidgetItem(human(f.size)))
            self.lf_table.setItem(r, 2, QTableWidgetItem(datetime.fromtimestamp(f.mtime).strftime("%Y-%m-%d %H:%M")))
            cell = QWidget()
            ch = QHBoxLayout(cell)
            ch.setContentsMargins(6, 2, 6, 2)
            ch.setSpacing(6)
            del_btn = pill("删除", "danger")
            del_btn.setFixedHeight(26)
            del_btn.clicked.connect(lambda _=False, p=f.path: self._delete_one(p))
            open_btn = pill("打开位置", "secondary")
            open_btn.setFixedHeight(26)
            open_btn.clicked.connect(lambda _=False, p=f.path: _open_location(p))
            ch.addWidget(del_btn, 0)
            ch.addWidget(open_btn, 0)
            ch.addStretch(1)
            self.lf_table.setCellWidget(r, 3, cell)

    def _delete_one(self, p: Path):
        if self._worker is not None:
            return
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle("删除文件")
        box.setText(f"把「{p.name}」移入回收站？")
        box.setInformativeText(str(p))
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        box.button(QMessageBox.Yes).setText("移入回收站")
        box.button(QMessageBox.Cancel).setText("取消")
        if box.exec() != QMessageBox.Yes:
            return
        worker = Worker(delete_paths, [p], parent=self)
        self._worker = worker

        def done(rep):
            self._worker = None
            self.lf_summary.setText(
                f"已移入回收站 {rep['ok']} 项"
                + (f"，失败 {rep['failed']} 项。" if rep["failed"] else "。")
                + " 可重新扫描查看最新结果。")

        run_with_progress(self, "正在删除", worker, done)

    # ---------- 空文件夹 ----------
    def _build_empty(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 12, 0, 0)
        v.setSpacing(12)
        card = Card(spacing=12)
        h = QHBoxLayout()
        h.setSpacing(10)
        self.ed_path = QLineEdit(str(Path.home() / "Downloads"))
        btn_pick = pill("选择文件夹", "secondary")
        btn_pick.clicked.connect(self._pick_empty)
        h.addWidget(QLabel("扫描位置"), 0)
        h.addWidget(self.ed_path, 1)
        h.addWidget(btn_pick, 0)
        self.ed_scan = pill("开始扫描", "primary")
        self.ed_scan.clicked.connect(self._scan_empty)
        h.addWidget(self.ed_scan, 0)
        card.body.addLayout(h)
        v.addWidget(card)

        self.ed_summary = QLabel(" ")
        self.ed_summary.setObjectName("Secondary")
        v.addWidget(self.ed_summary)
        self.ed_list = QListWidget()
        v.addWidget(self.ed_list, 1)
        row = QHBoxLayout()
        self.btn_all = pill("全选", "secondary")
        self.btn_all.clicked.connect(lambda: self._check_all(True))
        self.btn_none = pill("全不选", "secondary")
        self.btn_none.clicked.connect(lambda: self._check_all(False))
        row.addWidget(self.btn_all, 0)
        row.addWidget(self.btn_none, 0)
        row.addStretch(1)
        self.ed_del = pill("删除选中", "danger")
        self.ed_del.clicked.connect(self._delete_empty)
        row.addWidget(self.ed_del, 0)
        v.addLayout(row)
        return w

    def _pick_empty(self):
        d = QFileDialog.getExistingDirectory(self, "选择扫描位置", self.ed_path.text())
        if d:
            self.ed_path.setText(d)

    def _scan_empty(self):
        if self._worker is not None:
            return
        root = Path(self.ed_path.text().strip())
        if not root.is_dir():
            QMessageBox.warning(self, "无效文件夹", "请选择真实存在的文件夹。")
            return
        self.ed_scan.setEnabled(False)
        worker = Worker(scan_empty_dirs, root, None, parent=self)
        self._worker = worker

        def done(dirs):
            self._worker = None
            self.ed_scan.setEnabled(True)
            self.ed_list.clear()
            for d in dirs:
                it = QListWidgetItem(str(d))
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                it.setCheckState(Qt.Checked)
                self.ed_list.addItem(it)
            self.ed_summary.setText(
                f"找到 {len(dirs)} 个空文件夹。" if dirs else "没有找到空文件夹。")

        run_with_progress(self, "正在扫描空文件夹", worker, done)

    def _check_all(self, checked: bool):
        for i in range(self.ed_list.count()):
            self.ed_list.item(i).setCheckState(Qt.Checked if checked else Qt.Unchecked)

    def _delete_empty(self):
        if self._worker is not None:
            return
        paths = [Path(self.ed_list.item(i).text()) for i in range(self.ed_list.count())
                 if self.ed_list.item(i).checkState() == Qt.Checked]
        if not paths:
            return
        paths = _prune_nested(paths)
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle("删除空文件夹")
        box.setText(f"把 {len(paths)} 个空文件夹移入回收站？")
        box.setInformativeText("这些文件夹里没有任何文件，删除是安全的，且可以在回收站恢复。")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        box.button(QMessageBox.Yes).setText("移入回收站")
        box.button(QMessageBox.Cancel).setText("取消")
        if box.exec() != QMessageBox.Yes:
            return
        worker = Worker(delete_paths, paths, parent=self)
        self._worker = worker

        def done(rep):
            self._worker = None
            for i in reversed(range(self.ed_list.count())):
                if self.ed_list.item(i).checkState() == Qt.Checked:
                    self.ed_list.takeItem(i)
            self.ed_summary.setText(
                f"已移入回收站 {rep['ok']} 个"
                + (f"，失败 {rep['failed']} 个。" if rep["failed"] else "。"))

        run_with_progress(self, "正在删除", worker, done)
