"""Main window: sidebar navigation, provider status, pages."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QMainWindow, QStackedWidget, QVBoxLayout, QWidget)

from .pages import (DashboardPage, FaceStudioPage, HardwarePage, ImagePage, LivePage,
                    ModelsPage, PrivacyPage, SettingsPage, VideoPage)
from .runtime import Runtime


class MainWindow(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.setWindowTitle("SAQR AI Studio")
        self.resize(1400, 880)
        self.runtime = Runtime(settings)
        self.pages = {}
        self.nav_items = [
            ("لوحة التحكم", "dashboard"), ("استوديو الوجه", "studio"),
            ("الكاميرا المباشرة", "live"), ("استوديو الصور", "image"),
            ("استوديو الفيديو", "video"), ("مكتبة النماذج", "models"),
            ("العتاد والتشخيص", "hardware"), ("الإعدادات", "settings"),
            ("الخصوصية", "privacy"),
        ]

        central = QWidget()
        shell = QHBoxLayout(central)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(248)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(16, 20, 16, 18)
        side_layout.setSpacing(14)

        brand = QLabel("SAQR <span style='color:#a78bfa'>AI</span>")
        brand.setObjectName("Brand")
        brand.setTextFormat(Qt.TextFormat.RichText)
        side_layout.addWidget(brand)
        caption = QLabel("FACE STUDIO · 0.9")
        caption.setObjectName("BrandSub")
        side_layout.addWidget(caption)

        self.nav = QListWidget()
        self.nav.setObjectName("Nav")
        self.nav.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for label, key in self.nav_items:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.nav.addItem(item)
        self.nav.currentRowChanged.connect(self._switch)
        side_layout.addWidget(self.nav, 1)

        mode = QLabel("وضع المعالجة\nمحلي · بلا رفع تلقائي")
        mode.setObjectName("ModeCard")
        mode.setWordWrap(True)
        side_layout.addWidget(mode)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        topbar = QWidget()
        topbar.setObjectName("TopBar")
        top = QHBoxLayout(topbar)
        top.setContentsMargins(24, 14, 24, 14)
        self.title = QLabel("لوحة التحكم")
        self.title.setObjectName("TopTitle")
        top.addWidget(self.title)
        top.addStretch(1)
        self.provider_badge = QLabel("الخلفية: —")
        self.provider_badge.setObjectName("Pill")
        self.bridge_badge = QLabel("الجسر: متوقف")
        self.bridge_badge.setObjectName("Pill")
        top.addWidget(self.provider_badge)
        top.addWidget(self.bridge_badge)
        content_layout.addWidget(topbar)

        self.stack = QStackedWidget()
        self.pages = {
            "dashboard": DashboardPage(self.runtime, self.navigate, self.toast),
            "studio": FaceStudioPage(self.runtime, self.toast),
            "live": LivePage(self.runtime, self.toast),
            "image": ImagePage(self.runtime, self.toast),
            "video": VideoPage(self.runtime, self.toast),
            "models": ModelsPage(self.runtime, self.toast),
            "hardware": HardwarePage(self.runtime, self.toast),
            "settings": SettingsPage(self.runtime, self.toast),
            "privacy": PrivacyPage(),
        }
        for _, key in self.nav_items:
            self.stack.addWidget(self.pages[key])
        content_layout.addWidget(self.stack, 1)

        shell.addWidget(sidebar)
        shell.addWidget(content, 1)
        self.setCentralWidget(central)
        self.statusBar().showMessage("جاهز. ابدأ بفحص العتاد من لوحة التحكم.")
        self.statusBar().setObjectName("Status")

        self.nav.setCurrentRow(0)
        self.runtime.decision_ready.connect(self._on_decision)
        self.runtime.profile_ready.connect(lambda _p: None)
        self.runtime.engine_ready.connect(lambda _e: self.statusBar().showMessage("المحرك محمّل وجاهز."))
        self.runtime.engine_error.connect(lambda m: self.statusBar().showMessage(f"خطأ في المحرك: {m}"))
        self.runtime.detect()

    def _switch(self, row: int) -> None:
        if row < 0:
            return
        key = self.nav_items[row][1]
        self.stack.setCurrentIndex(row)
        self.title.setText(self.nav_items[row][0])
        self.statusBar().showMessage(f"{self.nav_items[row][0]} — {key}")

    def navigate(self, key: str) -> None:
        for index, (_, item_key) in enumerate(self.nav_items):
            if item_key == key:
                self.nav.setCurrentRow(index)
                return

    def _on_decision(self, decision) -> None:
        self.provider_badge.setText(f"الخلفية: {decision.label}")
        self.provider_badge.setToolTip(decision.reason)

    def bridge_started(self, url: str) -> None:
        self.bridge_badge.setText(f"الجسر: {url}")

    def toast(self, message: str) -> None:
        self.statusBar().showMessage(message, 6000)

    def closeEvent(self, event):  # noqa: N802
        self.runtime.shutdown()
        super().closeEvent(event)
