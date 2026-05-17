import os
import webbrowser
import subprocess

def verificar_e_executar(texto):
    """
    Motor de automação flexível. Identifica palavras-chave centrais
    e executa ações locais ou comandos de mídia na Web.
    """
    texto = texto.lower().strip()
    
    # Remove pontuações que o Whisper joga no fim das frases para não quebrar a lógica
    texto = texto.replace(".", "").replace("!", "").replace("?", "").replace(",", "")
    
    # ---------------------------------------------------------
    # 1. SISTEMA DE PLAYER DE MÚSICA (YouTube Music)
    # ---------------------------------------------------------
    # Captura variações como: "tocar [artista]", "tocar musica de [artista]", "ouvir [musica]"
    if "tocar" in texto or "ouvir" in texto or "coloque" in texto:
        busca_musica = texto
        
        # Lista de termos comuns que o usuário fala antes do nome do artista/música
        gatilhos_remover = [
            "tocar música de", "tocar musica de", "tocar a música", "tocar a musica", "tocar",
            "ouvir música de", "ouvir musica de", "ouvir a música", "ouvir a musica", "ouvir",
            "coloque para tocar", "coloque a música", "coloque a musica", "coloque"
        ]
        
        # Limpa a frase para isolar apenas o nome do cantor ou da música
        for gatilho in gatilhos_remover:
            if gatilho in busca_musica:
                # Substitui apenas a primeira ocorrência do gatilho para não estragar nomes de músicas
                busca_musica = busca_musica.replace(gatilho, "", 1).strip()
                break
        
        # Se restou um nome válido após a limpeza, envia para o YouTube Music
        if busca_musica:
            # A URL do YouTube Music com '/search?q=' abre direto na central de áudio do artista
            webbrowser.open(f"https://music.youtube.com/search?q={busca_musica}")
            return f"Iniciando os sistemas de áudio. Buscando por '{busca_musica}' no YouTube Music Mestre."

    # ---------------------------------------------------------
    # 2. ECOSSISTEMA YOUTUBE TRADICIONAL (Vídeos)
    # ---------------------------------------------------------
    if "youtube" in texto:
        if "pesquisar" in texto or "pesquise" in texto or "procure" in texto or "buscar" in texto:
            for gatilho in ["por ", "sobre ", "youtube "]:
                if gatilho in texto:
                    busca = texto.split(gatilho)[-1].strip()
                    webbrowser.open(f"https://www.youtube.com/results?search_query={busca}")
                    return f"Efetuando busca por vídeo de '{busca}' no YouTube."
            
            busca = texto.replace("pesquisar", "").replace("youtube", "").replace("no", "").strip()
            webbrowser.open(f"https://www.youtube.com/results?search_query={busca}")
            return f"Buscando por '{busca}' no YouTube Senhor."
        else:
            webbrowser.open("https://www.youtube.com")
            return "Conectando aos servidores do YouTube. Concluído."

    # ---------------------------------------------------------
    # 3. ECOSSISTEMA GOOGLE (Pesquisas Gerais)
    # ---------------------------------------------------------
    if "google" in texto:
        if "pesquisar" in texto or "pesquise" in texto or "procure" in texto:
            for gatilho in ["por ", "sobre "]:
                if gatilho in texto:
                    busca = texto.split(gatilho)[-1].strip()
                    webbrowser.open(f"https://www.google.com/search?q={busca}")
                    return f"Pesquisando por '{busca}' no Google Mestre."
        else:
            webbrowser.open("https://www.google.com")
            return "Abrindo o Google."

    # ---------------------------------------------------------
    # 4. OUTROS SITES E APLICATIVOS LOCAIS
    # ---------------------------------------------------------
    if "github" in texto:
        webbrowser.open("https://github.com")
        return "Abrindo sua central do GitHub."

    if "bloco de notas" in texto or "notepad" in texto:
        subprocess.Popen("notepad.exe")
        return "Identalizando Bloco de Notas local."

    if "calculadora" in texto:
        subprocess.Popen("calc.exe")
        return "Calculadora ativa."

    if "cmd" in texto or "prompt de comando" in texto or "terminal" in texto:
        subprocess.Popen("cmd.exe")
        return "Acessando o terminal do Windows."

    # ---------------------------------------------------------
    # 5. RESET DE MEMÓRIA FISCA
    # ---------------------------------------------------------
    if "limpar memória" in texto or "esqueça o que conversamos" in texto or "esquecer tudo" in texto:
        from cerebro import limpar_memoria
        return limpar_memoria()

    return None