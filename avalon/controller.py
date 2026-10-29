from queue import Queue, Empty, Full
import logging
import re
import threading
import time
from .commands import Router, Executor, normalize
from .errors import ConfigurationError

log = logging.getLogger(__name__)

class Controller:
    """One worker owns microphone, inference, TTS and action execution."""
    def __init__(self, memory, llm, audio, speak=False, executor=None, agent=None, agent_enabled=False):
        self.memory, self.llm, self.audio = memory, llm, audio
        self.speak_enabled = speak
        self.agent = agent
        self.agent_enabled = agent_enabled
        self.task_cancel = threading.Event()
        self.router, self.executor = Router(), executor or Executor()
        self.events = Queue()
        self.tasks = Queue(maxsize=8)
        self.stop = threading.Event()
        self.wake = threading.Event()
        self.pending_clear = 0.0
        self.thread = threading.Thread(target=self._run, name="avalon-worker", daemon=True)
        self.thread.start()

    def emit(self, kind, text): self.events.put((kind, text))

    def submit(self, text):
        text = text.strip()
        if normalize(text) in {"/parar", "parar tarefa", "cancelar tarefa"}:
            self.stop_task()
            return True
        if not text: return False
        if len(text) > 8000:
            self.emit("error", "Mensagem muito longa (máximo: 8000 caracteres).")
            return False
        return self._enqueue(("text", text))

    def listen_once(self): return self._enqueue(("listen", ""))

    def _enqueue(self, item):
        if self.stop.is_set(): return False
        try: self.tasks.put_nowait(item)
        except Full:
            self.emit("error", "Fila cheia. Aguarde as tarefas atuais.")
            return False
        return True

    def set_wake(self, active):
        self.wake.set() if active else self.wake.clear()
        self.emit("status", "Voz contínua ativada" if active else "Voz contínua desativada")

    def _handle(self, text):
        self.emit("user", text)
        self.emit("status", "Processando")
        n = normalize(text.strip().rstrip(".!?"))
        if self.pending_clear:
            valid = time.monotonic() < self.pending_clear
            self.pending_clear = 0
            if n == "confirmar" and valid:
                self.memory.clear()
                self.emit("clear", "")
                return "Histórico local apagado."
            if n in {"confirmar", "cancelar"}: return "Limpeza cancelada ou expirada."
        command = self.router.parse(text)
        if command:
            if command.name == "note":
                ident = self.memory.add_note(command.argument)
                return f"Nota {ident} salva localmente."
            if command.name == "task":
                ident = self.memory.add_task(command.argument)
                return f"Tarefa {ident} adicionada."
            if command.name in {"notes", "tasks"}:
                rows = self.memory.notes() if command.name == "notes" else self.memory.tasks()
                return "\n".join(f"{ident}. {text}" for ident, text in rows) if rows else "Nenhum registro encontrado."
            if command.name == "complete_task":
                done = self.memory.complete_task(int(command.argument))
                return "Tarefa concluída." if done else "Tarefa não encontrada ou já concluída."
            if command.name == "clear":
                self.pending_clear = time.monotonic() + 30
                return "Apagar o histórico local? Digite ou diga 'confirmar' em até 30 segundos, ou 'cancelar'."
            if command.name == "sleep":
                self.set_wake(False)
                return "Escuta contínua desativada."
            if command.name == "quit":
                self.emit("quit", "")
                return "Encerrando o Avalon."
            return self.executor.execute(command)
        if self.agent_enabled and self.agent is not None:
            reply = self.agent.run(text, self.memory.context(), self.task_cancel)
        else:
            reply = self.llm.reply(self.memory.context(), text)
        if self.stop.is_set() or self.task_cancel.is_set(): return None
        self.memory.append(text, reply)
        return reply

    def _run(self):
        active_conversation = False
        try:
            while not self.stop.is_set():
                try: kind, text = self.tasks.get(timeout=0.15)
                except Empty:
                    if not self.wake.is_set():
                        active_conversation = False
                        continue
                    kind, text = "wake", ""
                self.task_cancel.clear()
                try:
                    if kind != "text":
                        self.emit("status", "Escutando" if kind == "listen" or active_conversation else "Aguardando Avalon")
                        text = self.audio.listen(self.stop)
                        if self.stop.is_set(): break
                        if self.task_cancel.is_set(): continue
                        if not text: continue
                        if kind == "wake" and not self.wake.is_set(): continue
                        if kind == "wake" and not active_conversation:
                            # Normalize preserves string length for Portuguese accent removal.
                            match = re.match(r"^avalon\b[ ,.:;!?-]*", normalize(text))
                            if not match: continue
                            active_conversation = True
                            text = text[match.end():].strip()
                            if not text:
                                self.emit("assistant", "Estou ouvindo. Diga seu comando.")
                                continue
                    reply = self._handle(text)
                    if reply and not self.stop.is_set() and not self.task_cancel.is_set():
                        self.emit("assistant", reply)
                        if self.speak_enabled:
                            self.emit("status", "Falando")
                            try: self.audio.speak(reply, self.stop)
                            except Exception:
                                self.emit("error", "Falha na voz. A resposta permanece disponível no texto.")
                except Exception as error:
                    # Do not log provider payloads or credentials.
                    log.warning("Operation failed: %s", type(error).__name__)
                    self.emit("error", str(error) if isinstance(error, ConfigurationError) else
                              "Não foi possível concluir. Verifique configuração, rede, modelo e dispositivos.")
                    if kind == "wake":
                        self.set_wake(False)
                        active_conversation = False
                finally:
                    self.emit("status", "Pronto")
        finally:
            for resource in (self.audio, self.llm, self.memory):
                try: resource.close()
                except Exception: pass
            self.emit("closed", "")

    def stop_task(self):
        self.task_cancel.set()
        self.wake.clear()
        self.audio.interrupt()
        if self.agent is not None: self.agent.tools.approvals.cancel()
        while True:
            try: self.tasks.get_nowait()
            except Empty: break
        self.emit("info", "Parada solicitada. Ações concluídas não são desfeitas; a requisição de IA atual pode levar até o timeout para retornar.")

    def close(self):
        self.stop.set()
        self.stop_task()
        self.wake.clear()
        self.audio.interrupt()
