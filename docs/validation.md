# Validação da reconstrução

Executado no ambiente de desenvolvimento em 29/10/2026:

- `python -m unittest discover -s tests -v`: 21 testes aprovados.
- `python -m compileall -q avalon tests`: sem erros de sintaxe.
- `python -m pip install -e . --no-deps --no-build-isolation`: pacote instalável em modo editável.
- `python -m avalon --doctor`: diagnóstico funciona sem bibliotecas opcionais e sem chave.
- Smoke test do terminal com `que horas são` e `/sair`: resposta local e encerramento concluídos.

Cobertura funcional: correspondência estrita de comandos, negações, parâmetros de URL, falha do
navegador, persistência SQLite, orçamento de contexto, retenção, notas e tarefas, falhas de IA sem
turnos parciais, confirmação de exclusão e expiração, captura serializada, wake word com comando,
fila limitada, encerramento cooperativo, inicialização preguiçosa, fallback CUDA/CPU,
limpeza de temporários em erro e montagem de contexto do adaptador de IA.

Não validado neste ambiente: abertura/renderização da janela Tk, captura de microfone real,
saída de áudio, Edge TTS remoto, GPU/CUDA, instalação das dependências de voz, autenticação e
respostas do modelo NVIDIA, aplicativos Windows e execuções do workflow GitHub Actions.
As dependências remotas não foram instaladas durante este teste; adaptadores foram simulados.
Não existem medições de desempenho ou garantia de disponibilidade do modelo remoto.

## Aceitação no computador do autor

1. Instalar conforme README e preencher `.env`; executar `python -m avalon --doctor`.
2. Abrir GUI, enviar `ajuda`, registrar nota e tarefa, fechar e reabrir; listar os registros.
3. Testar uma conversa com IA e continuidade após reiniciar.
4. Testar Ouvir, voz contínua e `Avalon, que horas são?`; desativar voz contínua.
5. Testar voz sintetizada, botão Interromper fala e fechamento durante captura.
6. Confirmar que `Quero ouvir sua opinião` não abre música e que negar limpeza não apaga dados.
7. Testar CPU e, com bibliotecas NVIDIA corretas, GPU; comparar latência.
8. Verificar falhas sem chave, sem rede e sem dispositivo de áudio; texto e comandos devem continuar utilizáveis.

Referências de adaptadores: [Faster Whisper](https://github.com/SYSTRAN/faster-whisper),
[SDK OpenAI](https://github.com/openai/openai-python),
[Edge TTS](https://github.com/rany2/edge-tts).
