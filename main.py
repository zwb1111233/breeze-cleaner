"""清风清理 Breeze Cleaner — 入口。"""
import sys

from PySide6.QtWidgets import QApplication

from breeze import APP_EN, APP_NAME, APP_VERSION
from breeze.ui.main_window import MainWindow
from breeze.ui.theme import apply_theme


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_EN)
    app.setStyle("Fusion")
    apply_theme(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
