import edge_tts
import pygame
import asyncio
import os

# Inicializa o motor de áudio
pygame.mixer.init()

async def gerar_arquivo_audio(texto, arquivo_saida):
    # pt-BR-AntonioNeural é uma voz masculina muito natural.
    # Outra opção excelente é "pt-BR-FranciscaNeural"
    voz = "pt-BR-AntonioNeural" 
    comunicador = edge_tts.Communicate(texto, voz)
    await comunicador.save(arquivo_saida)

def falar(texto):
    arquivo_temp = "avalon_voz.mp3"
    
    # Executa a geração do áudio (que é assíncrona)
    asyncio.run(gerar_arquivo_audio(texto, arquivo_temp))
    
    # Carrega e toca o áudio
    pygame.mixer.music.load(arquivo_temp)
    pygame.mixer.music.play()
    
    # Mantém o script rodando enquanto o áudio toca
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
        
    # Descarrega o arquivo da memória e o apaga para não lotar o PC
    pygame.mixer.music.unload()
    if os.path.exists(arquivo_temp):
        os.remove(arquivo_temp)

if __name__ == "__main__":
    # Teste isolado das cordas vocais
    print("[AVALON] Iniciando teste de voz...")
    falar("Olá senhor. Meus sistemas vocais estão online e operantes.")
    print("[AVALON] Teste concluído.")