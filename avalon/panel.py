"""On-demand conversation panel; the orb owns the only event consumer."""
import tkinter as tk
from tkinter import ttk

BG='#080d17'
PANEL='#111b2b'
GOLD='#dfb958'
GREEN='#62e9a5'

class ConversationPanel(tk.Toplevel):
    def __init__(self,orb):
        super().__init__(orb)
        self.orb=orb
        self.controller=orb.controller
        self.title('Avalon • Conversa e controles')
        self.geometry('520x640')
        self.minsize(420,480)
        self.configure(bg=BG,padx=16,pady=16)
        self.attributes('-topmost',True)
        self.protocol('WM_DELETE_WINDOW',self.withdraw)
        self.bind('<Escape>',lambda event:self.controller.stop_task())
        self.columnconfigure(0,weight=1)
        self.rowconfigure(2,weight=1)
        tk.Label(self,text='AVALON',fg=GOLD,bg=BG,font=('Segoe UI',18,'bold')).grid(row=0,column=0,sticky='w')
        self.status=tk.StringVar(value='Pronto')
        tk.Label(self,textvariable=self.status,fg=GREEN,bg=BG,wraplength=460,anchor='w').grid(row=1,column=0,sticky='ew',pady=(4,10))
        frame=tk.Frame(self,bg=BG)
        frame.grid(row=2,column=0,sticky='nsew')
        self.chat=tk.Text(frame,bg=PANEL,fg='#e1e9f5',font=('Segoe UI',11),wrap='word',relief='flat',padx=12,pady=12,state='disabled')
        scroll=ttk.Scrollbar(frame,command=self.chat.yview)
        scroll.pack(side='right',fill='y')
        self.chat.pack(side='left',fill='both',expand=True)
        self.chat.configure(yscrollcommand=scroll.set)
        self.chat.tag_configure('user',foreground=GOLD)
        self.chat.tag_configure('assistant',foreground=GREEN)
        self.chat.tag_configure('error',foreground='#ff9f9f')
        self.entry=tk.Entry(self,bg=PANEL,fg='white',insertbackground='white',font=('Segoe UI',12),relief='flat')
        self.entry.grid(row=3,column=0,sticky='ew',pady=12,ipady=10)
        self.entry.bind('<Return>',self.send)
        buttons=tk.Frame(self,bg=BG)
        buttons.grid(row=4,column=0,sticky='ew')
        ttk.Button(buttons,text='Ouvir',command=self.controller.listen_once).pack(side='left',padx=(0,6))
        ttk.Button(buttons,text='PARAR',command=self.controller.stop_task).pack(side='left',padx=6)
        ttk.Button(buttons,text='Enviar ↵',command=self.send).pack(side='right')
        switches=tk.Frame(self,bg=BG)
        switches.grid(row=5,column=0,sticky='w',pady=(10,0))
        for label,variable,command in (
            ('Voz contínua',orb.wake,orb.toggle_wake),
            ('Ler respostas',orb.speak,orb.toggle_speak),
            ('Modo agente',orb.agent_mode,orb.toggle_agent)):
            tk.Checkbutton(switches,text=label,variable=variable,command=command,bg=BG,fg='white',
                selectcolor=PANEL,activebackground=BG,activeforeground=GOLD).pack(side='left')
        tk.Label(self,text='Fechar este painel mantém a bolinha ativa. Botão direito nela: opções e Sair.',
                 bg=BG,fg='#91a6be',wraplength=470,font=('Segoe UI',9)).grid(row=6,column=0,sticky='w',pady=(10,0))

    def write(self,kind,text):
        self.chat.configure(state='normal')
        label={'user':'VOCÊ','assistant':'AVALON','error':'AVISO','info':'SISTEMA'}.get(kind,'SISTEMA')
        self.chat.insert('end',label+'\n',kind)
        self.chat.insert('end',text+'\n\n')
        if int(self.chat.index('end-1c').split('.')[0])>1200: self.chat.delete('1.0','250.0')
        self.chat.configure(state='disabled')
        self.chat.see('end')

    def clear(self):
        self.chat.configure(state='normal'); self.chat.delete('1.0','end'); self.chat.configure(state='disabled')

    def send(self,event=None):
        if self.controller.submit(self.entry.get()): self.entry.delete(0,'end')
        return 'break'

    def reveal(self):
        self.deiconify(); self.lift(); self.entry.focus_set()
