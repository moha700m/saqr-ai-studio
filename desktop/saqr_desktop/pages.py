"""Desktop pages. Every control is wired to the engine — no decorative buttons."""

from __future__ import annotations

import threading
from pathlib import Path

import cv2
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QGridLayout, QHBoxLayout,
                               QLabel, QMessageBox, QPlainTextEdit, QProgressBar,
                               QScrollArea, QSpinBox, QSplitter, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from saqr_engine.camera.stream import enumerate_cameras
from saqr_engine.media.image import process_image
from saqr_engine.media.video import process_video
from .runtime import CameraThread
from .widgets import Card, ImagePanel, PageHeader, SliderRow, StatCard, Toolbar, button


def _read_image(path: str):
    return cv2.imread(path, cv2.IMREAD_COLOR)


def _scroll(widget: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QScrollArea.Shape.NoFrame)
    area.setWidget(widget)
    return area


class DashboardPage(QWidget):
    def __init__(self, runtime, navigate, toast):
        super().__init__()
        self.runtime, self.navigate, self.toast = runtime, navigate, toast
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.addWidget(PageHeader("لوحة التحكم", "كشف العتاد واختيار الخلفية وحالة المحرك"))
        grid = QGridLayout()
        grid.setSpacing(12)
        self.cards = {
            "provider": StatCard("الخلفية", "—", "بانتظار الفحص"),
            "gpu": StatCard("كرت الشاشة", "—", ""),
            "cpu": StatCard("المعالج", "—", ""),
            "ram": StatCard("الذاكرة", "—", ""),
            "models": StatCard("النماذج", "—", "مدير النماذج"),
            "bridge": StatCard("الجسر", "متوقف", "127.0.0.1:8765"),
        }
        for index, card in enumerate(self.cards.values()):
            grid.addWidget(card, index // 3, index % 3)
        root.addLayout(grid)

        row = Toolbar()
        self.engine_badge = QLabel("المحرك: غير محمّل")
        self.engine_badge.setObjectName("Muted")
        row.add(self.engine_badge)
        row.add_stretch()
        row.add(button("فحص العتاد", primary=True)).clicked.connect(self.runtime.detect)
        row.add(button("تحميل المحرك")).clicked.connect(lambda: self.runtime.load_engine())
        row.add(button("بدء الجسر")).clicked.connect(self.start_bridge)
        root.addWidget(row)

        quick = Card("اختصارات")
        buttons = QHBoxLayout()
        for label, page in (("استوديو الوجه", "studio"), ("الكاميرا المباشرة", "live"),
                            ("استوديو الصور", "image"), ("استوديو الفيديو", "video"),
                            ("العتاد", "hardware"), ("النماذج", "models")):
            buttons.addWidget(button(label)).clicked.connect(lambda _=False, p=page: self.navigate(p))
        quick.body.addLayout(buttons)
        root.addWidget(quick)
        root.addStretch(1)

        runtime.profile_ready.connect(self.on_profile)
        runtime.decision_ready.connect(self.on_decision)
        runtime.engine_ready.connect(lambda _e: self.engine_badge.setText("المحرك: محمّل"))
        runtime.engine_error.connect(lambda msg: self.engine_badge.setText(f"المحرك: خطأ — {msg[:60]}"))

    def on_profile(self, profile):
        gpu = profile.primary_gpu
        self.cards["cpu"].set(f"{profile.cpu.physical_cores}C / {profile.cpu.logical_cores}T", profile.cpu.brand)
        self.cards["gpu"].set(gpu.name if gpu else "لا يوجد", f"{gpu.vendor} · {gpu.vram_mb or '?'} MB" if gpu else "CPU")
        self.cards["ram"].set(f"{profile.system.ram_total_mb} MB", f"{profile.system.disk_free_gb} GB قرص متاح")
        self.cards["models"].set(str(len(self.runtime.manager.list())), "مثبّتة")

    def on_decision(self, decision):
        self.cards["provider"].set(decision.label, decision.reason[:80])

    def start_bridge(self):
        self.runtime.start_bridge()
        self.runtime.bridge.started.connect(lambda url: self.cards["bridge"].set("يعمل", url))
        self.runtime.bridge.failed.connect(lambda msg: self.cards["bridge"].set("خطأ", msg[:50]))
        self.toast("جارٍ بدء الجسر المحلي على 127.0.0.1")


class HardwarePage(QWidget):
    def __init__(self, runtime, toast):
        super().__init__()
        self.runtime, self.toast = runtime, toast
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.addWidget(PageHeader("العتاد والتشخيص", "نتائج فحص المزوّدات بجلسات ONNX حقيقية"))
        row = Toolbar()
        row.add(button("إعادة الفحص", primary=True)).clicked.connect(self.runtime.detect)
        row.add(button("نسخ التقرير")).clicked.connect(self.copy)
        row.add_stretch()
        root.addWidget(row)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        self.report.setObjectName("Mono")
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["المزوّد", "متاح", "متحقق", "السبب"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        splitter.addWidget(self.report)
        splitter.addWidget(self.table)
        splitter.setSizes([520, 620])
        root.addWidget(splitter, 1)
        runtime.profile_ready.connect(self.on_profile)
        runtime.decision_ready.connect(self.on_decision)

    def on_profile(self, profile):
        self.report.setPlainText(profile.summary() + "\n\n" + "\n".join(profile.notes))

    def on_decision(self, decision):
        self.report.appendPlainText(
            f"\nBackend: {decision.provider}\nChain: {' -> '.join(decision.chain)}\n"
            f"Tier: {decision.tier}\nReason: {decision.reason}"
        )
        self.table.setRowCount(len(decision.probes))
        for row, probe in enumerate(decision.probes):
            for column, value in enumerate([probe.label, "نعم" if probe.offered else "لا",
                                            "نعم" if probe.verified else "لا", probe.reason]):
                self.table.setItem(row, column, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()

    def copy(self):
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(self.report.toPlainText())
        self.toast("نُسخ التقرير")


class FaceStudioPage(QWidget):
    def __init__(self, runtime, toast):
        super().__init__()
        self.runtime, self.toast = runtime, toast
        self.source_frame = self.target_frame = self.result_frame = None
        self.source_thumb = None
        self.source_path = self.target_path = ""
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.addWidget(PageHeader("استوديو الوجه", "صورة المصدر تبقى في الذاكرة؛ المعالجة محلية بالكامل"))

        previews = QHBoxLayout()
        self.source_view = ImagePanel("المصدر")
        self.target_view = ImagePanel("الهدف")
        self.result_view = ImagePanel("النتيجة")
        for view in (self.source_view, self.target_view, self.result_view):
            previews.addWidget(view, 1)
        root.addLayout(previews, 2)

        controls = Card("الضبط")
        grid = QGridLayout()
        self.strength = SliderRow("قوة التبديل", 0, 100, 100, "%")
        self.feather = SliderRow("نعومة الحافة", 3, 61, 21, "px")
        self.mouth = QCheckBox("قناع الفم (الحفاظ على حركة الشفاه)")
        self.mouth.setChecked(True)
        self.eyes = QCheckBox("حماية العينين")
        self.enhance = QCheckBox("تحسين الوجه (يتطلب enhancer)")
        grid.addWidget(self.strength, 0, 0)
        grid.addWidget(self.feather, 1, 0)
        grid.addWidget(self.mouth, 0, 1)
        grid.addWidget(self.eyes, 1, 1)
        grid.addWidget(self.enhance, 2, 1)
        controls.body.addLayout(grid)

        row = Toolbar()
        row.add(button("اختيار صورة المصدر")).clicked.connect(self.pick_source)
        row.add(button("اختيار صورة الهدف")).clicked.connect(self.pick_target)
        row.add(button("التقاط من الكاميرا")).clicked.connect(self.capture)
        row.add_stretch()
        row.add(button("معالجة", primary=True)).clicked.connect(self.process)
        row.add(button("حفظ النتيجة")).clicked.connect(self.save)
        controls.body.addWidget(row)
        root.addWidget(controls)
        self.metrics = QLabel("—")
        self.metrics.setObjectName("Muted")
        root.addWidget(self.metrics)

        runtime.engine_error.connect(lambda msg: self.toast(f"المحرك: {msg}"))

    def _load_source(self, frame, name):
        self.source_frame = frame
        self.source_view.set_frame(frame)
        engine = self.runtime.engine
        if engine is None:
            self.runtime.load_engine(want_swap=True, want_enhance=False)
            self.runtime.engine_ready.connect(
                lambda _e, f=frame, n=name: self._register_source(f, n),
                Qt.ConnectionType.SingleShotConnection,
            )
        else:
            self._register_source(frame, name)

    def _register_source(self, frame, name):
        engine = self.runtime.engine
        if engine is None:
            self.toast("المحرك لم يُحمّل بعد؛ أعد المحاولة بعد لحظات")
            return
        self.runtime.submit(engine.set_source_from_array, frame, name,
                            on_done=lambda src: setattr(self, "source_thumb", src.thumbnail),
                            on_error=lambda msg: self.toast(f"المصدر: {msg}"))

    def pick_source(self):
        path, _ = QFileDialog.getOpenFileName(self, "صورة المصدر", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if not path:
            return
        frame = _read_image(path)
        if frame is None:
            self.toast("تعذّر قراءة الصورة")
            return
        self.source_path = path
        self._load_source(frame, Path(path).stem)

    def pick_target(self):
        path, _ = QFileDialog.getOpenFileName(self, "صورة الهدف", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if not path:
            return
        frame = _read_image(path)
        if frame is None:
            self.toast("تعذّر قراءة الصورة")
            return
        self.target_path = path
        self.target_frame = frame
        self.target_view.set_frame(frame)

    def capture(self):
        if not self.runtime.camera:
            self.toast("شغّل الكاميرا من صفحة الكاميرا المباشرة أولًا")
            return
        self.toast("التقاط الإطار التالي…")
        def grab():
            cap = cv2.VideoCapture(self.runtime.camera.index)
            ok, frame = cap.read()
            cap.release()
            if not ok:
                raise RuntimeError("تعذّر التقاط إطار")
            return frame
        self.runtime.submit(grab, on_done=self._captured, on_error=lambda m: self.toast(m))

    def _captured(self, frame):
        self.target_frame = frame
        self.target_view.set_frame(frame)

    def process(self):
        if self.target_frame is None:
            self.toast("اختر صورة هدف أولًا")
            return
        engine = self.runtime.engine
        if engine is None:
            self.toast("حمّل المحرك أولًا من لوحة التحكم")
            return
        from saqr_engine.face.swapper import SwapOptions

        options = SwapOptions(strength=self.strength.value() / 100.0,
                              keep_mouth=self.mouth.isChecked(),
                              keep_eyes=self.eyes.isChecked(),
                              feather=self.feather.value())
        self.toast("جارٍ المعالجة…")
        self.runtime.submit(engine.process, self.target_frame.copy(), True, options,
                            on_done=self._done, on_error=lambda m: self.toast(f"فشل: {m}"))

    def _done(self, result):
        self.result_frame = result.frame
        self.result_view.set_frame(result.frame)
        m = result.metrics
        self.metrics.setText(
            f"FPS {m['fps']:.1f} · كشف {m['detect_ms']:.0f} ms · تبديل {m['swap_ms']:.0f} ms · "
            f"إجمالي {m['total_ms']:.0f} ms · وجوه {m['faces']}"
        )
        self.toast("تمت المعالجة")

    def save(self):
        if self.result_frame is None:
            self.toast("لا توجد نتيجة للحفظ")
            return
        path, _ = QFileDialog.getSaveFileName(self, "حفظ النتيجة", "saqr-result.png", "PNG (*.png);;JPEG (*.jpg)")
        if path:
            cv2.imwrite(path, self.result_frame)
            self.toast(f"حُفظت في {path}")


class LivePage(QWidget):
    progress = Signal(int, int)

    def __init__(self, runtime, toast):
        super().__init__()
        self.runtime, self.toast = runtime, toast
        self.latest = None
        self.busy = False
        self.processing = False
        self.last_processed = 0.0
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.addWidget(PageHeader("الكاميرا المباشرة", "معاينة فورية مع تبديل اختياري على المحرك المحلي"))
        row = Toolbar()
        self.camera_combo = QComboBox()
        self.refresh_cameras()
        row.add(self.camera_combo)
        row.add(button("تحديث")).clicked.connect(self.refresh_cameras)
        row.add(button("تشغيل", primary=True)).clicked.connect(self.start)
        row.add(button("إيقاف")).clicked.connect(self.stop)
        self.toggle = QCheckBox("تبديل الوجه مباشرة")
        row.add(self.toggle)
        row.add_stretch()
        self.stats = QLabel("—")
        self.stats.setObjectName("Mono")
        row.add(self.stats)
        root.addWidget(row)

        previews = QHBoxLayout()
        self.original_view = ImagePanel("الكاميرا")
        self.output_view = ImagePanel("مخرج المحرك")
        previews.addWidget(self.original_view, 1)
        previews.addWidget(self.output_view, 1)
        root.addLayout(previews, 1)
        self.notice = QLabel("المعاينة لا تعمل حتى تضغط «تشغيل». لا يبدأ أي تسجيل تلقائيًا.")
        self.notice.setObjectName("Muted")
        root.addWidget(self.notice)
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._tick)

    def refresh_cameras(self):
        self.camera_combo.clear()
        for camera in enumerate_cameras(probe=False):
            self.camera_combo.addItem(camera.name, camera.index)

    def start(self):
        self.stop()
        if self.runtime.engine is None:
            self.runtime.load_engine()
        index = self.camera_combo.currentData() or 0
        self.camera = CameraThread(int(index))
        self.camera.frame_ready.connect(self._frame)
        self.camera.stats_ready.connect(lambda s: self.stats.setText(f"{s['fps']} FPS · {s['frames']} إطار"))
        self.camera.failed.connect(lambda m: self.toast(m))
        self.camera.start()
        self.timer.start()
        self.notice.setText("الكاميرا تعمل. الإطارات تُعالج في الذاكرة فقط.")

    def stop(self):
        self.timer.stop()
        if getattr(self, "camera", None):
            self.camera.stop()
            self.camera = None
        self.original_view.set_frame(None)
        self.output_view.set_frame(None)
        self.notice.setText("الكاميرا متوقفة.")

    def _frame(self, frame):
        self.latest = frame
        self.original_view.set_frame(frame)

    def _tick(self):
        engine = self.runtime.engine
        if not self.toggle.isChecked() or engine is None or self.latest is None or self.busy:
            return
        import time

        now = time.perf_counter()
        if now - self.last_processed < 0.06:
            return
        self.last_processed = now
        self.busy = True
        frame = self.latest.copy()
        self.runtime.submit(engine.process, frame, True, None,
                            on_done=self._processed, on_error=self._process_error)

    def _processed(self, result):
        self.busy = False
        self.output_view.set_frame(result.frame)
        m = result.metrics
        self.stats.setText(f"{m['fps']:.1f} FPS · كشف {m['detect_ms']:.0f}ms · تبديل {m['swap_ms']:.0f}ms")

    def _process_error(self, message):
        self.busy = False
        self.toast(f"المعالجة: {message}")


class ImagePage(QWidget):
    def __init__(self, runtime, toast):
        super().__init__()
        self.runtime, self.toast = runtime, toast
        self.input_path = self.source_path = ""
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.addWidget(PageHeader("استوديو الصور", "معالجة صورة واحدة وتصدير PNG/JPEG"))
        self.preview = ImagePanel("المعاينة")
        root.addWidget(self.preview, 1)
        row = Toolbar()
        row.add(button("صورة المصدر")).clicked.connect(lambda: self._pick("source"))
        row.add(button("الصورة المطلوب معالجتها", primary=True)).clicked.connect(lambda: self._pick("input"))
        row.add(button("معالجة وتصدير")).clicked.connect(self.run)
        row.add_stretch()
        self.status = QLabel("—")
        self.status.setObjectName("Muted")
        row.add(self.status)
        root.addWidget(row)
        self.notice = QLabel("الصيغة النهائية تُحدد من امتداد ملف الحفظ.")
        self.notice.setObjectName("Muted")
        root.addWidget(self.notice)

    def _pick(self, kind):
        path, _ = QFileDialog.getOpenFileName(self, "اختر صورة", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not path:
            return
        if kind == "source":
            self.source_path = path
        else:
            self.input_path = path
            frame = _read_image(path)
            if frame is not None:
                self.preview.set_frame(frame)
        self.status.setText(f"{kind}: {Path(path).name}")

    def run(self):
        if not self.input_path:
            self.toast("اختر صورة أولًا")
            return
        engine = self.runtime.engine
        if engine is None:
            self.toast("حمّل المحرك أولًا")
            return
        out, _ = QFileDialog.getSaveFileName(self, "حفظ النتيجة", "saqr-image.png", "PNG (*.png);;JPEG (*.jpg)")
        if not out:
            return

        def job():
            if self.source_path:
                engine.set_source(self.source_path)
            return process_image(self.input_path, out, engine)

        self.runtime.submit(job,
                            on_done=lambda r: self.preview.set_frame(_read_image(r.output)),
                            on_error=lambda m: self.toast(m))
        self.toast("جارٍ المعالجة…")


class VideoPage(QWidget):
    progress = Signal(int, int)

    def __init__(self, runtime, toast):
        super().__init__()
        self.runtime, self.toast = runtime, toast
        self.cancel_event = threading.Event()
        self.input_path = self.source_path = ""
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.addWidget(PageHeader("استوديو الفيديو", "H.264 مع إعادة دمج الصوت، وتقدم وإلغاء"))
        row = Toolbar()
        row.add(button("المصدر")).clicked.connect(lambda: self._pick("source"))
        row.add(button("اختيار الفيديو", primary=True)).clicked.connect(lambda: self._pick("input"))
        row.add(button("بدء المعالجة")).clicked.connect(self.run)
        row.add(button("إلغاء")).clicked.connect(self.cancel)
        root.addWidget(row)
        self.info = QLabel("—")
        self.info.setObjectName("Muted")
        root.addWidget(self.info)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        root.addWidget(self.bar)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setObjectName("Mono")
        root.addWidget(self.log, 1)
        self.progress.connect(self._progress)

    def _pick(self, kind):
        path, _ = QFileDialog.getOpenFileName(self, "فيديو", "", "Video (*.mp4 *.mov *.mkv *.avi *.webm)")
        if not path:
            return
        if kind == "source":
            self.source_path = path
        else:
            self.input_path = path
            from saqr_engine.media.video import probe_video

            info = probe_video(path)
            self.info.setText(f"{Path(path).name} · {info.get('width')}×{info.get('height')} · "
                              f"{info.get('fps')} FPS · {info.get('duration_s')}s")
        self.log.appendPlainText(f"{kind}: {path}")

    def _progress(self, done, total):
        if total:
            self.bar.setValue(int(done * 100 / total))

    def run(self):
        if not self.input_path:
            self.toast("اختر فيديو")
            return
        engine = self.runtime.engine
        if engine is None:
            self.toast("حمّل المحرك أولًا")
            return
        out, _ = QFileDialog.getSaveFileName(self, "حفظ الفيديو", "saqr-video.mp4", "MP4 (*.mp4)")
        if not out:
            return
        self.cancel_event.clear()
        self.bar.setValue(0)

        def job():
            if self.source_path:
                engine.set_source(self.source_path)
            return process_video(self.input_path, out, engine, cancel=self.cancel_event,
                                 progress=lambda d, t: self.progress.emit(d, t), audio=True)

        self.runtime.submit(job, on_done=self._done, on_error=lambda m: self.toast(m))
        self.log.appendPlainText("بدأت المعالجة…")

    def _done(self, result):
        self.bar.setValue(100 if result.ok else 0)
        self.log.appendPlainText(
            f"{'تم' if result.ok else 'فشل'} · {result.frames} إطار · {result.elapsed_s}s · {result.error or ''}"
        )

    def cancel(self):
        self.cancel_event.set()
        self.log.appendPlainText("طُلب الإلغاء…")


class ModelsPage(QWidget):
    def __init__(self, runtime, toast):
        super().__init__()
        self.runtime, self.toast = runtime, toast
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.addWidget(PageHeader("مكتبة النماذج", "تحميل موثّق بالبصمة، واستيراد يدوي للنماذج المقيّدة"))
        row = Toolbar()
        row.add(button("تحديث", primary=True)).clicked.connect(self.refresh)
        row.add(button("استيراد .onnx")).clicked.connect(self.import_model)
        row.add(button("فتح مجلد النماذج")).clicked.connect(self.open_folder)
        row.add_stretch()
        root.addWidget(row)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["النموذج", "الترخيص", "تجاري", "مثبّت", "إجراء"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)
        self.license_note = QLabel("inswapper_128 غير تجاري: لا يُنزّل تلقائيًا ولا يُعاد توزيعه.")
        self.license_note.setObjectName("Muted")
        root.addWidget(self.license_note)
        self.refresh()

    def refresh(self):
        rows = self.runtime.manager.catalog()
        self.table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            self.table.setItem(index, 0, QTableWidgetItem(row["name"]))
            self.table.setItem(index, 1, QTableWidgetItem(row["license_id"]))
            self.table.setItem(index, 2, QTableWidgetItem("نعم" if row["commercial_use"] else "لا"))
            self.table.setItem(index, 3, QTableWidgetItem("نعم" if row["installed"] else "لا"))
            holder = QWidget()
            layout = QHBoxLayout(holder)
            layout.setContentsMargins(4, 2, 4, 2)
            if row["downloadable"] and not row["installed"]:
                action = button("تنزيل", primary=True)
                action.clicked.connect(lambda _=False, mid=row["id"]: self.download(mid))
                layout.addWidget(action)
            if row["requires_acceptance"] and not row["license_accepted"]:
                accept = button("قبول الترخيص")
                accept.clicked.connect(lambda _=False, mid=row["id"]: self.accept(mid))
                layout.addWidget(accept)
            layout.addStretch(1)
            self.table.setCellWidget(index, 4, holder)
        self.table.resizeColumnsToContents()

    def download(self, model_id):
        manager = self.runtime.manager
        self.runtime.submit(manager.download, model_id,
                            on_done=lambda r: (self.refresh(), self.toast(f"ثُبّت {r.filename}")),
                            on_error=lambda m: self.toast(m))
        self.toast("جارٍ التنزيل والتحقق من البصمة…")

    def accept(self, model_id):
        answer = QMessageBox.question(
            self, "ترخيص النموذج",
            "هذا النموذج مرخّص للاستخدام البحثي غير التجاري فقط. هل قرأت الترخيص وتوافق؟",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.runtime.manager.accept_license(model_id, "desktop")
            self.refresh()

    def import_model(self):
        path, _ = QFileDialog.getOpenFileName(self, "استيراد نموذج", "", "ONNX (*.onnx)")
        if not path:
            return
        manager = self.runtime.manager
        try:
            record = manager.install_file(path, accept_license=True)
            self.toast(f"استُورد {record.filename}")
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            self.toast(f"فشل الاستيراد: {exc}")

    def open_folder(self):
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.runtime.settings.models_dir)))


class SettingsPage(QWidget):
    def __init__(self, runtime, toast):
        super().__init__()
        self.runtime, self.toast = runtime, toast
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.addWidget(PageHeader("الإعدادات", "الخلفية، الجسر، والخصوصية"))

        backend = Card("المحرك")
        grid = QGridLayout()
        self.provider = QComboBox()
        self.provider.addItem("تلقائي (موصى به)", None)
        for name in ("CUDAExecutionProvider", "TensorrtExecutionProvider", "DmlExecutionProvider",
                     "ROCMExecutionProvider", "OpenVINOExecutionProvider", "CPUExecutionProvider"):
            self.provider.addItem(name, name)
        self.fallback = QCheckBox("السماح بالاحتياط التلقائي عند فشل الخلفية")
        self.fallback.setChecked(runtime.settings.allow_fallback)
        self.port = QSpinBox()
        self.port.setRange(1024, 65535)
        self.port.setValue(runtime.settings.api_port)
        grid.addWidget(QLabel("الخلفية المفضلة"), 0, 0)
        grid.addWidget(self.provider, 0, 1)
        grid.addWidget(self.fallback, 1, 0, 1, 2)
        grid.addWidget(QLabel("منفذ الجسر"), 2, 0)
        grid.addWidget(self.port, 2, 1)
        backend.body.addLayout(grid)
        save = button("حفظ وتطبيق", primary=True)
        save.clicked.connect(self.save)
        backend.body.addWidget(save)
        root.addWidget(backend)

        bridge = Card("الجسر المحلي")
        self.bridge_status = QLabel("متوقف")
        self.bridge_status.setObjectName("Muted")
        self.code = QLabel("—")
        self.code.setObjectName("PairCode")
        row = Toolbar()
        row.add(button("بدء الجسر", primary=True)).clicked.connect(self.start_bridge)
        row.add(button("رمز اقتران جديد")).clicked.connect(self.new_code)
        row.add_stretch()
        bridge.body.addWidget(self.bridge_status)
        bridge.body.addWidget(QLabel("رمز لمرة واحدة، صالح 3 دقائق:"))
        bridge.body.addWidget(self.code)
        bridge.body.addWidget(row)
        root.addWidget(bridge)

        privacy = Card("الخصوصية")
        row = QHBoxLayout()
        row.addWidget(QLabel("المعالجة السحابية"))
        cloud = QCheckBox("مفعّلة (تتطلب endpoint تملكه)")
        cloud.setChecked(runtime.settings.cloud_enabled)
        cloud.toggled.connect(lambda v: setattr(self.runtime.settings, "cloud_enabled", v))
        row.addWidget(cloud)
        row.addStretch()
        row.addWidget(QLabel("لا يرفع SAQR أي وسائط دون تأكيد صريح."))
        privacy.body.addLayout(row)
        root.addWidget(privacy)
        root.addStretch(1)

        runtime.decision_ready.connect(lambda d: self.toast(f"الخلفية: {d.provider}"))

    def save(self):
        settings = self.runtime.settings
        settings.preferred_provider = self.provider.currentData()
        settings.allow_fallback = self.fallback.isChecked()
        settings.api_port = self.port.value()
        settings.save()
        self.toast("حُفظت الإعدادات. أعد تشغيل الجسر لتطبيق المنفذ الجديد.")
        self.runtime.detect()

    def start_bridge(self):
        self.runtime.start_bridge()
        bridge = self.runtime.bridge
        bridge.started.connect(lambda url: self.bridge_status.setText(f"يعمل على {url}"))
        bridge.failed.connect(lambda msg: self.bridge_status.setText(f"خطأ: {msg}"))
        self.bridge_status.setText("جارٍ البدء…")

    def new_code(self):
        if not self.runtime.bridge or not self.runtime.bridge.isRunning():
            self.toast("ابدأ الجسر أولًا")
            return
        try:
            self.code.setText(self.runtime.bridge.new_code())
        except Exception as exc:  # noqa: BLE001
            self.toast(str(exc))


class PrivacyPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.addWidget(PageHeader("الخصوصية", "ما يُخزَّن، وأين، ولماذا"))
        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            "المعالجة محلية افتراضيًا\n"
            "• لا يرفع المحرك أي صورة أو فيديو إلى الإنترنت.\n"
            "• الكاميرا تُقرأ في الذاكرة فقط، ولا يوجد تسجيل تلقائي.\n"
            "• لا تُستخرج Embeddings ولا تُحفظ قاعدة هوية.\n\n"
            "التخزين\n"
            "• الصور المصدر في الذاكرة، وملفات النماذج في مجلد النماذج.\n"
            "• سجلات التشخيص في مجلد logs وتدور عند الإغلاق.\n\n"
            "الجسر\n"
            "• يستمع على 127.0.0.1 فقط.\n"
            "• رمز اقتران لمرة واحدة، جلسات مُهشّرة، وتحقّق من Origin.\n"
            "• يمكنك إلغاء كل الجلسات من صفحة الإعدادات.\n\n"
            "السحابة\n"
            "• معطّلة افتراضيًا. لا يوجد مزوّد مضمّن.\n"
            "• تتطلب endpoint تملكه، وموافقة صريحة لكل ملف، وحذف الملف المؤقت بعد المعالجة.\n\n"
            "الاستخدام المسؤول\n"
            "• لا تنشئ محتوى لشخص دون موافقته، ولا مواد جنسية غير رضائية.\n"
            "• أشر بوضوح إلى أن المخرج مُولّد أو معدّل رقميًا."
        )
        root.addWidget(text, 1)


__all__ = [
    "DashboardPage", "HardwarePage", "FaceStudioPage", "LivePage", "ImagePage",
    "VideoPage", "ModelsPage", "SettingsPage", "PrivacyPage",
]
