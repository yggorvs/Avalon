import customtkinter as ctk
import tkinter as tk
import math
import time
import threading
import random

# --- PALETA DE CORES PROFISSIONAL ---
BG_COLOR = "#030406"
GOLD = "#D4AF37"
GREEN = "#39FF14"
GOLD_DARK = "#4a3d13" # Ouro sutil para as partículas de fundo
GREEN_DARK = "#124a08" # Verde sutil para as partículas de fundo
CYAN = "#00ffff" # Cor para anéis sutil de órbita (como no exemplo)

class AvalonOrbitalV2UI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("A.V.A.L.O.N. | Órbita Neural V2")
        self.geometry("1100x750")
        self.configure(fg_color=BG_COLOR)

        # --- 1. HUD / PAINEL LATERAL (Status Técnico) ---
        self.hud_frame = ctk.CTkFrame(self, fg_color="transparent", width=250)
        self.hud_frame.pack(side="left", fill="y", padx=30, pady=40)

        ctk.CTkLabel(self.hud_frame, text="AVALON.OS", font=("Orbitron", 26, "bold"), text_color=GOLD).pack(anchor="w")
        ctk.CTkLabel(self.hud_frame, text="SISTEMA ORBITAL V2", font=("Consolas", 12), text_color=GREEN).pack(anchor="w", pady=(0, 40))

        self.lbl_status = self.criar_linha_hud("STATUS:", "ESTÁVEL", GOLD)
        self.lbl_motor = self.criar_linha_hud("MOTOR 3D:", "ATIVO", GREEN)
        self.lbl_rede = self.criar_linha_hud("REDE NEURAL:", "ONLINE", GOLD)

        self.btn_escutar = ctk.CTkButton(self.hud_frame, text="🎙️ INICIAR ESCUTA", 
                                         font=("Consolas", 14, "bold"), fg_color="#1a1a00", 
                                         border_color=GOLD, border_width=1, hover_color="#332a00",
                                         command=self.alternar_modo)
        self.btn_escutar.pack(side="bottom", pady=20)

        # --- 2. TELA DE RENDERIZAÇÃO (Canvas Escuro) ---
        self.canvas = tk.Canvas(self, bg=BG_COLOR, highlightthickness=0)
        self.canvas.pack(side="right", fill="both", expand=True)

        # --- 3. MOTOR ORBITAL V2 ---
        self.particulas_nucleo = [] # Mesh densa central
        self.particulas_aura = []   # Nuvemdispersa externa
        
        # Gera o novo núcleo denso (Dourado vibrante)
        self.gerar_esfera_nucleo(raios=20, segmentos=40, raio_nucleo=60)
        # Gera a aura orbital externa (Verde sutil)
        self.gerar_nuvem_aura(quantidade=500, raio_min=100, raio_max=350)
        
        self.angulo_y = 0.0
        self.angulo_x = 0.0
        self.escutando = False
        self.tempo_inicio = time.time()
        
        # Inicia o loop de renderização (Z-Sorting implementado)
        self.renderizar_frame()

    def criar_linha_hud(self, titulo, valor, cor):
        frame = ctk.CTkFrame(self.hud_frame, fg_color="transparent")
        frame.pack(fill="x", pady=10)
        ctk.CTkLabel(frame, text=titulo, font=("Consolas", 14), text_color="#666").pack(side="left")
        lbl_valor = ctk.CTkLabel(frame, text=f" {valor}", font=("Consolas", 14, "bold"), text_color=cor)
        lbl_valor.pack(side="right")
        return lbl_valor

    def gerar_esfera_nucleo(self, raios, segmentos, raio_nucleo):
        """Gera coordenadas 3D para uma mesh esférica densa do núcleo"""
        for i in range(raios):
            lat = math.pi * i / raios - (math.pi / 2) # Latitude
            for j in range(segmentos):
                lon = 2 * math.pi * j / segmentos     # Longitude
                
                # Equação paramétrica da esfera
                x = math.cos(lat) * math.cos(lon) * raio_nucleo
                y = math.sin(lat) * raio_nucleo
                z = math.cos(lat) * math.sin(lon) * raio_nucleo
                
                self.particulas_nucleo.append((x, y, z))

    def gerar_nuvem_aura(self, quantidade, raio_min, raio_max):
        """Gera partículas em distâncias aleatórias ao redor do centro"""
        for _ in range(quantidade):
            # Distribuição esférica
            distancia = random.uniform(raio_min, raio_max)
            theta = random.uniform(0, 2 * math.pi)
            phi = math.acos(random.uniform(-1, 1))
            
            x = distancia * math.sin(phi) * math.cos(theta)
            y = distancia * math.sin(phi) * math.sin(theta)
            z = distancia * math.cos(phi)
            
            self.particulas_aura.append((x, y, z))

    def rotacionar_3d(self, x, y, z, ang_x, ang_y):
        # Eixo X
        y1 = y * math.cos(ang_x) - z * math.sin(ang_x)
        z1 = y * math.sin(ang_x) + z * math.cos(ang_x)
        # Eixo Y
        x2 = x * math.cos(ang_y) + z1 * math.sin(ang_y)
        z2 = -x * math.sin(ang_y) + z1 * math.cos(ang_y)
        return x2, y1, z2

    def renderizar_frame(self):
        self.canvas.delete("all")
        
        largura = self.canvas.winfo_width()
        altura = self.canvas.winfo_height()
        centro_x, centro_y = largura // 2, altura // 2

        if largura > 10:
            tempo_atual = time.time() - self.tempo_inicio

            # Lógica de Modos (Standby vs Escutando)
            if self.escutando:
                self.angulo_y += 0.05  # Órbita rápida
                self.angulo_x += 0.02
                # O núcleo denso vibra agressivamente
                vibra_nucleo = 1 + math.sin(tempo_atual * 25) * 0.15 
                cor_particula = GREEN
                cor_fundo_aura = GREEN_DARK
                cor_fundo_nucleo = GOLD_DARK
            else:
                self.angulo_y += 0.005 # Órbita lenta
                self.angulo_x += 0.002
                # O núcleo denso "respira" calmamente
                vibra_nucleo = 1 + math.sin(tempo_atual * 3) * 0.05 
                cor_particula = GOLD
                cor_fundo_aura = GOLD_DARK
                cor_fundo_nucleo = "#221d09"

            # Lista para Z-Sorting: (x_tela, y_tela, depth_z, size, color)
            z_sort_list = []

            # 1. Processar Partículas da Aura (Nuvem dispersa)
            for (x, y, z) in self.particulas_aura:
                rx, ry, rz = self.rotacionar_3d(x, y, z, self.angulo_x, self.angulo_y)
                tela_x = centro_x + rx
                tela_y = centro_y + ry
                cor_final = GREEN if not self.escutando else cor_particula
                if rz < 0:
                    cor_final = cor_fundo_aura
                z_sort_list.append((tela_x, tela_y, rz, 2, cor_final))

            # 2. Processar Partículas do Novo Núcleo (Mesh densa central)
            for (x, y, z) in self.particulas_nucleo:
                # O núcleo vibra sutilmente
                x_v, y_v, z_v = x * vibra_nucleo, y * vibra_nucleo, z * vibra_nucleo
                rx, ry, rz = self.rotacionar_3d(x_v, y_v, z_v, self.angulo_x, self.angulo_y)
                tela_x = centro_x + rx
                tela_y = centro_y + ry
                tamanho_p = 3 if not self.escutando else 4
                cor_final = GOLD
                if rz < 0:
                    cor_final = cor_fundo_nucleo
                z_sort_list.append((tela_x, tela_y, rz, tamanho_p, cor_final))

            # 3. Z-Sorting: Ordenar a lista pela profundidade (rz)
            # Organiza do fundo (menor z) para a frente (maior z)
            z_sort_list.sort(key=lambda p: p[2])

            # 4. Desenhar com Profundidade
            for (px, py, pz, size, color) in z_sort_list:
                # Efeito sutil de brilho: Partículas próximas ficam mais brilhantes
                if pz > 0 and self.escutando and random.random() > 0.98:
                    # Desenha um feixe técnico sutil conectando partículas da frente
                    self.canvas.create_line(centro_x, centro_y, px, py, fill=GREEN, width=1)
                
                self.canvas.create_oval(px-size, py-size, px+size, py+size, fill=color, outline="")

            # Adiciona o texto do AVALON no centro do núcleo de mesh
            self.canvas.create_text(centro_x, centro_y, text="AVALON", fill=BG_COLOR, font=("Orbitron", 14, "bold"))

        self.after(20, self.renderizar_frame)

    def alternar_modo(self):
        self.escutando = True
        self.lbl_status.configure(text=" CAPTURANDO", text_color=GREEN)
        self.btn_escutar.configure(state="disabled", text="[ NÚCLEO EM ALERTA ]")
        
        threading.Thread(target=self.simular_resposta, daemon=True).start()

    def simular_resposta(self):
        time.sleep(5) 
        self.escutando = False
        self.lbl_status.configure(text=" ESTÁVEL", text_color=GOLD)
        self.btn_escutar.configure(state="normal", text="🎙️ INICIAR ESCUTA")

if __name__ == "__main__":
    app = AvalonOrbitalV2UI()
    app.mainloop()