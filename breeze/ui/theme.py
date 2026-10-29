"""苹果官网风格主题：浅色、留白、圆角卡片、克制的蓝色点缀。"""
from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

ACCENT = "#0071e3"
TEXT = "#1d1d1f"
TEXT_2 = "#86868b"
BG = "#f5f5f7"
CARD = "#ffffff"

QSS = """
* {
    font-family: "Segoe UI Variable Display", "Segoe UI", "PingFang SC", "Microsoft YaHei UI";
    color: #1d1d1f;
    font-size: 13px;
    outline: none;
}
#Root { background-color: #f5f5f7; border: 1px solid rgba(0,0,0,0.08); border-radius: 10px; }
#TitleBar { background-color: transparent; }
QLabel#AppTitle { font-size: 14px; font-weight: 600; color: #1d1d1f; }
#TrafficClose, #TrafficMin, #TrafficMax { border: none; border-radius: 7px; }
#TrafficClose { background-color: #ff5f57; }
#TrafficMin { background-color: #febc2e; }
#TrafficMax { background-color: #28c840; }
#TrafficClose:hover { background-color: #ff4d44; }
#TrafficMin:hover { background-color: #f5b71e; }
#TrafficMax:hover { background-color: #22b538; }

#Sidebar { background-color: rgba(255,255,255,0.55); border-right: 1px solid rgba(0,0,0,0.05); }
QPushButton#NavButton {
    background-color: transparent; border: none; border-radius: 9px;
    padding: 9px 14px; text-align: left; font-size: 14px; color: #1d1d1f;
}
QPushButton#NavButton:hover:!checked { background-color: rgba(0,0,0,0.045); }
QPushButton#NavButton:checked { background-color: #e8e8ed; font-weight: 600; }

QFrame#Card { background-color: #ffffff; border: 1px solid rgba(0,0,0,0.05); border-radius: 16px; }
QLabel#PageTitle { font-size: 26px; font-weight: 700; }
QLabel#PageSubtitle { font-size: 13px; color: #86868b; }
QLabel#HeroTitle { font-size: 22px; font-weight: 700; }
QLabel#Secondary { color: #86868b; }
QLabel#BigNumber { font-size: 34px; font-weight: 700; }
QLabel#CardTitle { font-size: 15px; font-weight: 600; }

QPushButton#PrimaryButton {
    background-color: #0071e3; color: #ffffff; border: none;
    border-radius: 17px; padding: 9px 26px; font-size: 14px; font-weight: 600;
}
QPushButton#PrimaryButton:hover { background-color: #0077ed; }
QPushButton#PrimaryButton:pressed { background-color: #0068d1; }
QPushButton#PrimaryButton:disabled { background-color: #b9d7f7; color: rgba(255,255,255,0.95); }

QPushButton#SecondaryButton {
    background-color: rgba(0,0,0,0.055); color: #1d1d1f; border: none;
    border-radius: 17px; padding: 8px 20px; font-size: 13px;
}
QPushButton#SecondaryButton:hover { background-color: rgba(0,0,0,0.09); }
QPushButton#SecondaryButton:disabled { color: #b0b0b5; }

QPushButton#DangerButton {
    background-color: #ff3b30; color: #ffffff; border: none; border-radius: 15px;
    padding: 7px 18px; font-size: 13px; font-weight: 600;
}
QPushButton#DangerButton:hover { background-color: #e6352b; }
QPushButton#DangerButton:disabled { background-color: #ffc4c0; }

QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 5px; border: 1px solid rgba(0,0,0,0.22); background: #ffffff; }
QCheckBox::indicator:hover { border-color: #0071e3; }
QCheckBox::indicator:checked { background-color: #0071e3; border-color: #0071e3; }

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #ffffff; border: 1px solid rgba(0,0,0,0.14); border-radius: 8px;
    padding: 6px 10px; font-size: 13px; selection-background-color: #0071e3; selection-color: #ffffff;
}
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background: #ffffff; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px;
    selection-background-color: #e8e8ed; selection-color: #1d1d1f;
}

QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }

QScrollBar:vertical { background: transparent; width: 9px; margin: 2px; }
QScrollBar::handle:vertical { background: rgba(0,0,0,0.16); border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: rgba(0,0,0,0.28); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 9px; margin: 2px; }
QScrollBar::handle:horizontal { background: rgba(0,0,0,0.16); border-radius: 4px; min-width: 30px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }

QTableWidget { background: transparent; border: none; gridline-color: transparent; }
QTableWidget::item { padding: 6px; }
QHeaderView::section {
    background: transparent; border: none; border-bottom: 1px solid rgba(0,0,0,0.08);
    padding: 6px 8px; color: #86868b; font-size: 12px;
}
QTableCornerButton::section { background: transparent; border: none; }

QListWidget { background: transparent; border: none; }
QListWidget::item { padding: 6px 8px; border-radius: 7px; }
QListWidget::item:selected { background: #e8e8ed; color: #1d1d1f; }

QTabWidget::pane { border: none; }
QTabBar::tab {
    background: transparent; border: none; padding: 8px 16px;
    color: #86868b; font-size: 14px;
}
QTabBar::tab:selected { color: #1d1d1f; font-weight: 600; border-bottom: 2px solid #0071e3; }
QTabBar::tab:hover:!selected { color: #1d1d1f; }

QMessageBox, QDialog { background-color: #f5f5f7; }
QDialogButtonBox QPushButton {
    background: #ffffff; border: 1px solid rgba(0,0,0,0.15); border-radius: 8px;
    padding: 6px 18px; min-width: 64px; font-size: 13px;
}
QDialogButtonBox QPushButton:hover { background: #f0f0f2; }
QDialogButtonBox QPushButton:default { background: #0071e3; color: #ffffff; border: none; }

QToolTip { background: #ffffff; color: #1d1d1f; border: 1px solid rgba(0,0,0,0.12); padding: 4px 8px; border-radius: 6px; }
"""


def apply_theme(app: QApplication) -> None:
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(QSS)
