import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

chave_api = os.getenv("NVIDIA_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=chave_api
)

# Arquivo físico onde a memória será guardada para sempre
MEMORIA_FILE = "memoria_avalon.json"

SYSTEM_PROMPT = {
    "role": "system", 
    "content": (
        "Você é o AVALON, uma inteligência artificial avançada de nível militar, de uso pessoal e secreto. "
        "Sua interface é um núcleo holográfico orbital rodando localmente com aceleração de hardware "
        "numa GPU NVIDIA RTX 3050. Seja sempre imersivo, extremamente inteligente, técnico e sofisticado. "
        "Responda em português e chame o usuário sempre de 'Mestre' ou 'Senhor'."
    )
}

def carregar_memoria_do_disco():
    """Busca o histórico salvo no SSD. Se não existir, inicia um novo."""
    if os.path.exists(MEMORIA_FILE):
        try:
            with open(MEMORIA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return [SYSTEM_PROMPT]
    return [SYSTEM_PROMPT]

def salvar_memoria_no_disco(historico):
    """Guarda a conversa atual no arquivo físico"""
    try:
        with open(MEMORIA_FILE, "w", encoding="utf-8") as f:
            json.dump(historico, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Erro ao gravar no disco: {e}")

# Inicializa o Avalon já carregando o passado
historico_conversa = carregar_memoria_do_disco()

def pensar(texto_usuario):
    global historico_conversa
    
    historico_conversa.append({"role": "user", "content": texto_usuario})
    
    # Mantém as últimas 18 mensagens para não estourar o limite de processamento
    if len(historico_conversa) > 20:
        historico_conversa = [historico_conversa[0]] + historico_conversa[-18:]

    try:
        completion = client.chat.completions.create(
            model="meta/llama-3.1-70b-instruct", 
            messages=historico_conversa,
            temperature=0.5,
            max_tokens=768
        )
        
        resposta = completion.choices[0].message.content
        historico_conversa.append({"role": "assistant", "content": resposta})
        
        # SALVAMENTO EM TEMPO REAL: Respondeu? Grava no HD!
        salvar_memoria_no_disco(historico_conversa)
        
        return resposta
        
    except Exception as e:
        if historico_conversa[-1]["role"] == "user":
            historico_conversa.pop()
        return f"Erro na rede neural: {str(e)}"

def limpar_memoria():
    """Zera o arquivo e apaga as lembranças do Avalon"""
    global historico_conversa
    historico_conversa = [SYSTEM_PROMPT]
    salvar_memoria_no_disco(historico_conversa)
    return "Protocolo de limpeza executado. Memória física redefinida, Mestre."