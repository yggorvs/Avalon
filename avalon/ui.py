"""Floating pixel-art orb. All Tk access stays on the main thread."""
from collections import deque
from queue import Empty
from pathlib import Path
import sys
import time
import tkinter as tk
from tkinter import ttk
from PIL import ImageTk
from .sprites import SpriteAtlas
from .overlay_state import Preferences, VisualState
from .panel import ConversationPanel, BG, PANEL, GOLD, GREEN

COLOR_KEY='#ff00ff'

class App(tk.Tk):
    def __init__(self,controller):
        super().__init__()
        self.withdraw()
        self.controller=controller
        self.closing=False
        self.poll_timer=None
        self.animation_timer=None
        self.tooltip_timer=None
        self.panel=None
        self.approval_window=None
        self.approval_id=None
        self.events_history=deque(maxlen=200)
        self.visual=VisualState()
        self.title('Avalon • Núcleo flutuante')
        self.preferences_path=controller.memory_path.parent/'overlay.json' if hasattr(controller,'memory_path') else Path.home()/'.avalon'/'overlay.json'
        self.preferences=Preferences.load(self.preferences_path)
        self.atlas=SpriteAtlas()
        self.photo_cache={}
        self.start_time=time.monotonic()
        self.last_frame=None
        self.hover=False
        self.drag=None
        self.click_timer=None
        self.tooltip=None
        self.wake=tk.BooleanVar(value=controller.wake.is_set())
        self.speak=tk.BooleanVar(value=controller.speak_enabled)
        self.agent_mode=tk.BooleanVar(value=controller.agent_enabled)
        self.animation=tk.BooleanVar(value=self.preferences.animate)
        self.overrideredirect(True)
        self.attributes('-topmost',True)
        self.background=BG
        if sys.platform=='win32':
            try:
                self.attributes('-transparentcolor',COLOR_KEY)
                self.attributes('-toolwindow',True)
                self.background=COLOR_KEY
            except tk.TclError: pass
        self.configure(bg=self.background)
        self.canvas=tk.Canvas(self,bg=self.background,highlightthickness=0,bd=0,cursor='hand2')
        self.canvas.pack(fill='both',expand=True)
        self.sprite_item=self.canvas.create_image(0,0,anchor='nw')
        self.stop_item=self.canvas.create_oval(0,0,0,0,fill='#c63e44',outline='#ff9797',state='hidden',tags='stop')
        self.stop_text=self.canvas.create_text(0,0,text='■',fill='white',font=('Segoe UI',10,'bold'),state='hidden',tags='stop')
        self.canvas.tag_bind('stop','<Button-1>',self.stop_clicked)
        self.canvas.bind('<ButtonPress-1>',self.press)
        self.canvas.bind('<B1-Motion>',self.motion)
        self.canvas.bind('<ButtonRelease-1>',self.release)
        self.canvas.bind('<Double-Button-1>',self.double_click)
        self.canvas.bind('<Button-3>',self.context_menu)
        self.canvas.bind('<Enter>',self.enter)
        self.canvas.bind('<Leave>',self.leave)
        self.bind('<Escape>',lambda event:self.controller.stop_task())
        self.protocol('WM_DELETE_WINDOW',self.close)
        self.set_size(self.preferences.size,save=False)
        self.deiconify()
        self.poll_timer=self.after(50,self.poll)
        self.animate()

    def set_size(self,size,save=True):
        if type(size) is not int or not 80<=size<=256: raise ValueError("Tamanho inválido.")
        self.preferences.size=size
        self.preferences.fit(self.winfo_screenwidth(),self.winfo_screenheight())
        self.canvas.configure(width=size,height=size)
        self.geometry(f'{size}x{size}+{self.preferences.x}+{self.preferences.y}')
        self.canvas.coords(self.stop_item,size-29,size-29,size-5,size-5)
        self.canvas.coords(self.stop_text,size-17,size-17)
        self.photo_cache.clear(); self.last_frame=None
        if save: self.save_preferences()

    def save_preferences(self):
        try: self.preferences.save(self.preferences_path)
        except OSError: self.record('error','Não foi possível salvar a posição da bolinha.')

    def press(self,event):
        if 'stop' in self.canvas.gettags('current'): self.drag=None; return 'break'
        self.hide_tooltip()
        self.drag=(event.x_root,event.y_root,self.winfo_x(),self.winfo_y(),False)

    def motion(self,event):
        if self.drag is None: return
        sx,sy,wx,wy,moved=self.drag
        dx,dy=event.x_root-sx,event.y_root-sy
        if abs(dx)+abs(dy)>5: moved=True
        self.drag=(sx,sy,wx,wy,moved)
        if moved:
            self.preferences.x=max(0,wx+dx); self.preferences.y=max(0,wy+dy)
            self.preferences.fit(self.winfo_screenwidth(),self.winfo_screenheight())
            self.geometry(f'+{self.preferences.x}+{self.preferences.y}')

    def release(self,event):
        if self.drag is None: return
        moved=self.drag[4]; self.drag=None
        if moved: self.save_preferences()
        else:
            if self.click_timer is not None: self.after_cancel(self.click_timer)
            self.click_timer=self.after(260,self.single_click)

    def single_click(self):
        self.click_timer=None
        self.show_panel()

    def double_click(self,event):
        if self.click_timer is not None:
            self.after_cancel(self.click_timer); self.click_timer=None
        self.drag=None
        if 'stop' not in self.canvas.gettags('current'): self.controller.listen_once()
        return 'break'

    def stop_clicked(self,event=None):
        self.controller.stop_task()
        self.drag=None
        if self.click_timer is not None: self.after_cancel(self.click_timer); self.click_timer=None
        return 'break'

    def enter(self,event=None):
        self.hover=True
        self.canvas.itemconfigure('stop',state='normal')
        self.canvas.tag_raise('stop')
        if self.tooltip_timer is not None: self.after_cancel(self.tooltip_timer)
        self.tooltip_timer=self.after(650,self.show_tooltip)

    def leave(self,event=None):
        self.hover=False
        if not self.visual.approval_id: self.canvas.itemconfigure('stop',state='hidden')
        self.hide_tooltip()

    def show_tooltip(self):
        self.tooltip_timer=None
        if not self.hover or self.tooltip or self.closing: return
        self.tooltip=tk.Toplevel(self)
        self.tooltip.overrideredirect(True); self.tooltip.attributes('-topmost',True)
        label=tk.Label(self.tooltip,text=self.visual.status+'\nClique: conversar • Duplo clique: ouvir\nArraste: mover • Botão direito: opções',
                       bg=PANEL,fg=GOLD,padx=10,pady=7,justify='left',font=('Segoe UI',9))
        label.pack()
        self.tooltip.update_idletasks()
        x=max(0,min(self.winfo_x()-180,self.winfo_screenwidth()-self.tooltip.winfo_reqwidth()))
        y=max(0,self.winfo_y()-self.tooltip.winfo_reqheight()-8)
        self.tooltip.geometry(f'+{x}+{y}')

    def hide_tooltip(self):
        if self.tooltip_timer is not None:
            self.after_cancel(self.tooltip_timer); self.tooltip_timer=None
        if self.tooltip is not None:
            self.tooltip.destroy(); self.tooltip=None

    def context_menu(self,event):
        self.hide_tooltip()
        menu=tk.Menu(self,tearoff=False)
        menu.add_command(label='Abrir conversa',command=self.show_panel)
        menu.add_command(label='Ouvir um comando',command=self.controller.listen_once)
        menu.add_checkbutton(label='Voz contínua',variable=self.wake,command=self.toggle_wake)
        menu.add_checkbutton(label='Ler respostas',variable=self.speak,command=self.toggle_speak)
        menu.add_checkbutton(label='Modo agente',variable=self.agent_mode,command=self.toggle_agent)
        menu.add_separator()
        menu.add_command(label='PARAR TAREFA',command=self.controller.stop_task,foreground='#c63e44')
        menu.add_command(label='Interromper fala',command=self.controller.audio.interrupt)
        sizes=tk.Menu(menu,tearoff=False)
        for size,label in ((96,'Pequena'),(144,'Normal'),(192,'Grande')):
            sizes.add_command(label=label,command=lambda size=size:self.set_size(size))
        menu.add_cascade(label='Tamanho',menu=sizes)
        menu.add_checkbutton(label='Animações',variable=self.animation,command=self.toggle_animation)
        menu.add_command(label='Reposicionar no canto',command=self.reset_position)
        menu.add_separator(); menu.add_command(label='Sair do Avalon',command=self.close)
        try: menu.tk_popup(event.x_root,event.y_root)
        finally: menu.grab_release(); menu.destroy()

    def reset_position(self):
        self.preferences.x=self.preferences.y=-1
        self.set_size(self.preferences.size)

    def toggle_animation(self):
        self.preferences.animate=self.animation.get(); self.last_frame=None; self.save_preferences()

    def toggle_wake(self): self.controller.set_wake(self.wake.get())
    def toggle_speak(self): self.controller.speak_enabled=self.speak.get()

    def toggle_agent(self):
        self.controller.agent_enabled=self.agent_mode.get()
        if not self.agent_mode.get(): self.controller.stop_task()
        self.record('info','Modo agente ativado. Leituras permitidas podem ser enviadas ao endpoint de IA; alterações exigem aprovação.' if self.agent_mode.get() else 'Modo conversa ativado.')

    def show_panel(self):
        if self.closing: return
        if self.panel is None:
            self.panel=ConversationPanel(self)
            for kind,text in self.events_history: self.panel.write(kind,text)
        self.panel.status.set(self.visual.status)
        self.panel.reveal()

    def record(self,kind,text):
        self.events_history.append((kind,text))
        if self.panel is not None: self.panel.write(kind,text)
        if kind=='error': self.visual.observe(kind,text)

    def poll(self):
        if self.poll_timer is not None:
            self.after_cancel(self.poll_timer)
            self.poll_timer=None
        for _ in range(100):
            try: kind,text=self.controller.events.get_nowait()
            except Empty: break
            self.visual.observe(kind,text)
            if kind=='status':
                self.wake.set(self.controller.wake.is_set())
                if self.panel is not None: self.panel.status.set(text)
            elif kind=='approval' and not self.closing:
                self.show_approval(text)
            elif kind=='approval_done':
                if self.approval_id==text and self.approval_window is not None:
                    self.approval_window.destroy(); self.approval_window=None; self.approval_id=None
            elif kind=='clear':
                self.events_history.clear()
                if self.panel is not None: self.panel.clear()
            elif kind=='quit': self.close()
            elif kind=='closed' and self.closing:
                self.destroy(); return
            elif kind in {'user','assistant','info','error'} and not self.closing:
                self.record(kind,text)
        if self.closing and not self.controller.thread.is_alive(): self.destroy(); return
        self.poll_timer=self.after(50,self.poll)

    def show_approval(self,request):
        self.hide_tooltip()
        window=tk.Toplevel(self)
        self.approval_window,self.approval_id=window,request['id']
        window.title(request['title']); window.geometry('760x570'); window.configure(bg=BG)
        window.attributes('-topmost',True)
        tk.Label(window,text=request['title'],bg=BG,fg=GOLD,font=('Segoe UI',15,'bold')).pack(padx=15,pady=12)
        tk.Label(window,text='Revise a ação completa. Aprovação única, válida por 120 segundos.',bg=BG,fg='white').pack(padx=15,pady=5)
        frame=tk.Frame(window,bg=BG); frame.pack(fill='both',expand=True,padx=15,pady=10)
        preview=tk.Text(frame,wrap='word',bg=PANEL,fg='white',font=('Consolas',11))
        scroll=ttk.Scrollbar(frame,command=preview.yview); scroll.pack(side='right',fill='y')
        preview.pack(side='left',fill='both',expand=True); preview.configure(yscrollcommand=scroll.set)
        preview.insert('1.0',request['preview']); preview.configure(state='disabled')
        buttons=tk.Frame(window,bg=BG); buttons.pack(pady=12)
        def answer(allowed):
            window.withdraw(); self.update_idletasks()
            self.controller.agent.tools.approvals.resolve(request['id'],allowed)
        ttk.Button(buttons,text='Recusar',command=lambda:answer(False)).pack(side='left',padx=8)
        ttk.Button(buttons,text='Aprovar esta ação',command=lambda:answer(True)).pack(side='left',padx=8)
        ttk.Button(buttons,text='PARAR TAREFA',command=self.controller.stop_task).pack(side='left',padx=8)
        window.protocol('WM_DELETE_WINDOW',lambda:answer(False))
        window.bind('<Escape>',lambda event:self.controller.stop_task())
        window.lift(); window.focus_set()
        self.canvas.itemconfigure('stop',state='normal')

    def animate(self):
        if self.closing: return
        state=self.visual.current()
        elapsed=(time.monotonic()-self.start_time)*1000
        index=self.atlas.index(state,elapsed,self.preferences.animate)
        key=state,index,self.preferences.size
        if key!=self.last_frame:
            if key not in self.photo_cache:
                frame=self.atlas.frame(state,index,self.preferences.size)
                self.photo_cache[key]=ImageTk.PhotoImage(frame,master=self)
            self.canvas.itemconfigure(self.sprite_item,image=self.photo_cache[key])
            self.last_frame=key
        self.animation_timer=self.after(50,self.animate)

    def close(self):
        if self.closing: return
        self.closing=True
        self.hide_tooltip()
        self.save_preferences()
        if self.panel is not None: self.panel.entry.configure(state='disabled')
        self.controller.close()

    def destroy(self):
        self.closing=True
        for name in ('poll_timer','animation_timer','tooltip_timer','click_timer'):
            timer=getattr(self,name,None)
            if timer is not None:
                try: self.after_cancel(timer)
                except tk.TclError: pass
                setattr(self,name,None)
        super().destroy()
