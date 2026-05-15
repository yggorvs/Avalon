import os
from openai import OpenAI
from dotenv import load_dotenv

# Carrega as variáveis de ambiente (sua chave secreta)
load_dotenv()

# Conecta aos servidores da NVIDIA
client = OpenAI(
  base_url = "https://integrate.api.nvidia.com/v1",
  api_key = os.getenv("NVIDIA_API_KEY")
)

def pensar(mensagem_usuario):
    print("\n[AVALON] Consultando núcleo de processamento...")
    
    # Você pode trocar o modelo depois se quiser (ex: Mixtral, Gemma)
    # Mas o Llama 3 70B costuma ser excelente e rápido.
    completion = client.chat.completions.create(
      model="meta/llama-3.1-70b-instruct", 
      messages=[
        {"role": "system", "content": "Você é o AVALON, uma inteligência artificial avançada de automação residencial. Suas respostas devem ser curtas, diretas e levemente sarcásticas, como um mordomo digital altamente eficiente."},
        {"role": "user", "content": mensagem_usuario}
      ],
      temperature=0.5,
      max_tokens=512,
    )
    
    return completion.choices[0].message.content

if __name__ == "__main__":
    # Teste isolado do Cérebro
    resposta = pensar("Olá AVALON, os seus sistemas estão online?")
    print(f"\n[AVALON]: {resposta}")