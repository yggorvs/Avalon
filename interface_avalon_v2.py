import customtkinter as ctk
import tkinter as tk
import math
import random
import threading
import time

# --- CONFIGURAÇÕES DE DESIGN ---
COLOR_GOLD = "#D4AF37"  # Dourado Metálico
COLOR_GREEN = "#39FF14" # Verde Neon
COLOR_BG = "#050505"    # Preto profundo

class AvalonCoreUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AVALON | NÚCLEO DIGITAL")
        self.geometry("1100x750")
        self.configure(fg_color=COLOR_BG)
        
        # Variáveis de animação
        self.angle = 0
        self.is_listening = False

        # --- LAYOUT ---
        # Painel Lateral Esquerdo (Status)
        self.side_panel = ctk.CTkFrame(self, width=220, fg_color="transparent")
        self.side_panel.pack(side="left", fill="y", padx=30, pady=30)

        self.setup_status_panel()

        # Área Central do Núcleo
        self.canvas = tk.Canvas(self, bg=COLOR_BG, highlightthickness=0, bd=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        # Botão Inferior
        self.btn_listen = ctk.CTkButton(self, text="INVOCAR NÚCLEO", 
                                        font=("Orbitron", 14, "bold"),
                                        fg_color="transparent", 
                                        border_color=COLOR_GOLD, 
                                        border_width=2,
                                        text_color=COLOR_GOLD,
                                        hover_color="#1a1a00",
                                        corner_radius=15,
                                        height=50,
                                        command=self.trigger_listen)
        self.btn_listen.place(relx=0.5, rely=0.9, anchor="center")

        # Iniciar loop de animação
        self.update_animation()

    def setup_status_panel(self):
        # Título
        ctk.CTkLabel(self.side_panel, text="AVALON SYSTEM", font=("Orbitron", 18, "bold"), text_color=COLOR_GOLD).pack(pady=(20, 40))
        
        # Status com luzes
        self.create_status_indicator("NÚCLEO", "ATIVO", COLOR_GREEN)
        self.create_status_indicator("API KEY", "CONECTADO", COLOR_GOLD)
        self.create_status_indicator("SISTEMA", "ESTÁVEL", COLOR_GREEN)

        self.log_label = ctk.CTkLabel(self.side_panel, text="Aguardando ativação...", 
                                      font=("Consolas", 12), text_color="#555", wraplength=180)
        self.log_label.pack(side="bottom", pady=20)

    def create_status_indicator(self, label, status, color):
        frame = ctk.CTkFrame(self.side_panel, fg_color="transparent")
        frame.pack(fill="x", pady=10)
        ctk.CTkLabel(frame, text=f"{label}:", font=("Consolas", 13), text_color="#888").pack(side="left")
        ctk.CTkLabel(frame, text=f" {status}", font=("Consolas", 13, "bold"), text_color=color).pack(side="left")

    def draw_lightning(self, cx, cy, r_in, r_out):
        """Gera feixes de raio entre dois raios (círculos)"""
        if random.random() > 0.7: # Só desenha raios em alguns frames
            angle = random.uniform(0, 2 * math.pi)
            # Pontos do raio
            x1 = cx + r_in * math.cos(angle)
            y1 = cy + r_in * math.sin(angle)
            
            # Criar um caminho em zigue-zague para o raio
            mid_r = (r_in + r_out) / 2
            x_mid = cx + mid_r * math.cos(angle + random.uniform(-0.2, 0.2))
            y_mid = cy + mid_r * math.sin(angle + random.uniform(-0.2, 0.2))
            
            x2 = cx + r_out * math.cos(angle)
            y2 = cy + r_out * math.sin(angle)
            
            color = random.choice([COLOR_GOLD, COLOR_GREEN])
            self.canvas.create_line(x1, y1, x_mid, y_mid, x2, y2, fill=color, width=2, capstyle="round", tags="bolt")

    def update_animation(self):
        self.canvas.delete("all")
        
        # Centro do Canvas
        cx = self.canvas.winfo_width() // 2
        cy = self.canvas.winfo_height() // 2
        
        if cx > 1: # Só desenha se o canvas já tiver tamanho
            # 1. Desenhar Órbitas (Anéis)
            for i, r in enumerate([120, 180, 240]):
                speed = (i + 1) * 2
                start_ang = self.angle * speed
                # Desenha arcos interrompidos para parecer tecnológico
                self.canvas.create_arc(cx-r, cy-r, cx+r, cy+r, start=start_ang, extent=120, 
                                       outline=COLOR_GOLD, style="arc", width=1)
                self.canvas.create_arc(cx-r, cy-r, cx+r, cy+r, start=start_ang+180, extent=60, 
                                       outline=COLOR_GREEN, style="arc", width=1)

            # 2. Desenhar Núcleo (Hexágono Central)
            r_core = 60 + math.sin(self.angle * 0.1) * 5 # Pulsação
            points = []
            for i in range(6):
                a = math.radians(i * 60 + self.angle)
                points.extend([cx + r_core * math.cos(a), cy + r_core * math.sin(a)])
            
            self.canvas.create_polygon(points, outline=COLOR_GOLD, fill="#111", width=2)
            self.canvas.create_text(cx, cy, text="AVALON", fill=COLOR_GOLD, font=("Orbitron", 12, "bold"))

            # 3. Gerar Feixes de Raio
            self.draw_lightning(cx, cy, 60, 240)

        # Atualizar variáveis
        self.angle += 1
        self.after(20, self.update_animation)

    def trigger_listen(self):
        self.log_label.configure(text="🎙️ NÚCLEO EM ESCUTA...", text_color=COLOR_GOLD)
        self.btn_listen.configure(state="disabled", text="ESCUTANDO...")
        
        # Simula processo de escuta
        threading.Thread(target=self.end_listen_sim, daemon=True).start()

    def end_listen_sim(self):
        time.sleep(4)
        self.log_label.configure(text="✅ COMANDO PROCESSADO", text_color=COLOR_GREEN)
        self.btn_listen.configure(state="normal", text="INVOCAR NÚCLEO")

if __name__ == "__main__":
    app = AvalonCoreUI()
    app.mainloop()