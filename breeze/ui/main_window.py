"""主窗口：无边框、macOS 风格红绿灯按钮、侧边栏导航。"""
from __future__ import annotations

from PySide6.QtCore import Qt, QSettings, QPoint
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow,
                               QPushButton, QSizeGrip, QStackedWidget, QVBoxLayout, QWidget)

from .. import APP_NAME, APP_VERSION
from .clean_page import CleanPage
from .dashboard import DashboardPage
from .organize_page import OrganizePage
from .settings_page import SettingsPage
from .tools_page import ToolsPage


class AppContext:
    """页面之间共享的状态。"""

    def __init__(self):
        self.settings = QSettings("Breeze", "BreezeCleaner")
        self.scan_results = []      # 最近一次体检的结果（RuleResult 列表）
        self.results_dirty = False  # 体检结果是否已过期（清理过之后）
        self.main_window = None


class TitleBar(QWidget):
    HEIGHT = 46

    def __init__(self, window: "MainWindow"):
        super().__init__(window)
        self._win = window
        self._drag: QPoint | None = None
        self.setObjectName("TitleBar")
        self.setFixedHeight(self.HEIGHT)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 4)
        lay.setSpacing(8)

        self.btn_close = QPushButton()
        self.btn_close.setObjectName("TrafficClose")
        self.btn_close.setToolTip("关闭")
        self.btn_min = QPushButton()
        self.btn_min.setObjectName("TrafficMin")
        self.btn_min.setToolTip("最小化")
        self.btn_max = QPushButton()
        self.btn_max.setObjectName("TrafficMax")
        self.btn_max.setToolTip("最大化 / 还原")
        for b in (self.btn_close, self.btn_min, self.btn_max):
            b.setFixedSize(14, 14)
            b.setCursor(Qt.PointingHandCursor)
            lay.addWidget(b)
        self.btn_close.clicked.connect(self._win.close)
        self.btn_min.clicked.connect(self._win.showMinimized)
        self.btn_max.clicked.connect(self._win.toggle_max)

        lay.addSpacing(10)
        title = QLabel(APP_NAME)
        title.setObjectName("AppTitle")
        lay.addWidget(title)
        lay.addStretch(1)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self._win.isMaximized():
            self._drag = e.globalPosition().toPoint() - self._win.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag is not None and e.buttons() & Qt.LeftButton:
            self._win.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None

    def mouseDoubleClickEvent(self, e):
        self._win.toggle_max()


_PAGES = [
    ("dashboard", "✨  体检", DashboardPage),
    ("clean", "🧹  清理", CleanPage),
    ("organize", "📂  整理", OrganizePage),
    ("tools", "🧰  工具", ToolsPage),
    ("settings", "⚙️  设置", SettingsPage),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1120, 720)
        self.setMinimumSize(960, 640)

        self.ctx = AppContext()
        self.ctx.main_window = self

        root = QFrame()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(1, 1, 1, 1)
        outer.setSpacing(0)

        self.title_bar = TitleBar(self)
        outer.addWidget(self.title_bar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        outer.addLayout(body, 1)

        # ---- 侧边栏 ----
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        sv = QVBoxLayout(sidebar)
        sv.setContentsMargins(12, 8, 12, 14)
        sv.setSpacing(4)

        logo_row = QHBoxLayout()
        logo_row.setSpacing(10)
        badge = QLabel("清")
        badge.setFixedSize(34, 34)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            "background:#1d1d1f;color:#ffffff;border-radius:9px;"
            "font-size:17px;font-weight:700;")
        name_v = QVBoxLayout()
        name_v.setSpacing(0)
        name = QLabel(APP_NAME)
        name.setStyleSheet("font-size:15px;font-weight:700;")
        ver = QLabel(f"Breeze v{APP_VERSION}")
        ver.setObjectName("Secondary")
        ver.setStyleSheet("font-size:11px;color:#86868b;")
        name_v.addWidget(name)
        name_v.addWidget(ver)
        logo_row.addWidget(badge)
        logo_row.addLayout(name_v)
        logo_row.addStretch(1)
        sv.addLayout(logo_row)
        sv.addSpacing(14)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._nav_buttons: dict[str, QPushButton] = {}
        self._pages: dict[str, QWidget] = {}
        self.stack = QStackedWidget()
        for pid, label, cls in _PAGES:
            b = QPushButton(label)
            b.setObjectName("NavButton")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, i=pid: self.show_page(i))
            self._group.addButton(b)
            sv.addWidget(b)
            self._nav_buttons[pid] = b
            page = cls(self.ctx)
            self.stack.addWidget(page)
            self._pages[pid] = page
        sv.addStretch(1)

        tip = QFrame()
        tip.setObjectName("Card")
        tip_l = QVBoxLayout(tip)
        tip_l.setContentsMargins(12, 10, 12, 10)
        tip_text = QLabel("🛡️ 安全模式\n\n所有删除都会先进入回收站，误删可以恢复。")
        tip_text.setObjectName("Secondary")
        tip_text.setStyleSheet("font-size:11px;color:#86868b;")
        tip_text.setWordWrap(True)
        tip_l.addWidget(tip_text)
        sv.addWidget(tip)

        body.addWidget(sidebar)
        body.addWidget(self.stack, 1)

        self._grip = QSizeGrip(root)
        self._grip.setFixedSize(16, 16)
        self._nav_buttons["dashboard"].setChecked(True)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._grip.move(self.width() - 18, self.height() - 18)
        self._grip.raise_()

    def show_page(self, pid: str):
        self.stack.setCurrentWidget(self._pages[pid])
        for k, b in self._nav_buttons.items():
            b.setChecked(k == pid)
        page = self._pages[pid]
        if hasattr(page, "on_show"):
            page.on_show()

    def toggle_max(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def closeEvent(self, e):
        # 退出前尽量让后台任务停下
        for page in self._pages.values():
            w = getattr(page, "_worker", None)
            if w is not None:
                try:
                    w.cancel()
                    w.wait(1500)
                except Exception:
                    pass
        super().closeEvent(e)
