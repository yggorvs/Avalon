"""Sprite atlas decoding, independent of Tk and hardware."""
from pathlib import Path
import json
from PIL import Image

ASSETS = Path(__file__).parent / "assets"

class SpriteAtlas:
    def __init__(self, metadata=ASSETS / "orb-atlas.json"):
        self.metadata = json.loads(Path(metadata).read_text(encoding="utf-8"))
        with Image.open(Path(metadata).parent / self.metadata["image"]) as image:
            self.image = image.convert("RGBA")
        self.columns, self.rows = self.metadata["columns"], self.metadata["rows"]
        if self.columns < 1 or self.rows < 1: raise ValueError("Grade de sprites inválida.")
        self.states = self.metadata["states"]
        self.cache = {}

    def frame(self, state, index, size):
        if state not in self.states: state = "idle"
        if not 80 <= size <= 256: raise ValueError("Tamanho deve ficar entre 80 e 256 pixels.")
        index %= self.columns
        key = state, index, size
        if key not in self.cache:
            row = self.states[state]["row"]
            w,h = self.image.size
            box = (round(index*w/self.columns),round(row*h/self.rows),
                   round((index+1)*w/self.columns),round((row+1)*h/self.rows))
            frame = self.image.crop(box).resize((size,size),Image.Resampling.NEAREST)
            # Tk/Windows color-key transparency has no per-window alpha edges.
            # Snap the render mask to hard pixel edges, leaving the source RGBA untouched.
            frame.putalpha(frame.getchannel("A").point(lambda a: 255 if a >= 128 else 0))
            if len(self.cache) >= 80: self.cache.clear()
            self.cache[key] = frame
        return self.cache[key]

    def index(self, state, elapsed_ms, animate=True):
        if not animate: return 0
        return int(elapsed_ms / self.states.get(state,self.states["idle"])["frame_ms"]) % self.columns
