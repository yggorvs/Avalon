import argparse
import importlib.util
import json
import logging
from .config import Settings

def doctor(settings):
    modules = {name: importlib.util.find_spec(name) is not None for name in
               ("tkinter", "openai", "dotenv", "faster_whisper", "speech_recognition", "pyaudio", "edge_tts", "pygame", "pyautogui")}
    return {"python_modules": modules, "api_key_configured": bool(settings.api_key),
            "model": settings.model, "device": settings.device,
            "data_dir": str(settings.data_dir),
            "agent": {"enabled":settings.agent_enabled, "terminal":settings.shell_enabled,
                      "desktop":settings.desktop_enabled, "vision":settings.vision_enabled},
            "note": "Diagnóstico estático: não verifica rede, credenciais, modelo remoto, CUDA nem microfone."}

def main():
    parser = argparse.ArgumentParser(description="AVALON • Assistente pessoal")
    parser.add_argument("--agent", action="store_true", help="Ativar ferramentas do computador para tarefas")
    parser.add_argument("--cli", action="store_true", help="Conversar no terminal")
    parser.add_argument("--doctor", action="store_true", help="Diagnóstico sem acessar hardware ou rede")
    args = parser.parse_args()
    settings = Settings.load()
    if args.doctor:
        print(json.dumps(doctor(settings), ensure_ascii=False, indent=2))
        return
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    from .memory import Memory
    from .llm import LanguageModel
    from .audio import Audio
    from .controller import Controller
    memory = Memory(settings.data_dir / "memory.sqlite3")
    audio = Audio(settings)
    from .approvals import Approvals
    from .computer import ComputerTools
    from .agent import Agent
    controller = Controller(memory, LanguageModel(settings), audio, settings.speak)
    approvals = Approvals(controller.emit)
    controller.agent = Agent(controller.llm, ComputerTools(settings, approvals), controller.emit,
                             max_steps=settings.agent_steps)
    controller.agent_enabled = settings.agent_enabled or args.agent
    audio.notify = lambda text: controller.emit("info", text)
    if args.cli:
        from queue import Empty
        print("AVALON: digite uma mensagem; /sair encerra. Digite ajuda para comandos.")
        try:
            while True:
                text = input("Você: ")
                if text == "/sair": break
                if not controller.submit(text): continue
                from .commands import normalize
                if normalize(text.strip()) in {"/parar", "parar tarefa", "cancelar tarefa"}:
                    print("Parada solicitada.")
                    continue
                while True:
                    try: kind, result = controller.events.get(timeout=0.2)
                    except Empty:
                        if not controller.thread.is_alive(): return
                        continue
                    if kind in {"assistant", "error", "info"}: print(f"{kind}: {result}")
                    if kind == "approval":
                        print("\n" + result["title"] + "\n" + result["preview"])
                        answer = input("Autorizar exatamente esta ação? [sim/N]: ")
                        approvals.resolve(result["id"], answer.strip().lower()=="sim")
                    if kind == "quit": return
                    if kind == "status" and result == "Pronto": break
        except (KeyboardInterrupt, EOFError): pass
        finally:
            controller.close()
            controller.thread.join(timeout=60)
    else:
        try:
            from .ui import App
            App(controller).mainloop()
        finally:
            controller.close()

if __name__ == "__main__": main()
