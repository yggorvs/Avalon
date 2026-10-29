from dataclasses import dataclass
from datetime import datetime
import re
import unicodedata
import subprocess
import sys
import webbrowser
from urllib.parse import urlencode

HELP = """Comandos locais:
• abrir google / youtube / github
• pesquisar no google sobre <assunto>
• pesquisar no youtube sobre <assunto>
• tocar <música ou artista> (abre os resultados; não inicia reprodução)
• abrir calculadora / bloco de notas / terminal (Windows)
• que horas são / que dia é hoje
• limpar memória (exige confirmação)
• salvar nota <texto> / listar notas
• adicionar tarefa <texto> / listar tarefas / concluir tarefa <número>
• ajuda
Use o botão Ouvir para um comando, ou Ativar voz para escuta contínua com 'Avalon'."""

def normalize(text):
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")

@dataclass(frozen=True)
class Command:
    name: str
    argument: str = ""

class Router:
    def parse(self, text):
        # Match entire utterances. Questions and negations are not imperative commands.
        raw = text.strip().rstrip(".!?")
        n = normalize(raw)
        if n in {"ajuda", "comandos", "o que voce pode fazer"}:
            return Command("help")
        if n in {"que horas sao", "hora atual"}:
            return Command("time")
        if n in {"que dia e hoje", "data de hoje"}:
            return Command("date")
        if n in {"limpar memoria", "apagar memoria", "esqueca o que conversamos"}:
            return Command("clear")
        if n in {"dormir", "tchau", "ate logo", "encerrar conversa"}:
            return Command("sleep")
        if n == "desligar o sistema":
            return Command("quit")
        if n == "listar notas": return Command("notes")
        if n == "listar tarefas": return Command("tasks")
        for prefix, name in (("salvar nota ", "note"), ("adicionar tarefa ", "task")):
            if n.startswith(prefix) and raw[len(prefix):].strip():
                return Command(name, raw[len(prefix):].strip())
        match = re.fullmatch(r"concluir tarefa ([1-9][0-9]{0,8})", n)
        if match: return Command("complete_task", match[1])
        match = re.fullmatch(r"(?:abra|abrir) (google|youtube|github|calculadora|bloco de notas|terminal)", n)
        if match:
            return Command("open", match[1])
        match = re.fullmatch(r"(?:pesquise|pesquisar|busque|buscar) no (google|youtube) (?:sobre|por) (.+)", raw, re.I)
        if match:
            return Command(match[1].lower(), match[2])
        match = re.fullmatch(r"(?:tocar|toque|ouvir musica de|coloque a musica) (.+)", raw, re.I)
        if match:
            return Command("music", match[1])
        return None

class Executor:
    def __init__(self, opener=webbrowser.open, launcher=subprocess.Popen):
        self.opener, self.launcher = opener, launcher

    def execute(self, command):
        name, arg = command.name, command.argument
        if name == "help": return HELP
        if name == "time": return datetime.now().strftime("Agora são %H:%M.")
        if name == "date": return datetime.now().strftime("Hoje é %d/%m/%Y.")
        if name == "open":
            sites = {"google": "https://www.google.com", "youtube": "https://www.youtube.com", "github": "https://github.com"}
            if arg in sites:
                if not self.opener(sites[arg]): raise RuntimeError("Não foi possível abrir o navegador.")
                return f"Solicitei a abertura de {arg} no navegador."
            if sys.platform != "win32": return "Este aplicativo local só está configurado no Windows."
            apps = {"calculadora": "calc.exe", "bloco de notas": "notepad.exe", "terminal": "cmd.exe"}
            self.launcher([apps[arg]], shell=False)
            return f"Solicitei a abertura de {arg}."
        targets = {"google": ("https://www.google.com/search", "q"),
                   "youtube": ("https://www.youtube.com/results", "search_query"),
                   "music": ("https://music.youtube.com/search", "q")}
        url, parameter = targets[name]
        if not self.opener(url + "?" + urlencode({parameter: arg})):
            raise RuntimeError("Não foi possível abrir o navegador.")
        return f"Abri os resultados para: {arg}."
