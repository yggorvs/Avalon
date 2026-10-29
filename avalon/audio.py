import asyncio
from pathlib import Path
import tempfile
import threading

class Audio:
    """Used exclusively by the controller worker; no hardware work on import."""
    def __init__(self, settings, notify=lambda text: None):
        self.settings, self.notify = settings, notify
        self.model = None
        self.mixer = None
        self.lock = threading.Lock()
        self.speech_stop = threading.Event()

    def _load_model(self):
        if self.model is not None: return
        from faster_whisper import WhisperModel
        device = self.settings.device
        try:
            self.model = WhisperModel(self.settings.whisper_model,
                device="cuda" if device in {"auto", "cuda"} else "cpu",
                compute_type="float16" if device in {"auto", "cuda"} else "int8")
        except Exception:
            if device != "auto": raise
            self.notify("GPU indisponível; carregando transcrição na CPU.")
            self.model = WhisperModel(self.settings.whisper_model, device="cpu", compute_type="int8")

    def listen(self, stop):
        import speech_recognition as sr
        with self.lock:
            self._load_model()
            if stop.is_set(): return ""
            recognizer = sr.Recognizer()
            recognizer.operation_timeout = 5
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.4)
                self.notify("Microfone aberto.")
                try:
                    audio = recognizer.listen(source, timeout=2, phrase_time_limit=12)
                except sr.WaitTimeoutError:
                    return ""
            if stop.is_set(): return ""
            # TemporaryDirectory is unique and cleaned even if transcription fails.
            with tempfile.TemporaryDirectory(prefix="avalon-") as directory:
                path = Path(directory)/"capture.wav"
                path.write_bytes(audio.get_wav_data())
                segments, _ = self.model.transcribe(str(path), language="pt", vad_filter=True, beam_size=3)
                return " ".join(s.text.strip() for s in segments).strip()

    def speak(self, text, stop):
        import edge_tts
        import pygame
        self.speech_stop.clear()
        with tempfile.TemporaryDirectory(prefix="avalon-tts-") as directory:
            path = str(Path(directory)/"speech.mp3")
            async def generate():
                await asyncio.wait_for(edge_tts.Communicate(text, self.settings.voice).save(path), timeout=20)
            asyncio.run(generate())
            if stop.is_set() or self.speech_stop.is_set(): return
            if self.mixer is None:
                pygame.mixer.init()
                self.mixer = pygame.mixer
            try:
                self.mixer.music.load(path)
                self.mixer.music.play()
                while self.mixer.music.get_busy():
                    if stop.wait(0.05) or self.speech_stop.is_set(): break
            finally:
                self.mixer.music.stop()
                self.mixer.music.unload()

    def interrupt(self):
        self.speech_stop.set()

    def close(self):
        if self.mixer is not None: self.mixer.quit()
