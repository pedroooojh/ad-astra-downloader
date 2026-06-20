import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, QThread, QTimer, QUrl, QVariantAnimation, QObject, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QComboBox, QFileDialog, QFrame, QGraphicsDropShadowEffect,
    QHBoxLayout, QLabel, QLineEdit, QListView, QMainWindow, QProgressBar, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)


APP_NAME = "ad astra downloader"
APP_DATA_FOLDER = "AdAstraDownloader"
YT_DLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
PROGRESS_RE = re.compile(r"(?P<percent>[\d.,]+)%\|(?P<speed>.*?)\|(?P<eta>.*)")
YOUTUBE_URL_RE = re.compile(
    r"^https?://(?:www\.|m\.)?(?:youtube\.com/(?:watch\?.*v=|shorts/|live/)|youtu\.be/)[^\s]+$",
    re.IGNORECASE,
)


def resource_path(relative: str) -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / relative


def app_data_dir() -> Path:
    root = Path(os.getenv("LOCALAPPDATA", Path.home())) / APP_DATA_FOLDER
    root.mkdir(parents=True, exist_ok=True)
    return root


def yt_dlp_path() -> Path:
    bundled = resource_path("bin/yt-dlp.exe")
    writable = app_data_dir() / "yt-dlp.exe"
    if writable.exists():
        return writable
    if bundled.exists():
        shutil.copy2(bundled, writable)
        return writable
    on_path = shutil.which("yt-dlp")
    return Path(on_path) if on_path else writable


def ffmpeg_location() -> str | None:
    bundled = resource_path("bin/ffmpeg.exe")
    if bundled.exists():
        return str(bundled.parent)
    found = shutil.which("ffmpeg")
    return str(Path(found).parent) if found else None


def format_duration(seconds) -> str:
    if not seconds:
        return "duração indisponível"
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


class Worker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(float, str)

    def __init__(self, action, **kwargs):
        super().__init__()
        self.action = action
        self.kwargs = kwargs
        self.process = None

    def run(self):
        try:
            self.finished.emit(getattr(self, self.action)())
        except Exception as exc:
            self.failed.emit(str(exc))

    def ensure_engine(self):
        target = yt_dlp_path()
        if not target.exists():
            self.progress.emit(0, "baixando o mecanismo yt-dlp…")
            temp = target.with_suffix(".tmp")
            urllib.request.urlretrieve(YT_DLP_URL, temp)
            temp.replace(target)
            return "Pronto"
        self.progress.emit(0, "verificando atualizações…")
        subprocess.run(
            [str(target), "-U"], capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=90,
        )
        return "Pronto"

    def analyze(self):
        exe = yt_dlp_path()
        if not exe.exists():
            self.ensure_engine()
        result = subprocess.run(
            [str(exe), "--dump-single-json", "--no-playlist", "--no-warnings", self.kwargs["url"]],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=120,
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "Não foi possível analisar este endereço.")
        return json.loads(result.stdout)

    def download(self):
        exe = yt_dlp_path()
        output = str(Path(self.kwargs["destination"]) / "%(title)s.%(ext)s")
        command = [
            str(exe), "--newline", "--no-playlist", "--windows-filenames", "--no-simulate",
            "--progress-template", "%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s",
            "--print", "after_move:__AD_ASTRA_FILE__%(filepath)s",
            "-f", self.kwargs["format_id"], "-o", output,
        ]
        ffmpeg = ffmpeg_location()
        if ffmpeg:
            command += ["--ffmpeg-location", ffmpeg]
        if self.kwargs["mode"] == "audio":
            if not ffmpeg:
                raise RuntimeError("O FFmpeg é necessário para converter áudio.")
            command += [
                "-x", "--audio-format", self.kwargs["audio_format"],
                "--audio-quality", str(self.kwargs.get("audio_quality", "192")),
            ]
        else:
            output_ext = self.kwargs["output_ext"]
            command += ["--merge-output-format", output_ext, "--remux-video", output_ext]
        command.append(self.kwargs["url"])

        self.process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", creationflags=subprocess.CREATE_NO_WINDOW,
        )
        final_path = None
        for raw in self.process.stdout or []:
            if raw.startswith("__AD_ASTRA_FILE__"):
                final_path = raw.removeprefix("__AD_ASTRA_FILE__").strip()
                continue
            match = PROGRESS_RE.search(raw.strip())
            if match:
                value = float(match.group("percent").replace(",", "."))
                speed = match.group("speed").strip()
                eta = match.group("eta").strip()
                self.progress.emit(value, f"{speed}|{eta}")
        code = self.process.wait()
        if code:
            raise RuntimeError("Não foi possível concluir o download.")
        return {"message": "Download concluído", "path": final_path}


class AnimatedButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._base_color = QColor("#ffffff")
        self._hover_color = QColor("#f0f0f0")
        self._disabled_color = QColor("#e0e0e0")
        self._color_animation = QVariantAnimation(self)
        self._color_animation.setDuration(150)
        self._color_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._color_animation.valueChanged.connect(self._apply_color)

    def configure_colors(self, base, hover, disabled="#e0e0e0"):
        self._base_color = QColor(base)
        self._hover_color = QColor(hover)
        self._disabled_color = QColor(disabled)
        self._color_animation.stop()
        self._apply_color(self._base_color if self.isEnabled() else self._disabled_color)

    def _animate_to(self, target):
        if not self.isEnabled():
            return
        self._color_animation.stop()
        self._color_animation.setStartValue(self.palette().button().color())
        self._color_animation.setEndValue(target)
        self._color_animation.start()

    def _apply_color(self, color):
        self.setStyleSheet(f"background-color: {color.name()};")
        palette = self.palette()
        palette.setColor(palette.ColorRole.Button, color)
        self.setPalette(palette)

    def enterEvent(self, event):
        self._animate_to(self._hover_color)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate_to(self._base_color)
        super().leaveEvent(event)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.EnabledChange:
            self._apply_color(self._base_color if self.isEnabled() else self._disabled_color)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.info = None
        self.thread = None
        self.worker = None
        self.busy = False
        self.engine_available = False
        self.best_audio_selector = "bestaudio"
        self.last_download_path = None
        self.network = QNetworkAccessManager(self)
        self.result_animation = None
        self.reset_timer = QTimer(self)
        self.reset_timer.setSingleShot(True)
        self.reset_timer.timeout.connect(self.reset_form)

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(str(resource_path("assets/adastra.png"))))
        self.setFixedSize(480, 520)
        self._build_ui()
        self._set_style()
        self.update_url_state()
        self.run_worker("ensure_engine", self.engine_ready, quiet=True)

    def _button_accessibility(self, button, description):
        button.setToolTip(description)
        button.setAccessibleName(description)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(8)

        self.logo = QLabel()
        self.logo.setObjectName("logo")
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_pixmap = QPixmap(str(resource_path("assets/adastra.png")))
        self.logo.setPixmap(logo_pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.logo.setFixedHeight(64)
        layout.addWidget(self.logo)

        tagline = QLabel("per aspera ad astra!")
        tagline.setObjectName("secondary")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tagline)
        layout.addSpacing(8)

        card = QFrame()
        card.setObjectName("mainCard")
        card_shadow = QGraphicsDropShadowEffect(card)
        card_shadow.setBlurRadius(8)
        card_shadow.setOffset(0, 1)
        card_shadow.setColor(QColor(0, 0, 0, 20))
        card.setGraphicsEffect(card_shadow)
        form = QVBoxLayout(card)
        form.setContentsMargins(16, 14, 16, 14)
        form.setSpacing(8)

        url_row = QHBoxLayout()
        url_row.setSpacing(0)
        self.url = QLineEdit()
        self.url.setObjectName("urlInput")
        self.url.setPlaceholderText("cole um link do youtube")
        self.url.setFixedHeight(38)
        self.url.setClearButtonEnabled(True)
        self.url.setAccessibleName("link do vídeo do youtube")
        self.url.setToolTip("cole o endereço completo de um vídeo do youtube")
        self.url.textChanged.connect(self.update_url_state)
        self.url.returnPressed.connect(self.analyze)
        self.analyze_button = AnimatedButton("analisar")
        self.analyze_button.setObjectName("analyzeButton")
        self.analyze_button.setFixedSize(90, 38)
        self.analyze_button.clicked.connect(self.analyze)
        self._button_accessibility(self.analyze_button, "analisar o link do youtube")
        url_row.addWidget(self.url, 1)
        url_row.addWidget(self.analyze_button)
        form.addLayout(url_row)

        self.url_error = QLabel("")
        self.url_error.setObjectName("urlError")
        self.url_error.setFixedHeight(14)
        form.addWidget(self.url_error)

        self.result_card = QFrame()
        self.result_card.setObjectName("resultCard")
        self.result_card.setMinimumHeight(0)
        self.result_card.setMaximumHeight(70)
        self.result_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        result_layout = QHBoxLayout(self.result_card)
        result_layout.setContentsMargins(8, 8, 8, 8)
        result_layout.setSpacing(10)
        self.thumbnail = QLabel()
        self.thumbnail.setObjectName("thumbnail")
        self.thumbnail.setFixedSize(64, 48)
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        result_text = QVBoxLayout()
        result_text.setSpacing(2)
        self.video_title = QLabel()
        self.video_title.setObjectName("videoTitle")
        self.video_title.setWordWrap(True)
        self.video_title.setFixedHeight(32)
        self.video_meta = QLabel()
        self.video_meta.setObjectName("secondary")
        result_text.addWidget(self.video_title)
        result_text.addWidget(self.video_meta)
        result_layout.addWidget(self.thumbnail)
        result_layout.addLayout(result_text, 1)
        self.result_card.hide()
        form.addWidget(self.result_card)

        segment = QFrame()
        segment.setObjectName("segment")
        segment_layout = QHBoxLayout(segment)
        segment_layout.setContentsMargins(2, 2, 2, 2)
        segment_layout.setSpacing(2)
        self.video_button = AnimatedButton("vídeo")
        self.audio_button = AnimatedButton("somente áudio")
        for button in (self.video_button, self.audio_button):
            button.setObjectName("segmentButton")
            button.setCheckable(True)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.video_button.setChecked(True)
        self.video_button.setProperty("active", True)
        self.audio_button.setProperty("active", False)
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_group.addButton(self.video_button)
        self.mode_group.addButton(self.audio_button)
        self.video_button.clicked.connect(self.set_video_mode)
        self.audio_button.clicked.connect(self.set_audio_mode)
        self._button_accessibility(self.video_button, "selecionar download de vídeo")
        self._button_accessibility(self.audio_button, "selecionar download somente de áudio")
        segment_layout.addWidget(self.video_button)
        segment_layout.addWidget(self.audio_button)
        form.addWidget(segment)

        self.options_hint = QLabel("as opções de qualidade aparecem após analisar o link")
        self.options_hint.setObjectName("optionsHint")
        self.options_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.options_hint.setFixedHeight(38)
        form.addWidget(self.options_hint)

        self.quality = QComboBox()
        self.quality.setView(QListView())
        self.quality.setAccessibleName("qualidade e formato do vídeo")
        self.quality.setToolTip("escolha a qualidade e o formato final do vídeo")
        self.quality.setEnabled(False)
        self.quality.setFixedHeight(38)
        self.quality.hide()
        form.addWidget(self.quality)

        self.audio_bitrate = QComboBox()
        self.audio_bitrate.setView(QListView())
        self.audio_bitrate.addItem("áudio · 128 kbps · mp3", "128")
        self.audio_bitrate.addItem("áudio · 192 kbps · mp3", "192")
        self.audio_bitrate.addItem("áudio · 320 kbps · mp3", "320")
        self.audio_bitrate.setCurrentIndex(1)
        self.audio_bitrate.setAccessibleName("qualidade do áudio")
        self.audio_bitrate.setToolTip("escolha o bitrate do arquivo mp3")
        self.audio_bitrate.setFixedHeight(38)
        self.audio_bitrate.hide()
        form.addWidget(self.audio_bitrate)

        folder_row = QHBoxLayout()
        folder_row.setSpacing(6)
        self.destination = QLineEdit(str(Path.home() / "Downloads"))
        self.destination.setFixedHeight(38)
        self.destination.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.destination.setAccessibleName("pasta de destino")
        self.destination.setToolTip("pasta onde o arquivo será salvo")
        self.choose_button = AnimatedButton("escolher pasta")
        self.choose_button.setObjectName("outlineButton")
        self.choose_button.setFixedHeight(38)
        self.choose_button.clicked.connect(self.choose_folder)
        self._button_accessibility(self.choose_button, "escolher pasta de destino")
        folder_row.addWidget(self.destination, 1)
        folder_row.addWidget(self.choose_button)
        form.addLayout(folder_row)

        self.download_button = AnimatedButton("baixar")
        self.download_button.setObjectName("downloadButton")
        self.download_button.setFixedHeight(42)
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self.download)
        self._button_accessibility(self.download_button, "iniciar o download")
        form.addWidget(self.download_button)

        self.progress_meta = QLabel("0%")
        self.progress_meta.setObjectName("progressMeta")
        self.progress_meta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_meta.hide()
        form.addWidget(self.progress_meta)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(3)
        self.progress.hide()
        form.addWidget(self.progress)

        self.error_label = QLabel("")
        self.error_label.setObjectName("errorText")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        form.addWidget(self.error_label)

        self.completion = QWidget()
        completion_layout = QHBoxLayout(self.completion)
        completion_layout.setContentsMargins(0, 0, 0, 0)
        completion_layout.setSpacing(8)
        done = QLabel("✓ download concluído")
        done.setObjectName("completionText")
        self.open_folder_button = AnimatedButton("abrir pasta →")
        self.open_folder_button.setObjectName("linkButton")
        self.open_folder_button.clicked.connect(self.open_folder)
        self._button_accessibility(self.open_folder_button, "abrir a pasta do arquivo baixado")
        completion_layout.addWidget(done)
        completion_layout.addStretch()
        completion_layout.addWidget(self.open_folder_button)
        self.completion.hide()
        form.addWidget(self.completion)

        self.status = QLabel("Preparando…")
        self.status.setObjectName("secondary")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form.addWidget(self.status)

        layout.addWidget(card)
        layout.addStretch()
        self.setCentralWidget(root)

    def _set_style(self):
        arrow = resource_path("assets/chevron-down.svg").as_posix()
        self.setStyleSheet(f"""
            QWidget {{ background: #ffffff; color: #0a0a0a; font-size: 12px; font-weight: 400; }}
            #root {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f5f5f5, stop:1 #ebebeb); }}
            QLabel {{ background: transparent; }}
            #logo {{ background: transparent; }}
            #secondary {{ color: #888888; font-size: 12px; }}
            #mainCard {{ background: #ffffff; border: 1px solid #d0d0d0; border-radius: 12px; }}
            #resultCard {{ background: #f9f9f9; border: 1px solid #e0e0e0; border-radius: 8px; }}
            #thumbnail {{ background: #eeeeee; border: 0; border-radius: 4px; color: #aaaaaa; }}
            #videoTitle {{ background: transparent; font-size: 13px; font-weight: 500; color: #0a0a0a; }}
            #optionsHint {{ background: transparent; color: #aaaaaa; font-size: 12px; }}
            QLineEdit, QComboBox {{
                background: #ffffff; color: #0a0a0a; border: 1px solid #cccccc; border-radius: 6px;
                padding: 6px 9px; font-size: 13px; placeholder-text-color: #aaaaaa; selection-background-color: #0a0a0a;
                selection-color: #ffffff;
            }}
            QLineEdit:focus, QComboBox:focus {{ border: 2px solid #0a0a0a; padding: 5px 8px; }}
            QLineEdit:disabled, QComboBox:disabled {{ color: #aaaaaa; background: #f5f5f5; }}
            QLineEdit[urlState="valid"] {{ border: 1px solid #0a0a0a; }}
            QLineEdit[urlState="valid"]:focus {{ border: 2px solid #0a0a0a; }}
            QLineEdit[urlState="invalid"] {{ border: 1px solid #dd4444; }}
            QLineEdit[urlState="invalid"]:focus {{ border: 2px solid #dd4444; }}
            QLineEdit#urlInput {{ border-top-right-radius: 0; border-bottom-right-radius: 0; }}
            #urlError {{ color: #dd4444; font-size: 12px; background: transparent; }}
            QPushButton {{
                border: 1px solid #cccccc; border-radius: 6px; padding: 6px 12px;
                background: #ffffff; color: #0a0a0a; font-size: 13px; font-weight: 500;
            }}
            QPushButton:hover {{ border-color: #0a0a0a; }}
            QPushButton:focus {{ border: 2px solid #0a0a0a; padding: 5px 11px; }}
            QPushButton:disabled {{ background: #e0e0e0; border-color: #e0e0e0; color: #aaaaaa; }}
            #analyzeButton {{ border-top-left-radius: 0; border-bottom-left-radius: 0; background: #0a0a0a; color: #ffffff; border-color: #0a0a0a; }}
            #analyzeButton:disabled {{ background: #b7b7b7; color: #eeeeee; border-color: #b7b7b7; }}
            #downloadButton:enabled {{ background: #0a0a0a; color: #ffffff; border-color: #0a0a0a; font-size: 14px; }}
            #downloadButton:disabled {{ background: #e0e0e0; color: #aaaaaa; border: 0; }}
            #outlineButton {{ background: #ffffff; border-color: #cccccc; font-weight: 400; }}
            #segment {{ background: #eeeeee; border: 0; border-radius: 8px; }}
            #segmentButton {{ border: 0; border-radius: 6px; color: #555555; background: transparent; padding: 7px; font-size: 13px; font-weight: 500; }}
            #segmentButton[active="true"] {{ background: #0a0a0a; color: #ffffff; }}
            #segmentButton[active="false"] {{ background: transparent; color: #555555; }}
            #segmentButton:focus {{ border: 2px solid #0a0a0a; padding: 5px; }}
            QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 30px; border: 0; }}
            QComboBox::down-arrow {{ image: url("{arrow}"); width: 10px; height: 6px; }}
            #progressMeta {{ color: #555555; font-size: 12px; background: transparent; }}
            QProgressBar {{ background: #e0e0e0; border: 0; border-radius: 2px; }}
            QProgressBar::chunk {{ background: #0a0a0a; border-radius: 2px; }}
            #errorText {{ color: #0a0a0a; font-size: 12px; background: transparent; }}
            #completionText {{ color: #0a0a0a; background: transparent; }}
            #linkButton {{ border: 0; padding: 2px; color: #0a0a0a; text-decoration: underline; background: transparent; }}
            #linkButton:focus {{ border: 2px solid #0a0a0a; padding: 0; }}
            QComboBox QAbstractItemView {{ background: #ffffff; color: #0a0a0a; border: 1px solid #cccccc; selection-background-color: #0a0a0a; selection-color: #ffffff; }}
            QComboBox QAbstractItemView::item {{ min-height: 34px; padding: 4px 10px; border-bottom: 1px solid #eeeeee; }}
            QComboBox QAbstractItemView::item:hover {{ background: #f0f0f0; color: #0a0a0a; }}
            QComboBox QAbstractItemView::item:selected {{ background: #0a0a0a; color: #ffffff; }}
        """)
        self.analyze_button.configure_colors("#0a0a0a", "#333333", "#b7b7b7")
        self.download_button.configure_colors("#0a0a0a", "#333333", "#e0e0e0")
        self.choose_button.configure_colors("#ffffff", "#eeeeee")
        self.open_folder_button.configure_colors("#ffffff", "#eeeeee")
        self.update_toggle_visuals(True)

    def update_url_state(self):
        text = self.url.text().strip()
        valid = bool(YOUTUBE_URL_RE.match(text))
        state = "valid" if valid else "invalid" if text else "empty"
        self.url.setProperty("urlState", state)
        self.url.style().unpolish(self.url)
        self.url.style().polish(self.url)
        self.url_error.setText("" if valid or not text else "insira uma url válida do youtube")
        self.analyze_button.setEnabled(valid and self.engine_available and not self.busy)

    def set_video_mode(self):
        self.update_toggle_visuals(True)
        self.populate_formats()

    def set_audio_mode(self):
        self.update_toggle_visuals(False)
        self.populate_formats()

    def update_toggle_visuals(self, video_active):
        self.video_button.setProperty("active", video_active)
        self.audio_button.setProperty("active", not video_active)
        for button in (self.video_button, self.audio_button):
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()
        if video_active:
            self.video_button.configure_colors("#0a0a0a", "#333333")
            self.audio_button.configure_colors("#eeeeee", "#dddddd")
        else:
            self.video_button.configure_colors("#eeeeee", "#dddddd")
            self.audio_button.configure_colors("#0a0a0a", "#333333")

    def run_worker(self, action, success, quiet=False, **kwargs):
        self.thread = QThread(self)
        self.worker = Worker(action, **kwargs)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(success)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        if not quiet:
            self.set_busy(True)
        self.thread.start()

    def engine_ready(self, message):
        self.engine_available = True
        self.status.clear()
        self.status.hide()
        self.update_url_state()

    def analyze(self):
        if not YOUTUBE_URL_RE.match(self.url.text().strip()) or self.busy:
            return
        self.clear_feedback()
        self.status.setText("analisando formatos…")
        self.run_worker("analyze", self.analysis_ready, url=self.url.text().strip())

    def analysis_ready(self, info):
        self.info = info
        title = info.get("title") or "vídeo encontrado"
        display_title = title.lower()
        self.video_title.setText(display_title if len(display_title) <= 92 else display_title[:91].rstrip() + "…")
        channel = (info.get("channel") or info.get("uploader") or "canal desconhecido").lower()
        self.video_meta.setText(f"canal: {channel}  ·  duração: {format_duration(info.get('duration'))}")
        self.load_thumbnail(info.get("id"))
        self.populate_formats()
        self.show_result_card()
        self.status.clear()
        self.status.hide()
        self.set_busy(False)

    def load_thumbnail(self, video_id):
        self.thumbnail.clear()
        self.thumbnail.setText("…")
        if not video_id:
            return
        reply = self.network.get(QNetworkRequest(QUrl(f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg")))
        reply.finished.connect(lambda: self.thumbnail_ready(reply))

    def thumbnail_ready(self, reply):
        data = reply.readAll()
        reply.deleteLater()
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            self.thumbnail.setText("")
            scaled = pixmap.scaled(64, 48, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            x = max(0, (scaled.width() - 64) // 2)
            y = max(0, (scaled.height() - 48) // 2)
            self.thumbnail.setPixmap(scaled.copy(x, y, 64, 48))

    def show_result_card(self):
        self.result_card.setMaximumHeight(0)
        self.result_card.show()
        self.result_animation = QPropertyAnimation(self.result_card, b"maximumHeight", self)
        self.result_animation.setDuration(200)
        self.result_animation.setStartValue(0)
        self.result_animation.setEndValue(70)
        self.result_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.result_animation.start()

    def populate_formats(self):
        self.quality.clear()
        if not self.info:
            self.quality.hide()
            self.audio_bitrate.hide()
            self.options_hint.show()
            self.download_button.setEnabled(False)
            return
        self.options_hint.hide()
        formats = self.info.get("formats", [])
        audio_candidates = [f for f in formats if f.get("acodec") not in (None, "none") and f.get("vcodec") == "none"]
        audio_candidates.sort(key=lambda f: f.get("abr") or f.get("tbr") or 0, reverse=True)
        self.best_audio_selector = str(audio_candidates[0]["format_id"]) if audio_candidates else "bestaudio"

        if self.video_button.isChecked():
            self.quality.show()
            self.audio_bitrate.hide()
            candidates = [f for f in formats if f.get("vcodec") not in (None, "none") and f.get("height")]
            best_by_output = {}
            for fmt in candidates:
                height = int(fmt["height"])
                source_ext = str(fmt.get("ext") or "").lower()
                output_ext = source_ext if source_ext in ("mp4", "webm") else "mkv"
                key = (height, output_ext)
                current = best_by_output.get(key)
                score = (fmt.get("fps") or 0, fmt.get("tbr") or 0)
                old_score = ((current or {}).get("fps") or 0, (current or {}).get("tbr") or 0)
                if current is None or score > old_score:
                    best_by_output[key] = fmt
            ordered = sorted(best_by_output.items(), key=lambda item: (item[0][0], item[0][1] == "mp4"), reverse=True)
            for (height, output_ext), fmt in ordered:
                fps = f" · {int(fmt['fps'])} fps" if fmt.get("fps") else ""
                label = f"vídeo · {height}p{fps} · {output_ext.lower()}"
                selector = str(fmt["format_id"])
                if fmt.get("acodec") in (None, "none"):
                    if output_ext == "mp4":
                        selector += "+bestaudio[ext=m4a]/" + str(fmt["format_id"]) + "+bestaudio"
                    elif output_ext == "webm":
                        selector += "+bestaudio[ext=webm]/" + str(fmt["format_id"]) + "+bestaudio"
                    else:
                        selector += "+bestaudio"
                self.quality.addItem(label, {"selector": selector, "output_ext": output_ext})
        else:
            self.quality.hide()
            self.audio_bitrate.show()
        self.refresh_download_state()

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "escolha onde salvar", self.destination.text())
        if folder:
            self.destination.setText(folder)

    def download(self):
        destination = self.destination.text().strip()
        if not destination or not Path(destination).is_dir():
            self.show_error("escolha uma pasta válida para salvar o arquivo.")
            return
        if not ffmpeg_location():
            self.show_error("o ffmpeg não está disponível.")
            return
        self.clear_feedback()
        self.progress.setValue(0)
        self.progress.show()
        self.progress_meta.setText("0%")
        self.progress_meta.show()
        self.status.setText("iniciando download…")
        if self.video_button.isChecked():
            selected = self.quality.currentData()
            format_id = selected["selector"]
            output_ext = selected["output_ext"]
            mode = "video"
        else:
            format_id = self.best_audio_selector
            output_ext = "mp3"
            mode = "audio"
        self.run_worker(
            "download", self.download_ready, url=self.url.text().strip(), destination=destination,
            format_id=format_id, output_ext=output_ext, mode=mode, audio_format="mp3",
            audio_quality=self.audio_bitrate.currentData(),
        )

    def download_ready(self, result):
        self.last_download_path = result.get("path")
        self.progress.setValue(100)
        self.progress.hide()
        self.progress_meta.hide()
        self.status.hide()
        self.completion.show()
        self.set_busy(False)
        self.reset_timer.start(8000)

    def update_progress(self, value, detail):
        if not self.progress.isVisible():
            self.status.setText(detail.replace("|", " · "))
            return
        self.progress.setValue(round(value))
        speed, _, eta = detail.partition("|")
        meta = f"{round(value)}%"
        if speed and speed != "N/A":
            meta += f"  ·  {speed}"
        if eta and eta != "N/A":
            meta += f"  ·  restante {eta}"
        self.progress_meta.setText(meta)

    def open_folder(self):
        folder = Path(self.last_download_path).parent if self.last_download_path else Path(self.destination.text())
        try:
            os.startfile(str(folder))
        except OSError:
            self.show_error("não foi possível abrir a pasta.")

    def set_busy(self, busy):
        self.busy = busy
        self.url.setEnabled(not busy)
        self.video_button.setEnabled(not busy)
        self.audio_button.setEnabled(not busy)
        self.quality.setEnabled(not busy and self.info is not None and self.quality.count() > 0)
        self.audio_bitrate.setEnabled(not busy)
        self.choose_button.setEnabled(not busy)
        self.destination.setEnabled(not busy)
        self.update_url_state()
        self.refresh_download_state()

    def refresh_download_state(self):
        ready = self.info is not None and not self.busy
        if self.video_button.isChecked():
            ready = ready and self.quality.count() > 0
        self.download_button.setEnabled(ready)

    def clear_feedback(self):
        self.reset_timer.stop()
        self.error_label.hide()
        self.completion.hide()
        self.status.show()

    def show_error(self, message):
        self.set_busy(False)
        short = message.strip().splitlines()[-1]
        if len(short) > 130:
            short = short[:129].rstrip() + "…"
        self.progress.hide()
        self.progress_meta.hide()
        self.completion.hide()
        self.error_label.setText(f"✕ erro: {short.lower()}")
        self.error_label.show()
        self.status.setText("")

    def reset_form(self):
        self.info = None
        self.last_download_path = None
        self.url.clear()
        self.result_card.hide()
        self.quality.clear()
        self.video_button.setChecked(True)
        self.update_toggle_visuals(True)
        self.options_hint.show()
        self.quality.hide()
        self.audio_bitrate.hide()
        self.progress.hide()
        self.progress_meta.hide()
        self.completion.hide()
        self.error_label.hide()
        self.status.clear()
        self.status.hide()
        self.refresh_download_state()
        self.url.setFocus()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setFont(QFont("Segoe UI", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
