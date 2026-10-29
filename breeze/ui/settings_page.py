"""设置页：关于、通用开关、数据。"""
from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QHBoxLayout, QLabel, QMessageBox,
                               QVBoxLayout, QWidget)

from .. import APP_EN, APP_NAME, APP_VERSION, REPO_URL
from ..core.organizer import clear_history
from ..core.platform import app_support_dir
from .widgets import Card, page_header, pill


class SettingsPage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        v = QVBoxLayout(self)
        v.setContentsMargins(30, 6, 30, 16)
        v.setSpacing(14)
        v.addWidget(page_header("设置", "个性化你的清风清理。"))

        about = Card(spacing=10)
        h = QHBoxLayout()
        h.setSpacing(16)
        badge = QLabel("清")
        badge.setFixedSize(56, 56)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            "background:#1d1d1f;color:#ffffff;border-radius:14px;"
            "font-size:26px;font-weight:700;")
        h.addWidget(badge, 0, Qt.AlignTop)
        mid = QVBoxLayout()
        name = QLabel(f"{APP_NAME} · {APP_EN}")
        name.setObjectName("HeroTitle")
        ver = QLabel(f"版本 v{APP_VERSION} · 轻·快·净 的 Windows 清理工具")
        ver.setObjectName("Secondary")
        link = QLabel(f'<a href="{REPO_URL}">{REPO_URL}</a>')
        link.setOpenExternalLinks(True)
        mid.addWidget(name)
        mid.addWidget(ver)
        mid.addWidget(link)
        h.addLayout(mid)
        h.addStretch(1)
        about.body.addLayout(h)
        star = QLabel("如果清风帮到了你，欢迎在 GitHub 给个 ⭐ Star，这是对开源作者最大的鼓励。")
        star.setObjectName("Secondary")
        about.body.addWidget(star)
        v.addWidget(about)

        opts = Card(spacing=12)
        t = QLabel("通用")
        t.setObjectName("CardTitle")
        opts.body.addWidget(t)
        c1 = QCheckBox("清理前总是弹出确认对话框（推荐）")
        c1.setChecked(bool(ctx.settings.value("confirm_before_clean", True, type=bool)))
        c1.toggled.connect(lambda c: ctx.settings.setValue("confirm_before_clean", c))
        opts.body.addWidget(c1)
        c2 = QCheckBox("体检时扫描 AppData 里的开发垃圾（更全面，稍慢）")
        c2.setChecked(bool(ctx.settings.value("scan_appdata", False, type=bool)))
        c2.toggled.connect(lambda c: ctx.settings.setValue("scan_appdata", c))
        opts.body.addWidget(c2)
        c3 = QCheckBox("整理文件时包含隐藏文件")
        c3.setChecked(bool(ctx.settings.value("organize_include_hidden", False, type=bool)))
        c3.toggled.connect(lambda c: ctx.settings.setValue("organize_include_hidden", c))
        opts.body.addWidget(c3)
        v.addWidget(opts)

        data = Card(spacing=12)
        t2 = QLabel("数据")
        t2.setObjectName("CardTitle")
        data.body.addWidget(t2)
        row = QHBoxLayout()
        b1 = pill("打开配置文件夹", "secondary")
        b1.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(app_support_dir()))))
        b2 = pill("清空整理历史", "secondary")
        b2.clicked.connect(self._clear_history)
        row.addWidget(b1, 0)
        row.addWidget(b2, 0)
        row.addStretch(1)
        data.body.addLayout(row)
        note = QLabel("清风不联网、不上传任何数据；清理与整理记录只保存在你自己电脑的配置文件夹里。")
        note.setObjectName("Secondary")
        note.setWordWrap(True)
        data.body.addWidget(note)
        v.addWidget(data)
        v.addStretch(1)

    def _clear_history(self):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle("清空整理历史")
        box.setText("将删除全部整理历史记录（只删记录，不影响你的文件）。")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        box.button(QMessageBox.Yes).setText("清空")
        box.button(QMessageBox.Cancel).setText("取消")
        if box.exec() == QMessageBox.Yes:
            clear_history()
            QMessageBox.information(self, "清空整理历史", "已清空。")
