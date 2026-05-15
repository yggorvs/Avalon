from audicao import ouvir_e_transcrever, aguardar_wake_word
from cerebro import pensar
from voz import falar
from automacao import verificar_e_executar # <-- IMPORTAÇÃO NOVA

def iniciar_avalon():
    print("="*50)
    print("SISTEMA AVALON INICIADO")
    print("="*50)
    
    while True:
        try:
            aguardar_wake_word()
            falar("Estou ouvindo, senhor.")
            
            print("\n[AVALON] 🟢 Online. Diga seu comando...")
            texto_usuario = ouvir_e_transcrever()
            
            if not texto_usuario:
                continue
                
            if "desligar" in texto_usuario.lower() or "encerrar" in texto_usuario.lower():
                despedida = "Desligando os sistemas principais. Até logo."
                print(f"\n[AVALON]: {despedida}")
                falar(despedida)
                break
            
            # --- NOVO BLOCO DE AUTOMAÇÃO ---
            # O sistema tenta executar uma ação primeiro
            resultado_acao = verificar_e_executar(texto_usuario)
            
            if resultado_acao:
                # Se era uma automação, ele fala que executou e volta a dormir
                print(f"\n[AVALON]: {resultado_acao}")
                falar(resultado_acao)
                continue 
            # -------------------------------
                
            # Se NÃO foi uma automação, ele manda para o Cérebro conversar
            resposta = pensar(texto_usuario)
            print(f"\n[AVALON]: {resposta}")
            falar(resposta)
            
        except KeyboardInterrupt:
            print("\n[AVALON] Desligamento forçado pelo teclado. Encerrando.")
            break
        except Exception as e:
            print(f"\n[AVALON] Erro no fluxo principal: {e}")

if __name__ == "__main__":
    iniciar_avalon()