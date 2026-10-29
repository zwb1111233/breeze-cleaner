"""后台线程封装：扫描/清理都在工作线程里跑，界面不卡顿。"""
from __future__ import annotations

import threading
import time

from PySide6.QtCore import QThread, Signal

_MIN_PROGRESS_INTERVAL = 0.03  # 进度消息至少间隔 30ms，防止海量条目刷爆事件队列


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
        last_t = 0.0
        last_msg = None

        def emit(msg):
            nonlocal last_t, last_msg
            now = time.monotonic()
            if msg != last_msg or now - last_t >= _MIN_PROGRESS_INTERVAL:
                last_t = now
                last_msg = msg
                self.progress.emit(msg)

        try:
            result = self._fn(*self._args, cancel=self.cancel_event, progress=emit)
        except Exception as e:  # 工作线程内兜底，不让界面崩
            self.failed.emit(f"{type(e).__name__}: {e}")
            return
        self.done.emit(result)

    def cancel(self):
        self.cancel_event.set()
