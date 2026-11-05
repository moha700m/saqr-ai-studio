"""Application entry point."""

from __future__ import annotations

import logging
import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from saqr_engine.config import Settings

from .main_window import MainWindow

QSS = """
* { font-family: 'Segoe UI', 'Noto Sans Arabic', 'Tajawal', sans-serif; font-size: 13px; }
QMainWindow, QWidget { background: #07070c; color: #f2f2f7; }
#Sidebar { background: #0b0b13; border-left: 1px solid rgba(255,255,255,0.07); }
#Brand { font-family: 'Space Grotesk', 'Segoe UI'; font-size: 22px; font-weight: 700; letter-spacing: 0.5px; }
#BrandSub { color: #6f6f86; font-size: 10px; letter-spacing: 2px; }
#Nav { background: transparent; border: none; outline: none; }
#Nav::item { padding: 10px 12px; border-radius: 9px; color: #9d9db2; margin: 2px 0; }
#Nav::item:selected { background: rgba(139,92,246,0.16); color: #ffffff; border: 1px solid rgba(139,92,246,0.35); }
#Nav::item:hover { background: rgba(255,255,255,0.045); }
#ModeCard { background: rgba(139,92,246,0.10); border: 1px solid rgba(139,92,246,0.25);
            border-radius: 12px; padding: 12px; color: #c9c9dd; font-size: 11px; }
#TopBar { background: #08080f; border-bottom: 1px solid rgba(255,255,255,0.07); }
#TopTitle { font-size: 18px; font-weight: 700; }
#Pill { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.09);
        border-radius: 20px; padding: 5px 12px; color: #b8b8cc; font-size: 11px; }
#Card, #StatCard, #Preview { background: #101019; border: 1px solid rgba(255,255,255,0.075); border-radius: 14px; }
#CardTitle { font-size: 14px; font-weight: 700; }
#PageTitle { font-size: 22px; font-weight: 700; }
#Muted { color: #8f8fa6; }
#MutedSmall { color: #6f6f86; font-size: 11px; }
#StatValue { font-size: 19px; font-weight: 700; }
#Mono { font-family: 'Space Grotesk', 'Consolas', monospace; font-size: 12px; }
#PreviewEmpty { color: #5d5d73; font-size: 12px; }
#PreviewCaption { color: #8f8fa6; font-size: 11px; padding: 6px 10px; background: #0a0a12; }
#Primary { background: #7c3aed; border: 1px solid #8b5cf6; border-radius: 10px; padding: 8px 16px;
           color: white; font-weight: 600; }
#Primary:hover { background: #8b5cf6; }
#Primary:disabled { background: #2a2a3a; color: #6f6f86; border-color: #2a2a3a; }
#Secondary { background: #171724; border: 1px solid rgba(255,255,255,0.12); border-radius: 10px;
             padding: 8px 14px; color: #e5e5f0; }
#Secondary:hover { border-color: rgba(255,255,255,0.28); background: #1e1e2e; }
QComboBox, QSpinBox, QLineEdit { background: #0b0b14; border: 1px solid rgba(255,255,255,0.10);
             border-radius: 9px; padding: 7px 10px; min-height: 20px; }
QComboBox QAbstractItemView { background: #12121d; selection-background-color: #2d2350; }
QCheckBox { color: #c9c9dd; spacing: 8px; }
QProgressBar { background: #12121d; border: 1px solid rgba(255,255,255,0.08); border-radius: 7px;
               text-align: center; height: 16px; color: #d8d8e8; }
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #7c3aed, stop:1 #0e7490);
                      border-radius: 6px; }
QTableWidget { background: #0d0d16; gridline-color: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.07);
               border-radius: 10px; }
QHeaderView::section { background: #12121d; color: #8f8fa6; border: none; padding: 8px; font-weight: 600; }
QPlainTextEdit { background: #08080f; border: 1px solid rgba(255,255,255,0.07); border-radius: 10px; padding: 8px; }
QSlider::groove:horizontal { height: 4px; background: #232334; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #8b5cf6; border-radius: 2px; }
QSlider::handle:horizontal { width: 14px; height: 14px; margin: -6px 0; border-radius: 7px;
                             background: white; border: 2px solid #8b5cf6; }
QStatusBar { background: #08080f; color: #8f8fa6; border-top: 1px solid rgba(255,255,255,0.06); }
QScrollArea { border: none; background: transparent; }
QSplitter::handle { background: rgba(255,255,255,0.06); }
"""


def main() -> int:
    settings = Settings.load()
    settings.ensure_dirs()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(settings.logs_dir / "desktop.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    app = QApplication(sys.argv)
    app.setApplicationName("SAQR AI Studio")
    app.setOrganizationName("SAQR")
    app.setStyleSheet(QSS)
    app.setFont(QFont("Segoe UI", 10))
    window = MainWindow(settings)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
