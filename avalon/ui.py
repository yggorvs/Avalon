import math
from queue import Empty
import tkinter as tk
from tkinter import ttk

BG = "#080d17"
PANEL = "#111b2b"
GOLD = "#dfb958"
GREEN = "#62e9a5"

class App(tk.Tk):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.closing = False
        self.angle = 0
        self.title("AVALON • Assistente pessoal")
        self.geometry("1180x850")
        self.minsize(900, 800)
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TButton", padding=10, background=PANEL, foreground="white")
        style.map("TButton", background=[("active", "#29435c")])
        sidebar = tk.Frame(self, bg=PANEL, width=270, padx=22, pady=25)
        sidebar.grid(row=0, column=0, sticky="nsew")
        tk.Label(sidebar, text="A V A L O N", bg=PANEL, fg=GOLD, font=("Segoe UI", 23, "bold")).pack(anchor="w")
        tk.Label(sidebar, text="ASSISTENTE PESSOAL / V2", bg=PANEL, fg="#91a6be", font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 15))
        self.orb = tk.Canvas(sidebar, width=220, height=210, bg=PANEL, highlightthickness=0)
        self.orb.pack()
        self.status = tk.StringVar(value="Pronto • serviços carregados sob demanda")
        tk.Label(sidebar, textvariable=self.status, wraplength=220, bg=PANEL, fg=GREEN, font=("Segoe UI", 11)).pack(pady=10)
        ttk.Button(sidebar, text="Ouvir um comando", command=controller.listen_once).pack(fill="x", pady=5)
        self.wake = tk.BooleanVar(value=False)
        self.wake_button = tk.Checkbutton(sidebar, text="Ativar voz contínua", variable=self.wake,
            command=lambda: controller.set_wake(self.wake.get()), bg=PANEL, fg="white", selectcolor=BG, activebackground=PANEL, activeforeground="white")
        self.wake_button.pack(anchor="w", pady=8)
        self.speak = tk.BooleanVar(value=controller.speak_enabled)
        tk.Checkbutton(sidebar, text="Ler respostas em voz alta", variable=self.speak,
            command=lambda: setattr(controller, "speak_enabled", self.speak.get()), bg=PANEL, fg="white", selectcolor=BG, activebackground=PANEL, activeforeground="white").pack(anchor="w")
        self.agent_mode = tk.BooleanVar(value=controller.agent_enabled)
        tk.Checkbutton(sidebar, text="Modo agente: usar computador", variable=self.agent_mode,
            command=self.toggle_agent, bg=PANEL, fg=GOLD, selectcolor=BG,
            activebackground=PANEL, activeforeground=GOLD).pack(anchor="w", pady=8)
        ttk.Button(sidebar, text="PARAR TAREFA", command=controller.stop_task).pack(fill="x", pady=5)
        self.bind("<Escape>", lambda event: controller.stop_task())
        self.approval_window = None
        self.approval_id = None
        ttk.Button(sidebar, text="Interromper fala", command=controller.audio.interrupt).pack(fill="x", pady=10)
        ttk.Button(sidebar, text="Comandos disponíveis", command=lambda: controller.submit("ajuda")).pack(fill="x", pady=5)
        tk.Label(sidebar, text="Voz contínua usa o microfone.\nWhisper local • IA no endpoint configurado\nEdge TTS usa internet.\n\nHistórico local em SQLite.\nDigite ‘limpar memória’ para apagar.", justify="left", wraplength=220, bg=PANEL, fg="#91a6be", font=("Segoe UI", 9)).pack(side="bottom", anchor="w", pady=20)
        body = tk.Frame(self, bg=BG, padx=25, pady=25)
        body.grid(row=0, column=1, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)
        tk.Label(body, text="Sua central de conversa", bg=BG, fg="white", font=("Segoe UI", 22, "bold")).grid(row=0, column=0, sticky="w", pady=(0,20))
        chat_frame = tk.Frame(body, bg=BG)
        chat_frame.grid(row=1, column=0, sticky="nsew")
        chat_frame.rowconfigure(0, weight=1)
        chat_frame.columnconfigure(0, weight=1)
        self.chat = tk.Text(chat_frame, bg=PANEL, fg="#dce6f3", font=("Segoe UI", 12), wrap="word", padx=18, pady=18, relief="flat", state="disabled", takefocus=True)
        self.chat.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(chat_frame, command=self.chat.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.chat.configure(yscrollcommand=scrollbar.set)
        self.chat.tag_configure("user", foreground=GOLD)
        self.chat.tag_configure("error", foreground="#ffadad")
        self.chat.tag_configure("assistant", foreground=GREEN)
        self.entry = tk.Entry(body, bg=PANEL, fg="white", insertbackground="white", font=("Segoe UI", 13), relief="flat")
        self.entry.grid(row=2, column=0, sticky="ew", pady=(18,10), ipady=12)
        self.entry.bind("<Return>", self.send)
        self.entry.focus_set()
        ttk.Button(body, text="Enviar mensagem  ↵", command=self.send).grid(row=3, column=0, sticky="e")
        self.write("assistant", "Olá! Sou o Avalon. Você pode conversar por texto ou clicar em Ouvir. Digite ‘ajuda’ para conhecer os comandos locais. A IA precisa de configuração no .env.")
        self.after(50, self.poll)
        self.animate()

    def write(self, kind, text):
        self.chat.configure(state="normal")
        label = {"user": "VOCÊ", "assistant": "AVALON", "error": "AVISO", "info": "SISTEMA"}.get(kind, "SISTEMA")
        self.chat.insert("end", f"{label}\n", kind)
        self.chat.insert("end", text + "\n\n")
        if int(self.chat.index("end-1c").split(".")[0]) > 1500:
            self.chat.delete("1.0", "300.0")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def send(self, event=None):
        if self.controller.submit(self.entry.get()): self.entry.delete(0, "end")
        return "break"

    def poll(self):
        for _ in range(100):
            try: kind, text = self.controller.events.get_nowait()
            except Empty: break
            if kind == "status":
                if not self.closing: self.status.set(text)
                self.wake.set(self.controller.wake.is_set())
            elif kind == "approval":
                if not self.closing: self.show_approval(text)
            elif kind == "approval_done":
                if self.approval_id == text and self.approval_window is not None:
                    self.approval_window.destroy()
                    self.approval_window = None
                    self.approval_id = None
            elif kind == "clear":
                self.chat.configure(state="normal")
                self.chat.delete("1.0", "end")
                self.chat.configure(state="disabled")
            elif kind == "quit": self.close()
            elif kind == "closed":
                if self.closing:
                    self.destroy()
                    return
            elif not self.closing: self.write(kind, text)
        if self.closing and not self.controller.thread.is_alive():
            self.destroy()
            return
        self.after(50, self.poll)

    def toggle_agent(self):
        self.controller.agent_enabled = self.agent_mode.get()
        if not self.agent_mode.get(): self.controller.stop_task()
        self.write("info", "Modo agente ativado. Leituras permitidas podem ser enviadas ao endpoint de IA. Alterações exigem aprovação." if self.agent_mode.get() else "Modo conversa ativado.")

    def show_approval(self, request):
        window = tk.Toplevel(self)
        self.approval_window, self.approval_id = window, request["id"]
        window.title(request["title"])
        window.geometry("760x570")
        window.configure(bg=BG)
        window.transient(self)
        # Non-modal so the main emergency stop remains accessible.
        tk.Label(window, text=request["title"], bg=BG, fg=GOLD, font=("Segoe UI",15,"bold")).pack(padx=15,pady=12)
        tk.Label(window, text="Revise a ação completa. A aprovação vale somente para esta chamada e expira em 120 segundos.", bg=BG, fg="white", wraplength=700).pack(padx=15,pady=5)
        frame = tk.Frame(window,bg=BG)
        frame.pack(fill="both",expand=True,padx=15,pady=10)
        preview = tk.Text(frame,wrap="word",bg=PANEL,fg="white",font=("Consolas",11))
        scroll = ttk.Scrollbar(frame,command=preview.yview)
        scroll.pack(side="right",fill="y")
        preview.pack(side="left",fill="both",expand=True)
        preview.configure(yscrollcommand=scroll.set)
        preview.insert("1.0",request["preview"])
        preview.configure(state="disabled")
        buttons = tk.Frame(window,bg=BG)
        buttons.pack(pady=12)
        def answer(allowed):
            window.withdraw()
            self.update_idletasks()
            self.controller.agent.tools.approvals.resolve(request["id"],allowed)
            # The event poll closes the window; the worker cannot touch Tk.
        ttk.Button(buttons,text="Recusar",command=lambda:answer(False)).pack(side="left",padx=10)
        ttk.Button(buttons,text="Aprovar esta ação",command=lambda:answer(True)).pack(side="left",padx=10)
        window.protocol("WM_DELETE_WINDOW",lambda:answer(False))
        window.bind("<Escape>",lambda event:self.controller.stop_task())

    def animate(self):
        if self.closing: return
        self.orb.delete("all")
        self.angle += 1.5
        for i, radius in enumerate((50, 72, 92)):
            self.orb.create_arc(110-radius,105-radius,110+radius,105+radius,
                start=self.angle*(i+1),extent=240,style="arc",outline=GOLD if i%2 else GREEN,width=2)
        pulse = 29 + math.sin(self.angle/15)*3
        self.orb.create_oval(110-pulse,105-pulse,110+pulse,105+pulse,outline=GOLD,width=2)
        self.orb.create_text(110,105,text="A",fill=GOLD,font=("Segoe UI",24,"bold"))
        self.after(40,self.animate)

    def close(self):
        if self.closing: return
        self.closing = True
        self.entry.configure(state="disabled")
        self.status.set("Encerrando… aguardando operação atual")
        self.controller.close()
