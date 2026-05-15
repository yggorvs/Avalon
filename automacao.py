import os
import subprocess

def verificar_e_executar(comando_usuario):
    comando = comando_usuario.lower()
    
    # 1. Abrir Bloco de Notas
    if "bloco de notas" in comando or "anotar" in comando:
        print("[AVALON] ⚙️ Executando automação: Abrir Notepad")
        os.startfile("notepad.exe") # Comando nativo do Windows
        return "Bloco de notas aberto na sua tela, senhor."
        
    # 2. Abrir Calculadora
    elif "calculadora" in comando or "calcular" in comando:
        print("[AVALON] ⚙️ Executando automação: Abrir Calculadora")
        os.startfile("calc.exe")
        return "Calculadora iniciada."
        
    # Aqui, no seu PC de casa, você vai colocar caminhos específicos:
    # elif "modo de estudo" in comando:
    #     os.startfile("C:\\Caminho\\Para\\Seu\\VSCode.exe")
    #     return "Ambiente de desenvolvimento carregado."

    # Retorna None se não reconhecer nenhuma automação
    return None