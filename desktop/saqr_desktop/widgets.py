"""Reusable Qt widgets with the studio's dark visual language."""

from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QSlider,
                               QVBoxLayout, QWidget)


def bgr_to_pixmap(frame: np.ndarray) -> QPixmap:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    height, width, channels = rgb.shape
    image = QImage(rgb.data, width, height, channels * width, QImage.Format.Format_RGB888).copy()
    return QPixmap.fromImage(image)


class Card(QFrame):
    def __init__(self, title: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(18, 16, 18, 18)
        self.body.setSpacing(10)
        if title:
            label = QLabel(title)
            label.setObjectName("CardTitle")
            self.body.addWidget(label)


class PageHeader(QWidget):
    def __init__(self, title: str, subtitle: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 6)
        heading = QLabel(title)
        heading.setObjectName("PageTitle")
        caption = QLabel(subtitle)
        caption.setObjectName("Muted")
        layout.addWidget(heading)
        layout.addWidget(caption)


class StatCard(QFrame):
    def __init__(self, label: str, value: str = "—", foot: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 13)
        caption = QLabel(label)
        caption.setObjectName("MutedSmall")
        self.value = QLabel(value)
        self.value.setObjectName("StatValue")
        self.value.setWordWrap(True)
        self.foot = QLabel(foot)
        self.foot.setObjectName("MutedSmall")
        self.foot.setWordWrap(True)
        layout.addWidget(caption)
        layout.addWidget(self.value)
        layout.addWidget(self.foot)

    def set(self, value: str, foot: str | None = None) -> None:
        self.value.setText(value)
        if foot is not None:
            self.foot.setText(foot)


class ImagePanel(QFrame):
    """Fixed-aspect preview that never stretches the layout."""

    def __init__(self, caption: str, parent=None):
        super().__init__(parent)
        self.setObjectName("Preview")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel("لا توجد معاينة")
        self.label.setObjectName("PreviewEmpty")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setMinimumSize(320, 220)
        layout.addWidget(self.label)
        self.caption = QLabel(caption)
        self.caption.setObjectName("PreviewCaption")
        layout.addWidget(self.caption)

    def set_frame(self, frame: np.ndarray | None) -> None:
        if frame is None:
            self.label.setPixmap(QPixmap())
            self.label.setText("لا توجد معاينة")
            return
        pixmap = bgr_to_pixmap(frame)
        self.label.setPixmap(pixmap.scaled(self.label.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation))
        self.label.setText("")

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        if self.label.pixmap() is not None and not self.label.pixmap().isNull():
            self.label.setPixmap(self.label.pixmap().scaled(
                self.label.size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))


class SliderRow(QWidget):
    def __init__(self, label: str, minimum: int, maximum: int, value: int, suffix: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        text = QLabel(label)
        text.setMinimumWidth(110)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(minimum, maximum)
        self.slider.setValue(value)
        self.readout = QLabel(f"{value}{suffix}")
        self.readout.setObjectName("Mono")
        self.readout.setMinimumWidth(54)
        self.suffix = suffix
        self.slider.valueChanged.connect(lambda v: self.readout.setText(f"{v}{self.suffix}"))
        layout.addWidget(text)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.readout)

    def value(self) -> int:
        return self.slider.value()


class Toolbar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)

    def add(self, widget: QWidget) -> QWidget:
        self.layout.addWidget(widget)
        return widget

    def add_stretch(self) -> None:
        self.layout.addStretch(1)


def button(text: str, primary: bool = False) -> QPushButton:
    widget = QPushButton(text)
    widget.setObjectName("Primary" if primary else "Secondary")
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    return widget
