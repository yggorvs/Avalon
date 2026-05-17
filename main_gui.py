import customtkinter as ctk
import tkinter as tk
import math
import time
import threading
import random

# --- IMPORTAÇÕES DO SEU BACK-END ---
from audicao import ouvir_e_transcrever
from cerebro import pensar
from voz import falar
from automacao import verificar_e_executar

# --- PALETA DE CORES ---
BG_COLOR = "#030406"
GOLD = "#D4AF37"
GREEN = "#39FF14"
GOLD_DARK = "#4a3d13" 
GREEN_DARK = "#124a08" 

class AvalonMainUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("A.V.A.L.O.N. | Central de Comando")
        self.geometry("1100x750")
        self.configure(fg_color=BG_COLOR)

        # --- HUD / PAINEL LATERAL ---
        self.hud_frame = ctk.CTkFrame(self, fg_color="transparent", width=300)
        self.hud_frame.pack(side="left", fill="y", padx=30, pady=40)

        ctk.CTkLabel(self.hud_frame, text="AVALON.OS", font=("Orbitron", 26, "bold"), text_color=GOLD).pack(anchor="w")
        ctk.CTkLabel(self.hud_frame, text="SISTEMA INTEGRADO", font=("Consolas", 12), text_color=GREEN).pack(anchor="w", pady=(0, 40))

        self.lbl_status = self.criar_linha_hud("STATUS:", "STANDBY", GOLD)
        self.lbl_motor = self.criar_linha_hud("MOTOR 3D:", "ATIVO", GREEN)
        self.lbl_ia = self.criar_linha_hud("NÚCLEO IA:", "ONLINE", GREEN)

        self.log_caixa = ctk.CTkTextbox(self.hud_frame, width=280, height=200, fg_color="#0a0d14", 
                                        text_color="#a88c3a", font=("Consolas", 12), border_color="#1a1a1a", border_width=1)
        self.log_caixa.pack(pady=30)
        self.log_caixa.insert("0.0", "[SISTEMA]: Inicialização concluída.\n")
        self.log_caixa.configure(state="disabled")

        self.btn_escutar = ctk.CTkButton(self.hud_frame, text="🎙️ INICIAR ESCUTA", 
                                         font=("Consolas", 14, "bold"), fg_color="#1a1a00", 
                                         border_color=GOLD, border_width=1, hover_color="#332a00",
                                         command=self.iniciar_fluxo_ia)
        self.btn_escutar.pack(side="bottom", pady=20)

        # --- TELA DE RENDERIZAÇÃO 3D ---
        self.canvas = tk.Canvas(self, bg=BG_COLOR, highlightthickness=0)
        self.canvas.pack(side="right", fill="both", expand=True)

        self.particulas_nucleo = [] 
        self.particulas_aura = []   
        self.gerar_esfera_nucleo(raios=20, segmentos=40, raio_nucleo=60)
        self.gerar_nuvem_aura(quantidade=500, raio_min=100, raio_max=350)
        
        self.angulo_y = 0.0
        self.angulo_x = 0.0
        self.escutando = False
        self.tempo_inicio = time.time()
        
        self.conversando = False 

        # Inicia a Interface Visual e o Vigilante
        self.renderizar_frame()
        threading.Thread(target=self.vigilante_wake_word, daemon=True).start()

    # --- INTELIGÊNCIA ARTIFICIAL E FLUXOS ---
    def vigilante_wake_word(self):
        """Ouvido Passivo: Espera você dizer 'Avalon' para acordar"""
        self.atualizar_log("[SISTEMA]: Vigilante ativado. Diga 'Avalon'.", GREEN)
        
        while True:
            if not self.conversando:
                try:
                    texto_ouvido = ouvir_e_transcrever()
                    if texto_ouvido:
                        texto_lower = texto_ouvido.lower()
                        if "avalon" in texto_lower:
                            self.atualizar_log(f"[WAKE WORD]: '{texto_ouvido}'", GOLD)
                            falar("Estou ouvindo.") 
                            self.iniciar_fluxo_ia() 
                except Exception:
                    pass 
            else:
                time.sleep(1)

    def iniciar_fluxo_ia(self):
        """Trava o botão e inicia o loop de conversa"""
        self.btn_escutar.configure(state="disabled", text="[ CONVERSA ATIVA ]")
        self.atualizar_log("[AVALON]: Iniciando conversa contínua...", GREEN)
        threading.Thread(target=self.processo_ia_backend, daemon=True).start()

    def processo_ia_backend(self):
        """Loop de conversa que só termina com despedida"""
        self.conversando = True
        
        while self.conversando:
            try:
                self.escutando = True 
                self.lbl_status.configure(text=" ESCUTANDO...", text_color=GREEN)
                
                texto_usuario = ouvir_e_transcrever()
                
                if not texto_usuario:
                    continue

                self.atualizar_log(f"Você: {texto_usuario}", "#ffffff")
                texto_lower = texto_usuario.lower()
                
                palavras_despedida = ["tchau", "adeus", "até logo", "encerrar", "dormir", "dispensado"]
                if any(palavra in texto_lower for palavra in palavras_despedida):
                    self.escutando = False
                    self.lbl_status.configure(text=" PROCESSANDO", text_color="#00ffff")
                    self.atualizar_log("[AVALON]: Encerrando modo de escuta.")
                    falar("Entendido. Estarei em standby se precisar de mim. Até logo.")
                    self.conversando = False 
                    break 

                if "desligar o sistema" in texto_lower:
                    self.atualizar_log("[AVALON]: Encerrando sistemas centrais...")
                    falar("Encerrando todas as funções. Adeus.")
                    self.after(2000, self.destroy) 
                    return

                self.escutando = False 
                self.lbl_status.configure(text=" PROCESSANDO", text_color="#00ffff")
                
                resultado_acao = verificar_e_executar(texto_usuario)
                
                if resultado_acao:
                    resposta = resultado_acao
                else:
                    resposta = pensar(texto_usuario)

                self.atualizar_log(f"[AVALON]: {resposta}")
                falar(resposta) 

            except Exception as e:
                self.atualizar_log(f"[ERRO]: {str(e)}", "#ff4c4c")
                self.conversando = False
                break

        self.finalizar_fluxo_ia("Conversa finalizada.")

    def finalizar_fluxo_ia(self, log_final):
        """Retorna o visual ao Standby"""
        self.escutando = False 
        self.lbl_status.configure(text=" STANDBY", text_color=GOLD)
        self.btn_escutar.configure(state="normal", text="🎙️ INICIAR ESCUTA")
        self.atualizar_log(f"[SISTEMA]: {log_final}\n")

    # --- FUNÇÕES VISUAIS E MOTOR 3D ---
    def atualizar_log(self, texto, cor=GOLD):
        self.log_caixa.configure(state="normal")
        self.log_caixa.insert("end", f"\n{texto}")
        self.log_caixa.see("end")
        self.log_caixa.configure(state="disabled")

    def criar_linha_hud(self, titulo, valor, cor):
        frame = ctk.CTkFrame(self.hud_frame, fg_color="transparent")
        frame.pack(fill="x", pady=10)
        ctk.CTkLabel(frame, text=titulo, font=("Consolas", 14), text_color="#666").pack(side="left")
        lbl_valor = ctk.CTkLabel(frame, text=f" {valor}", font=("Consolas", 14, "bold"), text_color=cor)
        lbl_valor.pack(side="right")
        return lbl_valor

    def gerar_esfera_nucleo(self, raios, segmentos, raio_nucleo):
        for i in range(raios):
            lat = math.pi * i / raios - (math.pi / 2)
            for j in range(segmentos):
                lon = 2 * math.pi * j / segmentos
                x = math.cos(lat) * math.cos(lon) * raio_nucleo
                y = math.sin(lat) * raio_nucleo
                z = math.cos(lat) * math.sin(lon) * raio_nucleo
                self.particulas_nucleo.append((x, y, z))

    def gerar_nuvem_aura(self, quantidade, raio_min, raio_max):
        for _ in range(quantidade):
            distancia = random.uniform(raio_min, raio_max)
            theta = random.uniform(0, 2 * math.pi)
            phi = math.acos(random.uniform(-1, 1))
            x = distancia * math.sin(phi) * math.cos(theta)
            y = distancia * math.sin(phi) * math.sin(theta)
            z = distancia * math.cos(phi)
            self.particulas_aura.append((x, y, z))

    def rotacionar_3d(self, x, y, z, ang_x, ang_y):
        y1 = y * math.cos(ang_x) - z * math.sin(ang_x)
        z1 = y * math.sin(ang_x) + z * math.cos(ang_x)
        x2 = x * math.cos(ang_y) + z1 * math.sin(ang_y)
        z2 = -x * math.sin(ang_y) + z1 * math.cos(ang_y)
        return x2, y1, z2

    def renderizar_frame(self):
        self.canvas.delete("all")
        largura, altura = self.canvas.winfo_width(), self.canvas.winfo_height()
        centro_x, centro_y = largura // 2, altura // 2

        if largura > 10:
            tempo_atual = time.time() - self.tempo_inicio

            if self.escutando:
                self.angulo_y += 0.05
                self.angulo_x += 0.02
                vibra_nucleo = 1 + math.sin(tempo_atual * 25) * 0.15 
                cor_particula = GREEN
                cor_fundo_aura = GREEN_DARK
                cor_fundo_nucleo = GOLD_DARK
            else:
                self.angulo_y += 0.005
                self.angulo_x += 0.002
                vibra_nucleo = 1 + math.sin(tempo_atual * 3) * 0.05 
                cor_particula = GOLD
                cor_fundo_aura = GOLD_DARK
                cor_fundo_nucleo = "#221d09"

            z_sort_list = []
            for (x, y, z) in self.particulas_aura:
                rx, ry, rz = self.rotacionar_3d(x, y, z, self.angulo_x, self.angulo_y)
                cor_final = GREEN if not self.escutando else cor_particula
                if rz < 0: cor_final = cor_fundo_aura
                z_sort_list.append((centro_x + rx, centro_y + ry, rz, 2, cor_final))

            for (x, y, z) in self.particulas_nucleo:
                rx, ry, rz = self.rotacionar_3d(x * vibra_nucleo, y * vibra_nucleo, z * vibra_nucleo, self.angulo_x, self.angulo_y)
                cor_final = GOLD
                if rz < 0: cor_final = cor_fundo_nucleo
                tamanho_p = 3 if not self.escutando else 4
                z_sort_list.append((centro_x + rx, centro_y + ry, rz, tamanho_p, cor_final))

            z_sort_list.sort(key=lambda p: p[2])

            for (px, py, pz, size, color) in z_sort_list:
                if pz > 0 and self.escutando and random.random() > 0.98:
                    self.canvas.create_line(centro_x, centro_y, px, py, fill=GREEN, width=1)
                self.canvas.create_oval(px-size, py-size, px+size, py+size, fill=color, outline="")

            self.canvas.create_text(centro_x, centro_y, text="AVALON", fill=BG_COLOR, font=("Orbitron", 14, "bold"))

        self.after(20, self.renderizar_frame)

if __name__ == "__main__":
    app = AvalonMainUI()
    app.mainloop()