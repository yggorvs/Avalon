"""Human approval is an out-of-band UI/CLI action, never a model tool."""
from dataclasses import dataclass, field
import secrets
import threading
import time

@dataclass
class Request:
    id: str
    title: str
    preview: str
    expires: float
    ready: threading.Event = field(default_factory=threading.Event)
    allowed: bool = False

class Approvals:
    def __init__(self, emit, timeout=120):
        self.emit, self.timeout = emit, timeout
        self.lock = threading.Lock()
        self.pending = None

    def ask(self, title, preview, cancel):
        request = Request(secrets.token_hex(16), title, preview, time.monotonic()+self.timeout)
        with self.lock:
            if self.pending is not None: raise RuntimeError("Já existe aprovação pendente.")
            self.pending = request
        self.emit("approval", {"id": request.id, "title": title, "preview": preview})
        try:
            while not request.ready.wait(.05):
                if cancel.is_set() or time.monotonic() >= request.expires: return False
            return request.allowed and not cancel.is_set() and time.monotonic() < request.expires
        finally:
            with self.lock: self.pending = None
            self.emit("approval_done", request.id)

    def resolve(self, request_id, allowed):
        with self.lock:
            request = self.pending
            if not request or request.id != request_id or time.monotonic() >= request.expires: return False
            # First answer wins; stale buttons cannot authorize a later request.
            if request.ready.is_set(): return False
            request.allowed = bool(allowed)
            request.ready.set()
            return True

    def cancel(self):
        with self.lock:
            if self.pending:
                self.pending.allowed = False
                self.pending.ready.set()
