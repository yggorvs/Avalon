from dataclasses import dataclass
from pathlib import Path
import os

@dataclass(frozen=True)
class Settings:
    data_dir: Path
    api_key: str = ""
    base_url: str = "https://integrate.api.nvidia.com/v1"
    model: str = "meta/llama-3.1-70b-instruct"
    device: str = "auto"
    whisper_model: str = "base"
    voice: str = "pt-BR-AntonioNeural"
    speak: bool = False

    @classmethod
    def load(cls):
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        device = os.getenv("AVALON_DEVICE", "auto")
        if device not in {"auto", "cpu", "cuda"}:
            raise ValueError("AVALON_DEVICE deve ser auto, cpu ou cuda.")
        return cls(
            data_dir=Path(os.getenv("AVALON_DATA_DIR", str(Path.home()/".avalon"))).expanduser(),
            api_key=os.getenv("AVALON_API_KEY") or os.getenv("NVIDIA_API_KEY", ""),
            base_url=os.getenv("AVALON_BASE_URL", cls.base_url),
            model=os.getenv("AVALON_MODEL", cls.model), device=device,
            whisper_model=os.getenv("AVALON_WHISPER_MODEL", "base"),
            voice=os.getenv("AVALON_VOICE", cls.voice),
            speak=os.getenv("AVALON_SPEAK", "false").lower() == "true",
        )
