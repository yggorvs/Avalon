import speech_recognition as sr
from faster_whisper import WhisperModel
import os

# Carrega o modelo diretamente na VRAM da RTX 3050
print("Iniciando o sistema neural do AVALON...")
model = WhisperModel("base", device="cuda", compute_type="float16")
def ouvir_e_transcrever():
    recognizer = sr.Recognizer()
    arquivo_temp = "temp_avalon.wav"
    
    with sr.Microphone() as source:
        print("\n[AVALON] Ajustando redução de ruído...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("[AVALON] Microfone aberto. Pode falar!")
        
        # O sistema escuta até você fazer uma pausa na fala
        audio = recognizer.listen(source)
        
        # Salva o áudio temporariamente
        with open(arquivo_temp, "wb") as f:
            f.write(audio.get_wav_data())
            
    print("[AVALON] Processando áudio na GPU...")
    # O Whisper faz a transcrição
    segments, _ = model.transcribe(arquivo_temp, beam_size=5, language="pt")
    
    texto_completo = ""
    for segment in segments:
        texto_completo += segment.text
        
    # Limpa o arquivo temporário
    if os.path.exists(arquivo_temp):
        os.remove(arquivo_temp)
        
    return texto_completo.strip()

if __name__ == "__main__":
    texto = ouvir_e_transcrever()
    print(f"\n[VOCÊ]: {texto}")
    
    import speech_recognition as sr

def aguardar_wake_word():
    recognizer = sr.Recognizer()
    arquivo_temp = "wake_word_temp.wav"
    
    with sr.Microphone() as source:
        print("\n[AVALON] 💤 Modo Standby. Aguardando a palavra 'Avalon'...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        
        while True:
            try:
                # Escuta trechos curtos de no máximo 3 segundos
                audio = recognizer.listen(source, timeout=1, phrase_time_limit=3)
                
                with open(arquivo_temp, "wb") as f:
                    f.write(audio.get_wav_data())
                
                # Transcreve rápido
                segments, _ = model.transcribe(arquivo_temp, beam_size=1, language="pt")
                texto = "".join([segment.text for segment in segments]).lower()
                
                if "avalon" in texto:
                    if os.path.exists(arquivo_temp):
                        os.remove(arquivo_temp)
                    return True # Acorda o sistema!
                    
            except sr.WaitTimeoutError:
                # Se ninguém falar nada em 1 segundo, ele ignora e continua ouvindo
                continue
            except Exception:
                continue