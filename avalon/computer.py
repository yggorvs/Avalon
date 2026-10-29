"""Local capabilities. No network listener, elevation or hidden startup."""
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
import base64
import hashlib
import io
import json
import os
import platform
import re
import signal
import subprocess
import sys
import tempfile
import time
import uuid
import webbrowser

class PolicyError(ValueError):
    pass

@dataclass
class Result:
    data: dict
    image: str | None = None
    denied: bool = False

# Arguments are validated locally as well as advertised to the model.
DEFINITIONS = {
    "system_info": ("Ler sistema, diretório pessoal e horário local.", {}),
    "list_directory": ("Listar até 100 entradas de uma pasta permitida.", {"path":"string"}),
    "find_files": ("Buscar nomes de arquivos, sem ler conteúdo, em até 3000 entradas.", {"path":"string","query":"string"}),
    "read_text": ("Ler arquivo UTF-8 com até 64 KiB. O conteúdo será enviado ao modelo.", {"path":"string"}),
    "write_text": ("Criar/substituir arquivo UTF-8 após aprovação; backup ao substituir.", {"path":"string","content":"string"}),
    "create_directory": ("Criar uma pasta após aprovação.", {"path":"string"}),
    "move_file": ("Mover um arquivo sem sobrescrever, após aprovação.", {"source":"string","destination":"string"}),
    "open_application": ("Abrir um aplicativo conhecido: calculadora, bloco_de_notas, explorador ou terminal.", {"name":"string"}),
    "open_url": ("Abrir URL http/https após aprovação. Não navega nem lê páginas.", {"url":"string"}),
    "run_terminal": ("Executar PowerShell no Windows ou /bin/sh no Linux após aprovação exata; até 30 segundos.", {"command":"string","cwd":"string"}),
    "observe_screen": ("Capturar monitor principal após consentimento; imagem enviada ao modelo de visão.", {}),
    "desktop_click": ("Clicar coordenadas observadas na captura, após aprovação.", {"x":"integer","y":"integer"}),
    "desktop_type": ("Digitar ASCII no aplicativo em foco após aprovação. Não altera área de transferência.", {"text":"string"}),
    "desktop_hotkey": ("Pressionar combinação de teclas após aprovação.", {"keys":"array"}),
}

class ComputerTools:
    def __init__(self, settings, approvals, opener=webbrowser.open):
        self.settings, self.approvals, self.opener = settings, approvals, opener
        self.roots = tuple(p.expanduser().resolve() for p in (settings.file_roots or (Path.home(),)))
        self.screen_at = 0.0

    def environment(self):
        return "Sistema: " + platform.system() + ". Raízes de arquivos: " + json.dumps([str(p) for p in self.roots])

    def schemas(self):
        names = set(DEFINITIONS)
        if not self.settings.shell_enabled: names.discard("run_terminal")
        if not self.settings.vision_enabled: names.discard("observe_screen")
        if not (self.settings.desktop_enabled and self.settings.vision_enabled):
            names -= {"desktop_click", "desktop_type", "desktop_hotkey"}
        return [{"type":"function", "function":{"name":name,"description":DEFINITIONS[name][0],
            "parameters":{"type":"object", "properties":{
                key: ({"type":kind,"items":{"type":"string"}} if kind=="array" else {"type":kind})
                for key,kind in DEFINITIONS[name][1].items()},
                "required":list(DEFINITIONS[name][1]), "additionalProperties":False}}}
            for name in sorted(names)]

    def _validate(self, name, args):
        if name not in {s["function"]["name"] for s in self.schemas()}: raise ValueError("Ferramenta indisponível.")
        fields = DEFINITIONS[name][1]
        if set(args) != set(fields): raise ValueError("Argumentos inválidos.")
        for key, kind in fields.items():
            value = args[key]
            if kind=="string" and (not isinstance(value,str) or len(value)>64000 or "\x00" in value): raise ValueError("Texto inválido.")
            if kind=="integer" and (type(value) is not int or not 0<=value<=20000): raise ValueError("Coordenada inválida.")
            if kind=="array" and (not isinstance(value,list) or not 1<=len(value)<=4 or not all(isinstance(v,str) and len(v)<20 for v in value)): raise ValueError("Teclas inválidas.")

    def _path(self, value):
        path = Path(value).expanduser()
        if not path.is_absolute(): path = self.roots[0]/path
        path = path.resolve()
        if not any(path.is_relative_to(root) for root in self.roots): raise PolicyError("Caminho fora das raízes permitidas.")
        lowered = {part.lower() for part in path.parts}
        sensitive = {".ssh", ".aws", ".azure", ".gnupg", "credentials", "login data", "cookies", "local state", "key4.db", "logins.json"}
        if lowered & sensitive or path.name.lower().startswith('.env') or path.suffix.lower() in {'.pem','.key','.pfx','.p12'}:
            raise PolicyError("Arquivo sensível não disponível pelas ferramentas de arquivos.")
        return path

    def _audit(self, name, args, status):
        directory = self.settings.data_dir
        directory.mkdir(parents=True, exist_ok=True)
        # Metadata only, not command output, file contents, screenshot or API keys.
        entry = {"time":time.time(),"tool":name,"status":status,
                 "argument_sha256":hashlib.sha256(json.dumps(args,sort_keys=True).encode()).hexdigest()}
        path = directory/'actions.jsonl'
        if path.exists() and path.stat().st_size>2_000_000:
            path.replace(directory/'actions.previous.jsonl')
        with path.open('a',encoding='utf-8') as f: f.write(json.dumps(entry)+'\n')

    def execute(self, name, args, cancel):
        self._validate(name,args)
        if cancel.is_set(): return Result({"error":"cancelado"},denied=True)
        # Refuse to act if the local audit cannot be written.
        self._audit(name,args,"started")
        try:
            result = self._execute(name,args,cancel)
        except PolicyError:
            self._audit(name,args,"blocked")
            return Result({"error":"Bloqueado pela política local de arquivos. Não tente outra ferramenta para contornar."},denied=True)
        except (OSError, ValueError) as error:
            self._audit(name,args,"failed")
            return Result({"error":type(error).__name__,"message":"Verifique caminho, formato e permissões. A operação não foi confirmada."})
        self._audit(name,args,"denied" if result.denied else "completed")
        return result

    def _approve(self, name, args, cancel):
        preview = json.dumps(args,ensure_ascii=False,indent=2)
        if len(preview)>20000: raise ValueError("Ação longa demais para revisar; divida em arquivos menores.")
        return self.approvals.ask("Autorizar: " + name, preview, cancel)

    def _execute(self, name, a, cancel):
        if name=="system_info":
            return Result({"system":platform.system(),"release":platform.release(),"home":str(Path.home()),
                           "time":time.strftime('%Y-%m-%d %H:%M:%S'),"roots":[str(p) for p in self.roots]})
        if name=="list_directory":
            path=self._path(a['path']); entries=[]
            for child in path.iterdir():
                try: safe=self._path(str(child))
                except (ValueError,OSError): continue
                entries.append({"name":child.name,"directory":safe.is_dir()})
                if len(entries)>=100: break
            return Result({"entries":entries,"limit":100})
        if name=="find_files":
            path=self._path(a['path']); found=[]; scanned=0
            for directory, dirs, files in os.walk(path,followlinks=False):
                scanned += 1
                if scanned>=3000: return Result({"files":found,"truncated":True})
                if cancel.is_set(): return Result({"error":"cancelado"},denied=True)
                allowed=[]
                for d in dirs:
                    try:
                        child=self._path(str(Path(directory)/d))
                        if d not in {'.git','node_modules','.venv','venv'} and not child.is_symlink(): allowed.append(d)
                    except (ValueError,OSError): pass
                dirs[:]=allowed
                for filename in files:
                    scanned+=1
                    if a['query'].casefold() in filename.casefold():
                        try: candidate=self._path(str(Path(directory)/filename))
                        except (ValueError,OSError): continue
                        found.append(str(candidate))
                    if scanned>=3000 or len(found)>=100:
                        return Result({"files":found,"truncated":True})
            return Result({"files":found,"truncated":False})
        if name=="read_text":
            path=self._path(a['path'])
            with path.open('rb') as f: raw=f.read(65537)
            if len(raw)>65536: raise ValueError("Arquivo grande demais.")
            return Result({"path":str(path),"text":raw.decode('utf-8')[:16000],"truncated":len(raw.decode('utf-8'))>16000})
        if name in {"write_text","create_directory","move_file"}:
            return self._mutate(name,a,cancel)
        if name=="open_application":
            apps={"calculadora":"calc.exe","bloco_de_notas":"notepad.exe","explorador":"explorer.exe","terminal":"cmd.exe"}
            if sys.platform!='win32': return Result({"error":"Aplicativos pré-definidos somente no Windows."})
            if a['name'] not in apps: raise ValueError("Aplicativo não permitido.")
            subprocess.Popen([apps[a['name']]],shell=False)
            return Result({"launched":a['name'],"note":"Solicitação de abertura; conteúdo da janela não verificado."})
        if name=="open_url":
            parsed=urlparse(a['url'])
            if parsed.scheme not in {'https','http'} or not parsed.hostname or parsed.username or parsed.password: raise ValueError("URL inválida.")
            if not self._approve(name,a,cancel): return Result({"error":"recusado"},denied=True)
            return Result({"opened":bool(self.opener(a['url']))})
        if name=="run_terminal":
            cwd=self._path(a['cwd'])
            if not cwd.is_dir() or len(a['command'])>6000: raise ValueError("Comando ou pasta inválida.")
            preview={"command":a['command'],"cwd":str(cwd),"warning":"Comando arbitrário com suas permissões; pode alterar arquivos e acessar rede. Não é sandbox."}
            if not self._approve(name,preview,cancel): return Result({"error":"recusado"},denied=True)
            if cancel.is_set(): return Result({"error":"cancelado"},denied=True)
            return self._terminal(a['command'],cwd,cancel)
        if name=="observe_screen":
            if not self._approve(name,{"disclosure":"Captura do monitor principal será enviada ao endpoint de IA configurado. Feche dados privados antes de aprovar."},cancel):
                return Result({"error":"recusado"},denied=True)
            if cancel.wait(.3): return Result({"error":"cancelado"},denied=True)
            desktop=self._desktop(); image=desktop.screenshot()
            width,height=image.size
            # Keep coordinates in the original screenshot space; no hidden scaling.
            if width*height>10_000_000: raise ValueError("Monitor grande demais para envio sem redução configurada.")
            output=io.BytesIO(); image.convert('RGB').save(output,format='JPEG',quality=75)
            self.screen_at=time.monotonic()
            return Result({"width":width,"height":height,"coordinate_space":"original pixels"},
                          image='data:image/jpeg;base64,'+base64.b64encode(output.getvalue()).decode())
        if name.startswith('desktop_'):
            if time.monotonic()-self.screen_at>45: raise ValueError("Capture a tela novamente antes de interagir.")
            if name=='desktop_type' and (not a['text'].isascii() or len(a['text'])>2000 or any(ord(c)<32 for c in a['text'])):
                raise ValueError("Digitação aceita apenas ASCII sem caracteres de controle; use write_text para Unicode.")
            desktop=self._desktop()
            if name=='desktop_click' and not desktop.onScreen(a['x'],a['y']): raise ValueError("Fora da tela.")
            if name=='desktop_hotkey' and not all(key in desktop.KEYBOARD_KEYS for key in a['keys']): raise ValueError("Tecla inválida.")
            if not self._approve(name,a,cancel): return Result({"error":"recusado"},denied=True)
            if cancel.is_set(): return Result({"error":"cancelado"},denied=True)
            # Allow time to refocus the target app after the approval UI closes.
            if cancel.wait(2): return Result({"error":"cancelado"},denied=True)
            if name=='desktop_click': desktop.click(a['x'],a['y'])
            elif name=='desktop_type': desktop.write(a['text'],interval=.01)
            else: desktop.hotkey(*a['keys'])
            self.screen_at=0
            return Result({"input_sent":True,"note":"Capture novamente para verificar o efeito."})
        raise ValueError("Ferramenta não implementada.")

    def _mutate(self,name,a,cancel):
        source=self._path(a['source'] if name=='move_file' else a['path'])
        destination=self._path(a['destination']) if name=='move_file' else source
        if source.is_file() and source.stat().st_size>1_000_000: raise ValueError("Arquivo grande demais.")
        original=source.read_bytes() if source.is_file() else None
        if original is not None and len(original)>1_000_000: raise ValueError("Arquivo grande demais para backup/revisão.")
        if name=='move_file' and (original is None or destination.exists()): raise ValueError("Origem ou destino inválido.")
        preview={**a,"resolved_source":str(source),"resolved_destination":str(destination)}
        if name=='write_text' and original is not None:
            preview['previous_text']=original.decode('utf-8')[:10000]
            preview['previous_sha256']=hashlib.sha256(original).hexdigest()
        if not self._approve(name,preview,cancel): return Result({"error":"recusado"},denied=True)
        if cancel.is_set(): return Result({"error":"cancelado"},denied=True)
        # Re-resolve paths and verify bytes after user review to detect intervening changes.
        if self._path(str(source))!=source or self._path(str(destination))!=destination: raise ValueError("Caminho alterado.")
        if source.is_file() and source.stat().st_size>1_000_000: raise ValueError("Arquivo alterado após revisão.")
        current=source.read_bytes() if source.is_file() else None
        if current!=original: raise ValueError("Arquivo mudou após a prévia.")
        if name=='create_directory':
            source.mkdir(parents=False,exist_ok=False)
            return Result({"created":str(source)})
        if name=='move_file':
            # Hard link creation is exclusive: never overwrite a newly created destination.
            os.link(source,destination)
            source.unlink()
            return Result({"moved":str(source),"destination":str(destination)})
        backup=None
        if original is not None:
            backup=self.settings.data_dir/'backups'/(uuid.uuid4().hex+'-'+source.name)
            backup.parent.mkdir(parents=True,exist_ok=True); backup.write_bytes(original)
        if original is None:
            with source.open('x',encoding='utf-8') as f: f.write(a['content'])
        else:
            temporary=None
            try:
                with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=source.parent,delete=False) as f:
                    temporary=Path(f.name); f.write(a['content'])
                os.replace(temporary,source)
            finally:
                if temporary and temporary.exists(): temporary.unlink()
        return Result({"written":str(source),"backup":str(backup) if backup else None})

    def _desktop(self):
        import pyautogui
        pyautogui.FAILSAFE=True
        pyautogui.PAUSE=.2
        return pyautogui

    def _terminal(self,command,cwd,cancel):
        args=['powershell.exe','-NoProfile','-NonInteractive','-Command',command] if sys.platform=='win32' else ['/bin/sh','-c',command]
        environment={k:v for k,v in os.environ.items() if not re.search(r'KEY|TOKEN|SECRET|PASSWORD',k,re.I)}
        kwargs={'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP} if sys.platform=='win32' else {'start_new_session':True}
        with tempfile.TemporaryFile() as output:
            process=subprocess.Popen(args,cwd=cwd,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,env=environment,**kwargs)
            deadline=time.monotonic()+30; interrupted=False
            while process.poll() is None:
                if cancel.wait(.05) or time.monotonic()>deadline or os.fstat(output.fileno()).st_size>1_000_000:
                    interrupted=True
                    if sys.platform=='win32':
                        try:
                            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
                        except (OSError, subprocess.TimeoutExpired):
                            pass
                    else:
                        try: os.killpg(process.pid,signal.SIGKILL)
                        except ProcessLookupError: pass
                    if process.poll() is None: process.kill()
                    break
            process.wait(timeout=5)
            output.seek(0); data=output.read(12000)
        return Result({"exit_code":process.returncode,"output":data.decode('utf-8',errors='replace'),
                       "interrupted":interrupted,"note":"Saída limitada a 12000 bytes; processos destacados podem sobreviver."})
