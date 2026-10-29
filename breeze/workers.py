"""后台线程封装：扫描/清理都在工作线程里跑，界面不卡顿。"""
from __future__ import annotations

import threading

from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    progress = Signal(str)
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, *args, parent=None):
        super().__init__(parent)
        self._fn = fn
        self._args = args
        self.cancel_event = threading.Event()

    def run(self):
        try:
            result = self._fn(*self._args, cancel=self.cancel_event, progress=self.progress.emit)
        except Exception as e:  # 工作线程内兜底，不让界面崩
            self.failed.emit(f"{type(e).__name__}: {e}")
            return
        self.done.emit(result)

    def cancel(self):
        self.cancel_event.set()
