"""Small, testable model for floating-window state and persistence."""
from dataclasses import dataclass
from pathlib import Path
import json
import os
import tempfile
import time

@dataclass
class Preferences:
    x: int = -1
    y: int = -1
    size: int = 144
    animate: bool = True

    @classmethod
    def load(cls, path):
        try:
            value = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(value,dict): return cls()
            return cls(x=value["x"] if type(value.get("x")) is int else -1,
                       y=value["y"] if type(value.get("y")) is int else -1,
                       size=value["size"] if type(value.get("size")) is int and 80<=value["size"]<=256 else 144,
                       animate=value["animate"] if type(value.get("animate")) is bool else True)
        except (OSError,ValueError): return cls()

    def save(self,path):
        path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
        temporary=None
        try:
            with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=path.parent,delete=False) as f:
                temporary=Path(f.name)
                json.dump(vars(self),f)
            os.replace(temporary,path)
        finally:
            if temporary and temporary.exists(): temporary.unlink()

    def fit(self,width,height):
        self.x = max(0,min(self.x if self.x>=0 else width-self.size-28,max(0,width-self.size)))
        self.y = max(0,min(self.y if self.y>=0 else height-self.size-90,max(0,height-self.size)))
        return self.x,self.y

class VisualState:
    def __init__(self):
        self.activity='idle'
        self.alert_until=0.0
        self.approval_id=None
        self.status='Pronto'

    def observe(self,kind,text,now=None):
        now=time.monotonic() if now is None else now
        if kind=='approval': self.approval_id=text['id']
        elif kind=='approval_done' and self.approval_id==text: self.approval_id=None
        elif kind=='error': self.alert_until=now+6
        elif kind=='status':
            self.status=text
            lowered=text.casefold()
            self.activity=('speaking' if 'falando' in lowered else 'working' if
                any(term in lowered for term in ('processando','agente:','encerrando')) else
                'listening' if 'escutando' in lowered else 'idle')
        elif kind=='info' and text=='Microfone aberto.': self.activity='listening'

    def current(self,now=None):
        now=time.monotonic() if now is None else now
        return 'alert' if self.approval_id or now<self.alert_until else self.activity
