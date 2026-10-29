"""整理页：按类型 / 月份归类文件，先预览后移动，一键撤销。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFileDialog,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..core.organizer import (CATEGORY_ICONS, execute_plan, last_session,
                              plan_organization, undo_last_session)
from ..workers import Worker
from .widgets import Card, human, page_header, pill, run_with_progress

_MODES = ["按类型", "按类型 + 月份", "按月份"]
_MODE_IDS = {0: "type", 1: "type_date", 2: "date"}


class OrganizePage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self._worker = None
        self._plan = None

        v = QVBoxLayout(self)
        v.setContentsMargins(30, 6, 30, 16)
        v.setSpacing(14)
        v.addWidget(page_header(
            "整理",
            "把散落的文件归类到「图片 / 文档 / 视频…」文件夹。先预览，确认后才移动，随时可以一键撤销。"))

        folder_card = Card(spacing=12)
        f = QHBoxLayout()
        f.setSpacing(10)
        self.path_edit = QLineEdit()
        dl = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
        self.path_edit.setText(dl or str(Path.home() / "Downloads"))
        btn_pick = pill("选择文件夹", "secondary")
        btn_pick.clicked.connect(self._pick)
        f.addWidget(QLabel("目标文件夹"), 0)
        f.addWidget(self.path_edit, 1)
        f.addWidget(btn_pick)
        folder_card.body.addLayout(f)

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(QLabel("整理方式"), 0)
        self.mode = QComboBox()
        self.mode.addItems(_MODES)
        row.addWidget(self.mode, 0)
        self.chk_hidden = QCheckBox("包含隐藏文件")
        self.chk_hidden.setChecked(bool(ctx.settings.value("organize_include_hidden", False, type=bool)))
        self.chk_hidden.toggled.connect(lambda c: ctx.settings.setValue("organize_include_hidden", c))
        row.addWidget(self.chk_hidden, 0)
        row.addStretch(1)
        self.btn_preview = pill("预览整理", "primary")
        self.btn_preview.clicked.connect(self._preview)
        row.addWidget(self.btn_preview, 0)
        folder_card.body.addLayout(row)
        v.addWidget(folder_card)

        self.result_card = Card(spacing=8)
        self.result_title = QLabel("")
        self.result_title.setObjectName("CardTitle")
        self.result_title.setWordWrap(True)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["文件", "移动到", "大小"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.result_card.body.addWidget(self.result_title)
        self.result_card.body.addWidget(self.table)
        self.result_card.hide()
        v.addWidget(self.result_card, 1)

        footer = Card(spacing=10, margins=14)
        f2 = QHBoxLayout()
        self.status = QLabel("选择文件夹后点击「预览整理」。")
        self.status.setObjectName("Secondary")
        self.status.setWordWrap(True)
        f2.addWidget(self.status, 1)
        self.btn_undo = pill("撤销上次整理", "secondary")
        self.btn_undo.clicked.connect(self._undo)
        self.btn_run = pill("开始整理", "primary")
        self.btn_run.setEnabled(False)
        self.btn_run.clicked.connect(self._run)
        f2.addWidget(self.btn_undo, 0)
        f2.addWidget(self.btn_run, 0)
        footer.body.addLayout(f2)
        v.addWidget(footer)

    def on_show(self):
        s = last_session()
        if s:
            self.status.setText(
                f"上次整理：{s.get('time', '')[:16].replace('T', ' ')} "
                f"移动了 {len(s.get('moves', []))} 个文件（{s.get('root', '')}）。")

    def _pick(self):
        d = QFileDialog.getExistingDirectory(self, "选择要整理的文件夹", self.path_edit.text())
        if d:
            self.path_edit.setText(d)

    def _preview(self):
        if self._worker is not None:
            return
        root = Path(self.path_edit.text().strip())
        if not root.is_dir():
            QMessageBox.warning(self, "无效文件夹", "请选择一个真实存在的文件夹。")
            return
        self.status.setText("正在分析…")
        worker = Worker(plan_organization, root, _MODE_IDS[self.mode.currentIndex()],
                        self.chk_hidden.isChecked(), parent=self)
        self._worker = worker

        def done(plan):
            self._worker = None
            self._plan = plan
            self._show_plan(plan)

        run_with_progress(self, "正在分析", worker, done)

    def _show_plan(self, plan):
        self.table.setRowCount(0)
        chips = "　".join(
            f"{CATEGORY_ICONS.get(cat, '📁')} {cat} {len(ops)} 个"
            for cat, ops in plan.groups.items())
        self.result_title.setText(f"共 {plan.total} 个文件待移动　　{chips}")
        total_size = 0
        shown = 0
        for ops in plan.groups.values():
            for op in ops:
                if shown >= 300:
                    break
                try:
                    size = op.src.stat().st_size
                except OSError:
                    size = 0
                total_size += size
                r = self.table.rowCount()
                self.table.insertRow(r)
                self.table.setItem(r, 0, QTableWidgetItem(str(op.src)))
                self.table.setItem(r, 1, QTableWidgetItem(str(op.dst.parent)))
                self.table.setItem(r, 2, QTableWidgetItem(human(size)))
                shown += 1
        self.result_card.show()
        self.btn_run.setEnabled(plan.total > 0)
        if plan.total:
            extra = "（表格仅显示前 300 项）" if plan.total > 300 else ""
            self.status.setText(
                f"预览完成：{plan.total} 个文件将归类到目标文件夹下的分类子文件夹{extra}。"
                f"确认无误后点击「开始整理」。")
        else:
            self.status.setText("没有需要整理的文件，这个文件夹已经很整洁了 👍")

    def _run(self):
        if self._plan is None or self._worker is not None:
            return
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle("确认整理")
        box.setText(f"将移动 {self._plan.total} 个文件到「{self._plan.root}」下的分类文件夹。")
        box.setInformativeText("只移动位置、不修改文件内容；完成后可在本页一键撤销。")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        box.button(QMessageBox.Yes).setText("开始整理")
        box.button(QMessageBox.Cancel).setText("取消")
        if box.exec() != QMessageBox.Yes:
            return
        plan = self._plan
        worker = Worker(execute_plan, plan, parent=self)
        self._worker = worker

        def done(rep):
            self._worker = None
            self._plan = None
            self.btn_run.setEnabled(False)
            self.status.setText(
                f"整理完成：移动 {rep['moved']} 个文件"
                + (f"，失败 {rep['failed']} 个。" if rep["failed"] else "。")
                + " 可点击「撤销上次整理」恢复原状。")

        run_with_progress(self, "正在整理", worker, done)

    def _undo(self):
        if self._worker is not None:
            return
        s = last_session()
        if not s:
            QMessageBox.information(self, "撤销整理", "还没有可以撤销的整理记录。")
            return
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle("撤销整理")
        box.setText(f"将把上次整理的 {len(s.get('moves', []))} 个文件移回原位。")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        box.button(QMessageBox.Yes).setText("撤销")
        box.button(QMessageBox.Cancel).setText("取消")
        if box.exec() != QMessageBox.Yes:
            return
        worker = Worker(undo_last_session, parent=self)
        self._worker = worker

        def done(rep):
            self._worker = None
            self._plan = None
            self.btn_run.setEnabled(False)
            if rep.get("found"):
                self.status.setText(
                    f"撤销完成：恢复 {rep['restored']} 个文件"
                    + (f"，失败 {rep['failed']} 个。" if rep["failed"] else "。"))

        run_with_progress(self, "正在撤销", worker, done)
