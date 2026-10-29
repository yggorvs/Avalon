import argparse
import importlib.util
import json
import logging
from .config import Settings

def doctor(settings):
    modules = {name: importlib.util.find_spec(name) is not None for name in
               ("tkinter", "openai", "dotenv", "faster_whisper", "speech_recognition", "pyaudio", "edge_tts", "pygame")}
    return {"python_modules": modules, "api_key_configured": bool(settings.api_key),
            "model": settings.model, "device": settings.device,
            "data_dir": str(settings.data_dir),
            "note": "Diagnóstico estático: não verifica rede, credenciais, modelo remoto, CUDA nem microfone."}

def main():
    parser = argparse.ArgumentParser(description="AVALON • Assistente pessoal")
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
    controller = Controller(memory, LanguageModel(settings), audio, settings.speak)
    audio.notify = lambda text: controller.emit("info", text)
    if args.cli:
        from queue import Empty
        print("AVALON: digite uma mensagem; /sair encerra. Digite ajuda para comandos.")
        try:
            while True:
                text = input("Você: ")
                if text == "/sair": break
                if not controller.submit(text): continue
                while True:
                    try: kind, result = controller.events.get(timeout=0.2)
                    except Empty:
                        if not controller.thread.is_alive(): return
                        continue
                    if kind in {"assistant", "error", "info"}: print(f"{kind}: {result}")
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
