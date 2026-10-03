"""Microphone capture and local Faster-Whisper transcription.

Recording uses sounddevice's callback thread; model loading and transcription
run on background threads so the UI never blocks.
"""

import logging
import threading
import time

import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, QThread, QTimer, Signal

log = logging.getLogger(__name__)

SAMPLE_RATE = 16000          # whisper-native sample rate
BLOCK_SILENCE_RMS = 0.015    # block RMS below this counts as silence
SILENCE_STOP_SECONDS = 2.0   # auto-stop after this much trailing silence
MIN_AUDIO_SECONDS = 0.3      # shorter recordings are treated as "no speech"
MAX_RECORD_SECONDS = 120     # hard safety cap

MODEL_DEVICE = "cpu"
MODEL_COMPUTE = "int8"


class TranscriptionWorker(QThread):
    """Runs Faster-Whisper on one captured recording."""

    finished_text = Signal(str)
    failed = Signal(str)

    def __init__(self, service: "SpeechService", audio: np.ndarray, language, parent=None):
        super().__init__(parent)
        self._service = service
        self._audio = audio
        self._language = language

    def run(self) -> None:
        try:
            model = self._service.get_model()
            segments, info = model.transcribe(
                self._audio,
                language=self._language,
                beam_size=5,
                vad_filter=True,
                condition_on_previous_text=False,
            )
            text = " ".join(segment.text.strip() for segment in segments).strip()
            log.info(
                "Transcribed %.1fs of audio (lang=%s, prob=%.2f) -> %d chars",
                self._audio.shape[0] / SAMPLE_RATE,
                info.language,
                info.language_probability,
                len(text),
            )
            self.finished_text.emit(text)
        except Exception as exc:  # noqa: BLE001 - report everything to the UI
            log.exception("Transcription failed")
            self.failed.emit(str(exc))


class SpeechService(QObject):
    """Records microphone audio and transcribes it locally."""

    recording_started = Signal()
    recording_stopped = Signal()
    transcription_finished = Signal(str)
    transcription_error = Signal(str)
    model_status = Signal(str)

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._stream: sd.InputStream | None = None
        self._frames: list[np.ndarray] = []
        self._recording = False
        self._started_at = 0.0
        self._last_sound_at = 0.0
        self._speech_seen = False
        self._worker: TranscriptionWorker | None = None
        self._model = None
        self._model_size: str | None = None
        self._model_lock = threading.Lock()
        self._silence_timer = QTimer(self)
        self._silence_timer.setInterval(200)
        self._silence_timer.timeout.connect(self._check_silence)

    # ---------------------------------------------------------- recording

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start_recording(self) -> None:
        if self._recording or self._worker is not None:
            return
        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=self._on_audio
            )
            self._stream.start()
        except Exception as exc:  # noqa: BLE001
            log.error("Could not open the microphone: %s", exc)
            self._stream = None
            self.transcription_error.emit(f"Could not open the microphone: {exc}")
            return
        now = time.monotonic()
        self._frames = []
        self._speech_seen = False
        self._started_at = now
        self._last_sound_at = now
        self._recording = True
        self._silence_timer.start()
        log.info("Recording started")
        self.recording_started.emit()

    def stop_recording(self) -> None:
        if not self._recording:
            return
        self._recording = False
        self._silence_timer.stop()
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:  # noqa: BLE001
                pass
            self._stream = None
        audio = np.concatenate(self._frames) if self._frames else np.zeros(0, dtype="float32")
        self._frames = []
        duration = audio.shape[0] / SAMPLE_RATE
        log.info("Recording stopped (%.1fs)", duration)
        self.recording_stopped.emit()
        if duration < MIN_AUDIO_SECONDS:
            log.info("Recording too short; skipping transcription")
            self.transcription_finished.emit("")
            return
        language = self._settings.get("language")
        self._spawn_worker(audio, None if language == "auto" else language)

    def _on_audio(self, indata, frames, time_info, status) -> None:
        if status:
            log.warning("Audio stream status: %s", status)
        try:
            mono = indata[:, 0]
            self._frames.append(mono.copy())
            rms = float(np.sqrt(np.mean(mono * mono)))
            if rms >= BLOCK_SILENCE_RMS:
                self._speech_seen = True
                self._last_sound_at = time.monotonic()
        except Exception:  # noqa: BLE001 - audio callback must never raise
            log.exception("Audio callback error")

    def _check_silence(self) -> None:
        if not self._recording:
            return
        now = time.monotonic()
        if now - self._started_at > MAX_RECORD_SECONDS:
            log.info("Maximum recording length reached; stopping")
            self.stop_recording()
        elif self._speech_seen and now - self._last_sound_at >= SILENCE_STOP_SECONDS:
            log.info("Silence detected; stopping recording")
            self.stop_recording()

    # ----------------------------------------------------- model handling

    def _spawn_worker(self, audio: np.ndarray, language) -> None:
        self._worker = TranscriptionWorker(self, audio, language)
        self._worker.finished_text.connect(self.transcription_finished)
        self._worker.failed.connect(self.transcription_error)
        self._worker.finished.connect(self._worker_finished)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def _worker_finished(self) -> None:
        self._worker = None

    def get_model(self):
        """Return the loaded WhisperModel, loading/reloading when needed.

        Called from worker threads; the lock keeps concurrent loads safe.
        """
        wanted = str(self._settings.get("model"))
        with self._model_lock:
            if self._model is not None and self._model_size == wanted:
                return self._model
            self.model_status.emit(f"Loading model '{wanted}'…")
            log.info(
                "Loading Faster-Whisper model '%s' (device=%s, compute=%s)",
                wanted, MODEL_DEVICE, MODEL_COMPUTE,
            )
            from faster_whisper import WhisperModel  # imported lazily: heavy

            started = time.monotonic()
            model = WhisperModel(wanted, device=MODEL_DEVICE, compute_type=MODEL_COMPUTE)
            self._model = model
            self._model_size = wanted
            log.info("Model '%s' ready in %.1fs", wanted, time.monotonic() - started)
            self.model_status.emit(f"Model '{wanted}' ready")
            return model

    def preload_model(self) -> None:
        """Warm the model up in the background right after startup."""

        def _load() -> None:
            try:
                self.get_model()
            except Exception as exc:  # noqa: BLE001
                log.error("Background model load failed: %s", exc)
                self.model_status.emit(f"Model load failed: {exc}")

        threading.Thread(target=_load, name="model-preload", daemon=True).start()

    def shutdown(self) -> None:
        """Discard any in-flight recording without transcribing it."""
        if not self._recording:
            return
        self._recording = False
        self._silence_timer.stop()
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:  # noqa: BLE001
                pass
            self._stream = None
        self._frames = []
        log.info("Recording discarded on shutdown")
