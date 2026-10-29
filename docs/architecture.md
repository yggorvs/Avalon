# Arquitetura

`UI/CLI → fila de tarefas → Controller → Router/Executor ou LanguageModel → Memory`

- `config.py`: configuração imutável; sem credenciais globais.
- `controller.py`: um único worker, fila limitada, eventos para apresentação e encerramento cooperativo.
- `commands.py`: reconhecimento de frases completas; aplicativos em allowlist, sem shell arbitrário.
- `memory.py`: SQLite com transações, lock e retenção de turnos completos; notas e tarefas em tabelas próprias.
- `llm.py`: cliente carregado sob demanda, timeout e retry limitados; prompt honesto sobre capacidades.
- `audio.py`: microfone e Whisper carregados sob demanda; temporários exclusivos; TTS serializado.
- `ui.py`: somente a thread principal toca widgets; eventos via Queue/after.
- `__main__.py`: composição, CLI e diagnóstico.

## Extensão

Uma nova habilidade começa no Router e no Executor, com testes de interpretação e do efeito.
Para integrar Home Assistant, criar um adaptador específico, credenciais próprias e comandos com
entidades permitidas. Dispositivos sensíveis precisam confirmação e identidade apropriadas.
A IA não deve ganhar execução de shell livre. Adaptadores podem substituir `reply`, `listen`, `speak`
e `execute`; os testes demonstram injeção sem bibliotecas de hardware.

## Estado e concorrência

O worker serializa tarefas. O modo contínuo captura áudio apenas quando não há tarefa enfileirada.
Não há thread adicional para wake word; assim botão e vigilante nunca acessam o microfone juntos.
A interface pode enfileirar no máximo oito tarefas. Desativar voz descarta captura passiva ainda em curso.
Texto já enfileirado pode aguardar a captura terminar. Encerramento descarta tarefas pendentes,
aguarda operação atual e fecha recursos no worker. O Tk continua processando eventos nesse período.

## Agente de computador (2.1)

`Controller → Agent → LanguageModel.tool_turn → ComputerTools → Approvals → UI/CLI`

O modo agente usa chamadas estruturadas de funções, validação local, limites de etapas/prazo e
resultados observáveis. Aprovações são resolvidas fora do modelo e vinculadas a um identificador único.
`ComputerTools` aplica raízes e bloqueios de credenciais para arquivos; comandos aprovados de terminal
não são sandboxados. `PARAR TAREFA` usa um evento separado do encerramento da aplicação.
Veja docs/agent.md para capacidades, dados enviados ao modelo e limites reais de interrupção.
