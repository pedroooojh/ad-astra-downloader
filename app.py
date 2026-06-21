import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, QSize, QThread, QTimer, QUrl, QVariantAnimation, QObject, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QFileDialog, QFrame,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton,
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

def is_auth_required(message: str) -> bool:
    lowered = message.lower()
    return "sign in to confirm" in lowered and "bot" in lowered


def firefox_available() -> bool:
    paths = (
        Path(os.getenv("PROGRAMFILES", "")) / "Mozilla Firefox/firefox.exe",
        Path(os.getenv("PROGRAMFILES(X86)", "")) / "Mozilla Firefox/firefox.exe",
        Path(os.getenv("LOCALAPPDATA", "")) / "Mozilla Firefox/firefox.exe",
    )
    return any(path.is_file() for path in paths)


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


def javascript_args() -> list[str]:
    bundled = resource_path("bin/node.exe")
    node = str(bundled) if bundled.exists() else shutil.which("node")
    if not node:
        return []
    return ["--js-runtimes", f"node:{node}", "--remote-components", "ejs:github"]


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
        command = [str(exe), *javascript_args(), "--dump-single-json", "--no-playlist", "--no-warnings"]
        browser = self.kwargs.get("browser")
        if browser:
            command += ["--cookies-from-browser", browser]
        command.append(self.kwargs["url"])
        result = subprocess.run(
            command,
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
            str(exe), *javascript_args(), "--newline", "--no-playlist", "--windows-filenames", "--no-simulate",
            "--progress-template", "%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s",
            "--print", "after_move:__AD_ASTRA_FILE__%(filepath)s",
            "-f", self.kwargs["format_id"], "-o", output,
        ]
        browser = self.kwargs.get("browser")
        if browser:
            command += ["--cookies-from-browser", browser]
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


class ClickableLineEdit(QLineEdit):
    clicked = Signal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.info = None
        self.thread = None
        self.worker = None
        self.busy = False
        self.engine_available = False
        self.analysis_browser = None
        self.active_browser = None
        self.best_audio_selector = "bestaudio"
        self.last_download_path = None
        self.network = QNetworkAccessManager(self)
        self.result_animation = None
        self.reset_timer = QTimer(self)
        self.reset_timer.setSingleShot(True)
        self.reset_timer.timeout.connect(self.reset_form)

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(str(resource_path("assets/adastra.png"))))
        self.setFixedSize(420, 720)
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
        layout.setContentsMargins(18, 14, 18, 16)
        layout.setSpacing(8)

        self.logo = QLabel()
        self.logo.setObjectName("logo")
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_pixmap = QPixmap(str(resource_path("assets/adastra.png")))
        self.logo.setPixmap(logo_pixmap.scaled(
            64, 64, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))
        self.logo.setFixedHeight(64)
        layout.addWidget(self.logo)

        tagline = QLabel("per aspera ad astra!")
        tagline.setObjectName("tagline")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tagline)
        layout.addSpacing(10)

        card = QFrame()
        card.setObjectName("mainCard")
        form = QVBoxLayout(card)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(9)

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
        self.url_error.setFixedHeight(12)
        form.addWidget(self.url_error)

        self.result_card = QFrame()
        self.result_card.setObjectName("resultCard")
        self.result_card.setMinimumHeight(0)
        self.result_card.setMaximumHeight(66)
        self.result_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        result_layout = QHBoxLayout(self.result_card)
        result_layout.setContentsMargins(10, 8, 10, 8)
        result_layout.setSpacing(12)
        self.thumbnail = QLabel()
        self.thumbnail.setObjectName("thumbnail")
        self.thumbnail.setFixedSize(56, 46)
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        result_text = QVBoxLayout()
        result_text.setSpacing(2)
        self.video_title = QLabel()
        self.video_title.setObjectName("videoTitle")
        self.video_title.setWordWrap(True)
        self.video_title.setFixedHeight(28)
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
        self.options_hint.setFixedHeight(32)
        form.addWidget(self.options_hint)

        self.quality_label = QLabel("qualidade")
        self.quality_label.setObjectName("sectionLabel")
        self.quality_label.hide()
        form.addWidget(self.quality_label)

        self.quality_panel = QFrame()
        self.quality_panel.setObjectName("qualityPanel")
        self.quality_grid = QGridLayout(self.quality_panel)
        self.quality_grid.setContentsMargins(0, 0, 0, 0)
        self.quality_grid.setHorizontalSpacing(7)
        self.quality_grid.setVerticalSpacing(7)
        self.quality_grid.setColumnStretch(4, 1)
        self.quality_panel.hide()
        form.addWidget(self.quality_panel)

        self.format_buttons = []
        self.video_options = []
        self.selected_format = None
        self.selected_audio_quality = "192"

        self.destination_label = QLabel("destino")
        self.destination_label.setObjectName("sectionLabel")
        form.addWidget(self.destination_label)

        destination_box = QFrame()
        destination_box.setObjectName("destinationBox")
        destination_row = QHBoxLayout(destination_box)
        destination_row.setContentsMargins(10, 0, 0, 0)
        destination_row.setSpacing(0)
        self.destination = ClickableLineEdit(str(Path.home() / "Downloads"))
        self.destination.setObjectName("destinationInput")
        self.destination.setFixedHeight(36)
        self.destination.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.destination.setReadOnly(True)
        self.destination.setAccessibleName("pasta de destino")
        self.destination.setToolTip("clique para escolher a pasta de destino")
        self.destination.clicked.connect(self.choose_folder)
        self.choose_button = AnimatedButton("")
        self.choose_button.setObjectName("folderButton")
        self.choose_button.setFixedSize(38, 36)
        self.choose_button.setIcon(QIcon(str(resource_path("assets/folder.svg"))))
        self.choose_button.setIconSize(QSize(18, 18))
        self.choose_button.clicked.connect(self.choose_folder)
        self._button_accessibility(self.choose_button, "escolher pasta de destino")
        destination_row.addWidget(self.destination, 1)
        destination_row.addWidget(self.choose_button)
        form.addWidget(destination_box)

        self.download_button = AnimatedButton("⇩  baixar")
        self.download_button.setObjectName("downloadButton")
        self.download_button.setFixedHeight(42)
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self.download)
        self._button_accessibility(self.download_button, "iniciar o download")
        form.addWidget(self.download_button)

        self.download_hint = QLabel("analise um link primeiro")
        self.download_hint.setObjectName("downloadHint")
        self.download_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form.addWidget(self.download_hint)

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

        self.status = QLabel("preparando…")
        self.status.setObjectName("secondary")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form.addWidget(self.status)

        layout.addWidget(card)
        layout.addStretch()
        footer = QLabel("feito por editores para editores")
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)
        self.setCentralWidget(root)

    def _set_style(self):
        self.setStyleSheet("""
            QWidget { background: #ffffff; color: #111111; font-size: 12px; font-weight: 400; }
            #root { background: #ffffff; }
            QLabel { background: transparent; }
            #logo { background: transparent; }
            #tagline { color: #777777; font-size: 12px; font-weight: 600; }
            #footer { color: #999999; font-size: 9px; font-weight: 400; }
            #secondary { color: #777777; font-size: 12px; }
            #mainCard { background: transparent; border: 0; }
            #resultCard { background: #f7f7f7; border: 1px solid #d8d8d8; border-radius: 9px; }
            #thumbnail { background: #ececec; border: 0; border-radius: 6px; color: #777777; }
            #videoTitle { color: #111111; font-size: 13px; font-weight: 600; }
            #resultCard #secondary { color: #666666; font-size: 12px; }
            #optionsHint, #downloadHint { color: #888888; font-size: 11px; }
            #sectionLabel { color: #777777; font-size: 11px; font-weight: 600; }
            QLineEdit { background: #ffffff; color: #111111; border: 1px solid #c8c8c8; border-radius: 8px; padding: 6px 10px; font-size: 13px; placeholder-text-color: #999999; selection-background-color: #222222; selection-color: #ffffff; }
            QLineEdit#urlInput { border-top-right-radius: 0; border-bottom-right-radius: 0; }
            QLineEdit#urlInput:focus { border: 1px solid #111111; }
            QLineEdit[urlState="valid"] { border: 1px solid #444444; }
            QLineEdit[urlState="invalid"] { border: 1px solid #d86a6a; }
            #urlError { color: #cc5555; font-size: 11px; }
            QPushButton { border: 1px solid #c8c8c8; border-radius: 8px; padding: 6px 12px; color: #222222; font-size: 12px; font-weight: 600; }
            QPushButton:focus { border: 1px solid #111111; }
            #analyzeButton { border-top-left-radius: 0; border-bottom-left-radius: 0; background: #111111; color: #ffffff; border-color: #111111; }
            #analyzeButton:disabled { color: #888888; border-color: #dddddd; }
            #segment { background: #eeeeee; border: 1px solid #d2d2d2; border-radius: 10px; }
            #segmentButton { border: 0; border-radius: 8px; color: #666666; padding: 7px; font-size: 12px; }
            #segmentButton[active="true"] { color: #ffffff; }
            #segmentButton[active="false"] { color: #666666; }
            #qualityPanel { background: transparent; }
            #formatChip { border: 1px solid #bdbdbd; border-radius: 15px; color: #555555; padding: 5px 10px; font-size: 11px; }
            #formatChip[active="true"] { color: #ffffff; border-color: #111111; }
            #formatChip[active="false"] { color: #555555; }
            #destinationBox { background: #ffffff; border: 1px solid #c8c8c8; border-radius: 8px; }
            #destinationInput { background: transparent; border: 0; padding: 0; color: #333333; }
            #destinationInput:focus { border: 0; }
            #folderButton { border: 0; border-left: 1px solid #d2d2d2; border-radius: 7px; padding: 0; }
            #downloadButton { border: 0; border-radius: 8px; color: #ffffff; font-size: 14px; }
            #downloadButton:disabled { color: #999999; }
            #progressMeta { color: #555555; font-size: 12px; }
            QProgressBar { background: #dddddd; border: 0; border-radius: 2px; }
            QProgressBar::chunk { background: #111111; border-radius: 2px; }
            #errorText { color: #a94444; font-size: 12px; }
            #completionText { color: #111111; }
            #linkButton { border: 0; padding: 2px; color: #111111; text-decoration: underline; }
        """)
        self.analyze_button.configure_colors("#111111", "#333333", "#dddddd")
        self.download_button.configure_colors("#111111", "#333333", "#e2e2e2")
        self.choose_button.configure_colors("#f8f8f8", "#e8e8e8")
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
            self.video_button.configure_colors("#111111", "#333333")
            self.audio_button.configure_colors("#eeeeee", "#dddddd")
        else:
            self.video_button.configure_colors("#eeeeee", "#dddddd")
            self.audio_button.configure_colors("#111111", "#333333")

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
        self.info = None
        self.active_browser = None
        self.refresh_download_state()
        self.start_analysis()

    def start_analysis(self, browser=None):
        self.analysis_browser = browser
        self.clear_feedback()
        self.status.setText("analisando com sua sessão…" if browser else "analisando formatos…")
        self.run_worker(
            "analyze", self.analysis_ready, url=self.url.text().strip(), browser=browser,
        )

    def analysis_ready(self, info):
        self.info = info
        self.active_browser = self.analysis_browser
        title = info.get("title") or "vídeo encontrado"
        display_title = title.lower()
        self.video_title.setText(display_title if len(display_title) <= 92 else display_title[:91].rstrip() + "…")
        channel = (info.get("channel") or info.get("uploader") or "canal desconhecido").lower()
        self.video_meta.setText(f"{channel}  ·  {format_duration(info.get('duration'))}")
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
            scaled = pixmap.scaled(56, 46, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            x = max(0, (scaled.width() - 56) // 2)
            y = max(0, (scaled.height() - 46) // 2)
            self.thumbnail.setPixmap(scaled.copy(x, y, 56, 46))

    def show_result_card(self):
        self.result_card.setMaximumHeight(0)
        self.result_card.show()
        self.result_animation = QPropertyAnimation(self.result_card, b"maximumHeight", self)
        self.result_animation.setDuration(200)
        self.result_animation.setStartValue(0)
        self.result_animation.setEndValue(66)
        self.result_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.result_animation.start()

    def populate_formats(self):
        self.clear_quality_buttons()
        if not self.info:
            self.quality_label.hide()
            self.quality_panel.hide()
            self.options_hint.show()
            self.selected_format = None
            self.download_hint.setText("analise um link primeiro")
            self.download_button.setEnabled(False)
            return
        self.options_hint.hide()
        self.quality_label.show()
        self.quality_panel.show()
        formats = self.info.get("formats", [])
        audio_candidates = [f for f in formats if f.get("acodec") not in (None, "none") and f.get("vcodec") == "none"]
        audio_candidates.sort(key=lambda f: f.get("abr") or f.get("tbr") or 0, reverse=True)
        self.best_audio_selector = str(audio_candidates[0]["format_id"]) if audio_candidates else "bestaudio"

        if self.video_button.isChecked():
            candidates = [f for f in formats if f.get("vcodec") not in (None, "none") and f.get("height")]
            best_by_height = {}
            for fmt in candidates:
                height = int(fmt["height"])
                source_ext = str(fmt.get("ext") or "").lower()
                output_ext = source_ext if source_ext in ("mp4", "webm") else "mkv"
                current = best_by_height.get(height)
                score = (output_ext == "mp4", fmt.get("fps") or 0, fmt.get("tbr") or 0)
                old_ext = str((current or {}).get("ext") or "").lower()
                old_score = (old_ext == "mp4", (current or {}).get("fps") or 0, (current or {}).get("tbr") or 0)
                if current is None or score > old_score:
                    best_by_height[height] = fmt
            self.video_options = []
            for height, fmt in sorted(best_by_height.items(), reverse=True):
                output_ext = str(fmt.get("ext") or "mkv").lower()
                if output_ext not in ("mp4", "webm"):
                    output_ext = "mkv"
                fps_value = round(fmt.get("fps") or 0)
                selector = str(fmt["format_id"])
                if fmt.get("acodec") in (None, "none"):
                    if output_ext == "mp4":
                        selector += "+bestaudio[ext=m4a]/" + str(fmt["format_id"]) + "+bestaudio"
                    elif output_ext == "webm":
                        selector += "+bestaudio[ext=webm]/" + str(fmt["format_id"]) + "+bestaudio"
                    else:
                        selector += "+bestaudio"
                detail = output_ext + (f" · {fps_value} fps" if fps_value else "")
                self.video_options.append({
                    "label": f"{height}p", "detail": detail,
                    "selector": selector, "output_ext": output_ext,
                })
            options = self.video_options
        else:
            options = [
                {"label": "128 kbps", "detail": "mp3 · 128 kbps", "audio_quality": "128"},
                {"label": "192 kbps", "detail": "mp3 · 192 kbps", "audio_quality": "192"},
                {"label": "320 kbps", "detail": "mp3 · 320 kbps", "audio_quality": "320"},
            ]
        self.render_quality_buttons(options)
        self.refresh_download_state()

    def clear_quality_buttons(self):
        while self.quality_grid.count():
            item = self.quality_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.format_buttons.clear()

    def render_quality_buttons(self, options):
        columns = 4
        for index, option in enumerate(options):
            button = AnimatedButton(option["label"])
            button.setObjectName("formatChip")
            button.setProperty("active", False)
            chip_width = max(58, min(88, len(option["label"]) * 7 + 20))
            button.setFixedSize(chip_width, 30)
            button.setToolTip(option["detail"])
            button.setAccessibleName(f"selecionar {option['label']}")
            button.clicked.connect(lambda checked=False, i=index: self.select_quality(i, options))
            button.configure_colors("#ffffff", "#eeeeee")
            self.quality_grid.addWidget(
                button, index // columns, index % columns,
                alignment=Qt.AlignmentFlag.AlignLeft,
            )
            self.format_buttons.append(button)
        rows = max(1, (len(options) + columns - 1) // columns)
        self.quality_panel.setFixedHeight(rows * 30 + (rows - 1) * 7)
        default_index = 0 if self.video_button.isChecked() else 1
        if options:
            self.select_quality(min(default_index, len(options) - 1), options)

    def select_quality(self, index, options):
        self.selected_format = options[index]
        for button_index, button in enumerate(self.format_buttons):
            active = button_index == index
            button.setProperty("active", active)
            button.style().unpolish(button)
            button.style().polish(button)
            if active:
                button.configure_colors("#111111", "#333333")
            else:
                button.configure_colors("#ffffff", "#eeeeee")
        self.download_hint.setText(self.selected_format["detail"])
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
            selected = self.selected_format
            format_id = selected["selector"]
            output_ext = selected["output_ext"]
            mode = "video"
            audio_quality = "192"
        else:
            format_id = self.best_audio_selector
            output_ext = "mp3"
            mode = "audio"
            audio_quality = self.selected_format["audio_quality"]
        self.run_worker(
            "download", self.download_ready, url=self.url.text().strip(), destination=destination,
            format_id=format_id, output_ext=output_ext, mode=mode, audio_format="mp3",
            audio_quality=audio_quality, browser=self.active_browser,
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
        for button in self.format_buttons:
            button.setEnabled(not busy)
        self.choose_button.setEnabled(not busy)
        self.destination.setEnabled(not busy)
        self.update_url_state()
        self.refresh_download_state()

    def refresh_download_state(self):
        ready = self.info is not None and self.selected_format is not None and not self.busy
        self.download_button.setEnabled(ready)

    def clear_feedback(self):
        self.reset_timer.stop()
        self.error_label.hide()
        self.completion.hide()
        self.status.show()

    def show_error(self, message):
        self.set_busy(False)
        worker_action = getattr(self.worker, "action", None)
        worker_browser = getattr(self.worker, "kwargs", {}).get("browser") if self.worker else None
        if is_auth_required(message) and worker_action == "analyze" and not worker_browser:
            self.progress.hide()
            self.progress_meta.hide()
            self.completion.hide()
            self.error_label.hide()
            self.status.setText("o youtube exige autenticação…")
            self.status.show()
            QTimer.singleShot(150, self.offer_browser_retry)
            return
        lowered = message.lower()
        if worker_browser and is_auth_required(message):
            message = "O YouTube recusou a sessão. Entre no YouTube pelo navegador e tente novamente."
        elif worker_browser and "could not copy" in lowered and "cookie" in lowered:
            message = "Feche o navegador para liberar os cookies e tente novamente."
        elif worker_browser and "failed to decrypt" in lowered and "cookie" in lowered:
            message = "O Windows não permitiu acessar essa sessão. Tente outro navegador."
        short = message.strip().splitlines()[-1]
        if len(short) > 130:
            short = short[:129].rstrip() + "…"
        self.progress.hide()
        self.progress_meta.hide()
        self.completion.hide()
        self.error_label.setText(f"✕ erro: {short.lower()}")
        self.error_label.show()
        self.status.setText("")

    def offer_browser_retry(self):
        if self.busy:
            return
        if not firefox_available():
            self.error_label.setText("✕ instale o firefox e entre no youtube para autorizar esta tentativa.")
            return
        answer = QMessageBox.question(
            self,
            "autenticação necessária",
            f"O YouTube bloqueou a tentativa anônima.\n\n"
            "Tentar novamente usando sua sessão do Mozilla Firefox?\n\n"
            "Os cookies serão lidos localmente pelo yt-dlp somente nesta operação.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.start_analysis("firefox")
        else:
            self.status.hide()
            self.error_label.setText("✕ análise cancelada: o youtube exige autenticação.")
            self.error_label.show()

    def reset_form(self):
        self.info = None
        self.analysis_browser = None
        self.active_browser = None
        self.last_download_path = None
        self.url.clear()
        self.result_card.hide()
        self.clear_quality_buttons()
        self.selected_format = None
        self.video_button.setChecked(True)
        self.update_toggle_visuals(True)
        self.options_hint.show()
        self.quality_label.hide()
        self.quality_panel.hide()
        self.progress.hide()
        self.progress_meta.hide()
        self.completion.hide()
        self.error_label.hide()
        self.status.clear()
        self.status.hide()
        self.download_hint.setText("analise um link primeiro")
        self.refresh_download_state()
        self.url.setFocus()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setFont(QFont("Segoe UI", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
