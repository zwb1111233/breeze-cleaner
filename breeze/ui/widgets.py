"""通用小组件：卡片、胶囊按钮、进度环、标签、进度对话框。"""
from __future__ import annotations

import time

from PySide6.QtCore import Qt, QRectF, QEasingCurve, QPropertyAnimation, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QFrame, QGraphicsOpacityEffect,
                               QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout,
                               QWidget)

from .theme import ACCENT, TEXT_2

_BTN_NAMES = {"primary": "PrimaryButton", "secondary": "SecondaryButton", "danger": "DangerButton"}


def pill(text: str, kind: str = "primary", parent=None) -> QPushButton:
    b = QPushButton(text, parent)
    b.setCursor(Qt.PointingHandCursor)
    b.setObjectName(_BTN_NAMES.get(kind, "PrimaryButton"))
    return b


def chip(text: str, level: str) -> QLabel:
    l = QLabel(text)
    l.setObjectName("ChipLow" if level == "low" else "ChipMedium")
    l.setAlignment(Qt.AlignCenter)
    return l


def fade_in(w: QWidget, delay_ms: int = 0, duration_ms: int = 200) -> None:
    """轻微淡入动画，结束后移除特效以恢复最快渲染路径。"""
    if w.graphicsEffect() is not None:
        w.setGraphicsEffect(None)
    eff = QGraphicsOpacityEffect(w)
    eff.setOpacity(0.0)
    w.setGraphicsEffect(eff)
    anim = QPropertyAnimation(eff, b"opacity", w)
    anim.setDuration(duration_ms)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.OutCubic)

    def _cleanup():
        w.setGraphicsEffect(None)
        anim.deleteLater()

    anim.finished.connect(_cleanup)
    if delay_ms > 0:
        QTimer.singleShot(delay_ms, anim.start)
    else:
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)


def smooth_scroll(view) -> None:
    """列表/表格改为逐像素滚动，滚轮更顺滑。"""
    view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    view.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)


class Card(QFrame):
    """白底圆角卡片，内部自带垂直布局（通过 .body 使用）。"""

    def __init__(self, spacing: int = 12, margins: int = 18, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(margins, margins, margins, margins)
        self._lay.setSpacing(spacing)

    @property
    def body(self) -> QVBoxLayout:
        return self._lay


def page_header(title: str, subtitle: str = "") -> QWidget:
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(4)
    t = QLabel(title)
    t.setObjectName("PageTitle")
    v.addWidget(t)
    if subtitle:
        s = QLabel(subtitle)
        s.setObjectName("PageSubtitle")
        s.setWordWrap(True)
        v.addWidget(s)
    return w


class Ring(QWidget):
    """圆环进度指示器，数值变化带缓动动画。"""

    def __init__(self, diameter: int = 150, thickness: int = 13, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self._text = ""
        self._sub = ""
        self._color = ACCENT
        self._thickness = thickness
        self._anim_from = 0.0
        self._anim_target = 0.0
        self._anim_t0 = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self.setFixedSize(diameter, diameter)

    def set_value(self, value: float, text: str = "", sub: str = "", color: str | None = None):
        self._text = text
        self._sub = sub
        if color:
            self._color = color
        self._anim_from = self._value
        self._anim_target = max(0.0, min(1.0, value))
        self._anim_t0 = time.perf_counter()
        if not self._timer.isActive():
            self._timer.start()

    def _tick(self):
        p = min(1.0, (time.perf_counter() - self._anim_t0) / 0.6)
        eased = 1 - (1 - p) ** 3  # OutCubic
        self._value = self._anim_from + (self._anim_target - self._anim_from) * eased
        self.update()
        if p >= 1.0:
            self._timer.stop()
            self._value = self._anim_target

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        t = self._thickness
        rect = QRectF(t / 2, t / 2, w - t, w - t)
        p.setPen(QPen(QColor(0, 0, 0, 22), t, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(rect, 0, 360 * 16)
        if self._value > 0.0001:
            p.setPen(QPen(QColor(self._color), t, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(rect, 90 * 16, int(-360 * 16 * self._value))
        p.setPen(QColor("#1d1d1f"))
        f = QFont()
        f.setPixelSize(int(w * 0.20))
        f.setBold(True)
        p.setFont(f)
        p.drawText(rect.adjusted(0, -w * 0.05, 0, -w * 0.05), Qt.AlignCenter, self._text)
        if self._sub:
            p.setPen(QColor(TEXT_2))
            f2 = QFont()
            f2.setPixelSize(int(w * 0.085))
            p.setFont(f2)
            p.drawText(rect.adjusted(0, w * 0.16, 0, w * 0.16), Qt.AlignCenter, self._sub)
        p.end()


def human(n: int) -> str:
    f = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if f < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(f)} B"
            return f"{f:.1f} {unit}"
        f /= 1024
    return f"{f:.1f} TB"


def _safe_call(fn, arg):
    if fn:
        fn(arg)


def _show_fail(parent, title, msg, on_fail):
    if on_fail:
        on_fail(msg)
    else:
        QMessageBox.warning(parent, title, f"出错了：{msg}")


def run_with_progress(parent, title: str, worker, on_done, on_fail=None):
    """弹出一个小对话框展示 worker 进度；完成/失败/取消都由信号驱动。"""
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setFixedWidth(440)
    v = QVBoxLayout(dlg)
    v.setContentsMargins(24, 20, 24, 20)
    v.setSpacing(14)
    lbl = QLabel("准备中…")
    lbl.setWordWrap(True)
    v.addWidget(lbl)
    row = QHBoxLayout()
    row.addStretch(1)
    cancel_btn = pill("取消", "secondary")
    row.addWidget(cancel_btn)
    v.addLayout(row)

    worker.progress.connect(lbl.setText)
    worker.done.connect(lambda res: (dlg.accept(), _safe_call(on_done, res)))
    worker.failed.connect(lambda msg: (dlg.reject(), _show_fail(parent, title, msg, on_fail)))
    worker.finished.connect(worker.deleteLater)
    cancel_btn.clicked.connect(worker.cancel)
    worker.start()
    dlg.exec()
