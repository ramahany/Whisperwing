"""Settings window: General / Speech / Appearance / Hotkeys."""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from config.settings_manager import find_asset
from services.hotkey_service import DEFAULT_HOTKEY, ShortcutRecorder, prettify

MODELS = [
    ("Tiny — fastest", "tiny"),
    ("Base — fast", "base"),
    ("Small — balanced (recommended)", "small"),
    ("Medium — accurate", "medium"),
    ("Large v3 — most accurate", "large-v3"),
]
LANGUAGES = [
    ("Auto detect", "auto"),
    ("English", "en"),
    ("العربية (Arabic)", "ar"),
]
LABEL_WIDTH = 190


class ThemePreview(QFrame):
    """Small painted preview of the purple/black theme."""

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0.0, QColor("#2b1b4d"))
        gradient.setColorAt(0.55, QColor("#17121f"))
        gradient.setColorAt(1.0, QColor("#4c1d95"))
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor("#4a3a68"), 1))
        painter.drawRoundedRect(rect, 12, 12)
        painter.setPen(QColor("#e9d5ff"))
        font = painter.font()
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Whisperwing")
        painter.end()


class SettingsWindow(QWidget):
    settings_saved = Signal(dict)
    scale_preview = Signal(float)
    closed = Signal()

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._recorder = ShortcutRecorder(self)
        self._pending_hotkey = str(settings.get("hotkey"))

        idle_path = find_asset("images", "idle.png")
        self._preview_source = QPixmap(str(idle_path)) if idle_path else QPixmap()

        self.setObjectName("settingsWindow")
        self.setWindowTitle("Whisperwing — Settings")
        self.setMinimumSize(740, 500)
        self.resize(820, 560)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._nav = QListWidget()
        self._nav.setObjectName("sideNav")
        for name in ("General", "Speech", "Appearance", "Hotkeys"):
            self._nav.addItem(name)
        self._nav.setFixedWidth(190)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_general_page())
        self._stack.addWidget(self._build_speech_page())
        self._stack.addWidget(self._build_appearance_page())
        self._stack.addWidget(self._build_hotkeys_page())
        self._nav.currentRowChanged.connect(self._stack.setCurrentIndex)
        self._nav.setCurrentRow(0)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self._stack, 1)
        content_layout.addWidget(self._build_footer())

        root.addWidget(self._nav)
        root.addWidget(content, 1)

        self._recorder.captured.connect(self._on_shortcut_captured)
        self._recorder.cancelled.connect(self._on_shortcut_cancelled)

    # ----------------------------------------------------------- builders

    def _page(self, title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(18)
        title_label = QLabel(title)
        title_label.setObjectName("pageTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("pageSubtitle")
        subtitle_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        return page, layout

    def _field_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        label.setFixedWidth(LABEL_WIDTH)
        return label

    def _build_footer(self) -> QWidget:
        footer = QWidget()
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(32, 12, 32, 20)
        self._status_label = QLabel("")
        self._status_label.setObjectName("pageSubtitle")
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        save_button = QPushButton("Save Settings")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self._save)
        layout.addWidget(self._status_label)
        layout.addStretch(1)
        layout.addWidget(close_button)
        layout.addWidget(save_button)
        return footer

    def _build_general_page(self) -> QWidget:
        page, layout = self._page(
            "General", "How Whisperwing behaves on your system."
        )
        self._startup_check = QCheckBox("Launch on system startup")
        self._startup_check.setChecked(bool(self._settings.get("launch_on_startup")))
        self._on_top_check = QCheckBox("Keep mascot above other windows")
        self._on_top_check.setChecked(bool(self._settings.get("always_on_top")))
        layout.addWidget(self._startup_check)
        layout.addWidget(self._on_top_check)
        layout.addStretch(1)
        return page

    def _build_speech_page(self) -> QWidget:
        page, layout = self._page(
            "Speech", "Local transcription engine — everything stays on this PC."
        )

        self._model_combo = QComboBox()
        for label, value in MODELS:
            self._model_combo.addItem(label, value)
        self._model_combo.setCurrentIndex(
            max(0, self._model_combo.findData(str(self._settings.get("model"))))
        )
        self._model_combo.setToolTip(
            "Bigger models are more accurate but slower. "
            "Each model is downloaded once, then used fully offline."
        )

        self._language_combo = QComboBox()
        for label, value in LANGUAGES:
            self._language_combo.addItem(label, value)
        self._language_combo.setCurrentIndex(
            max(0, self._language_combo.findData(str(self._settings.get("language"))))
        )

        for text, widget in (("Whisper model", self._model_combo), ("Language", self._language_combo)):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addWidget(self._field_label(text))
            row_layout.addWidget(widget)
            row_layout.addStretch(1)
            layout.addWidget(row)

        note = QLabel(
            "All transcription runs locally with Faster-Whisper. "
            "No audio, text or telemetry ever leaves your machine."
        )
        note.setObjectName("pageSubtitle")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        return page

    def _build_appearance_page(self) -> QWidget:
        page, layout = self._page(
            "Appearance", "Tune the mascot and preview the theme."
        )

        scale_row = QWidget()
        scale_layout = QHBoxLayout(scale_row)
        scale_layout.setContentsMargins(0, 0, 0, 0)
        self._scale_slider = QSlider(Qt.Orientation.Horizontal)
        self._scale_slider.setRange(50, 200)
        self._scale_slider.setValue(int(float(self._settings.get("mascot_scale")) * 100))
        self._scale_value = QLabel(f"{self._scale_slider.value()}%")
        self._scale_slider.valueChanged.connect(self._on_scale_changed)
        scale_layout.addWidget(self._field_label("Mascot size"))
        scale_layout.addWidget(self._scale_slider, 1)
        scale_layout.addWidget(self._scale_value)
        layout.addWidget(scale_row)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(20)
        self._preview_label = QLabel()
        self._preview_label.setFixedHeight(190)
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._theme_preview = ThemePreview()
        self._theme_preview.setFixedSize(230, 130)
        card_layout.addWidget(self._preview_label, 1)
        card_layout.addWidget(self._theme_preview)
        layout.addWidget(card)

        self._on_scale_changed(self._scale_slider.value())
        layout.addStretch(1)
        return page

    def _build_hotkeys_page(self) -> QWidget:
        page, layout = self._page(
            "Hotkeys", "Global shortcut for starting and stopping dictation."
        )

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(12)
        self._hotkey_field = QLineEdit(prettify(self._pending_hotkey))
        self._hotkey_field.setReadOnly(True)
        self._hotkey_field.setFixedWidth(220)
        self._record_button = QPushButton("Record new")
        self._record_button.clicked.connect(self._start_capture)
        restore_button = QPushButton("Restore default")
        restore_button.clicked.connect(self._restore_default)
        row_layout.addWidget(self._field_label("Dictation shortcut"))
        row_layout.addWidget(self._hotkey_field)
        row_layout.addWidget(self._record_button)
        row_layout.addWidget(restore_button)
        row_layout.addStretch(1)
        layout.addWidget(row)

        hint = QLabel(
            "Click “Record new”, then press the combination anywhere. "
            "Esc cancels. The shortcut must include Ctrl, Alt or Shift."
        )
        hint.setObjectName("pageSubtitle")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch(1)
        return page

    # ------------------------------------------------------------- actions

    def _on_scale_changed(self, value: int) -> None:
        self._scale_value.setText(f"{value}%")
        self.scale_preview.emit(value / 100)
        if not self._preview_source.isNull():
            height = max(48, int(175 * value / 100))
            self._preview_label.setPixmap(
                self._preview_source.scaledToHeight(
                    height, Qt.TransformationMode.SmoothTransformation
                )
            )
        else:
            self._preview_label.setText("Mascot preview — add images/idle.png")

    def _start_capture(self) -> None:
        self._record_button.setText("Press keys…")
        self._record_button.setEnabled(False)
        self._hotkey_field.setText("Press the new shortcut…")
        self._recorder.start()

    def _on_shortcut_captured(self, combo: str) -> None:
        self._reset_record_button()
        self._pending_hotkey = combo
        self._hotkey_field.setText(prettify(combo))

    def _on_shortcut_cancelled(self) -> None:
        self._reset_record_button()
        self._hotkey_field.setText(prettify(self._pending_hotkey))

    def _reset_record_button(self) -> None:
        self._record_button.setText("Record new")
        self._record_button.setEnabled(True)

    def _restore_default(self) -> None:
        self._pending_hotkey = DEFAULT_HOTKEY
        self._hotkey_field.setText(prettify(DEFAULT_HOTKEY))

    def _save(self) -> None:
        self.settings_saved.emit(
            {
                "launch_on_startup": self._startup_check.isChecked(),
                "always_on_top": self._on_top_check.isChecked(),
                "model": self._model_combo.currentData(),
                "language": self._language_combo.currentData(),
                "mascot_scale": self._scale_slider.value() / 100,
                "hotkey": self._pending_hotkey,
            }
        )

    def show_status(self, message: str, error: bool = False) -> None:
        self._status_label.setText(message)
        self._status_label.setStyleSheet("color: #f0abfc;" if error else "")
        QTimer.singleShot(4000, lambda: self._status_label.setText(""))

    def closeEvent(self, event) -> None:
        self.closed.emit()
        super().closeEvent(event)
