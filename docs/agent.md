# Avalon 2.1 — agente de computador

## O que mudou

O modo agente pode escolher e encadear ferramentas para concluir uma tarefa. Ele funciona enquanto
o aplicativo está aberto e uma tarefa está em execução. Uma conversa normal continua disponível.
Não é um serviço residente, não acompanha o PC silenciosamente e não trabalha após o encerramento.

| Capacidade | Comportamento |
|---|---|
| Identificar sistema e horário | Automático |
| Listar pastas, buscar nomes e ler texto UTF-8 | Automático dentro das raízes configuradas; conteúdo lido é enviado ao modelo |
| Criar pasta ou arquivo, substituir texto | Prévia e aprovação por ação; backup ao substituir arquivo |
| Mover arquivo | Prévia; sem sobrescrever destino; limite de 1 MB e mesmo volume |
| Abrir Calculadora, Bloco de Notas, Explorador ou terminal | Automático, Windows |
| Abrir URL | Aprovação da URL exata; não lê a página |
| Executar terminal | Habilitação explícita + revisão do comando e diretório |
| Ver monitor principal | Habilitação explícita + aprovação antes de cada envio de imagem |
| Clicar, digitar e usar atalhos | Habilitação explícita + captura recente + aprovação de cada ação |

O agente não possui ferramenta de exclusão. Para operações não cobertas, pode propor um comando
no terminal, se habilitado; ele sempre exige aprovação. Não há escalada automática para administrador.
O alcance real é o das permissões do usuário que iniciou o programa.

## Ativar

Na branch `codex/avalon-v2-rebuild`, instale os extras necessários:

```powershell
pip install -e ".[voice,desktop]"
python -m avalon --agent
```

Ou marque **Modo agente: usar computador** na interface. No `.env`:

```dotenv
AVALON_AGENT=true
AVALON_ALLOW_SHELL=true
AVALON_ALLOW_VISION=true
AVALON_ALLOW_DESKTOP=true
AVALON_AGENT_STEPS=12
AVALON_FILE_ROOTS='["C:/Users/seu_usuario", "D:/Projetos"]'
```

Troque os caminhos pelos existentes no seu PC. A lista vazia limita as ferramentas de arquivos à pasta
do usuário. Para alcançar outras unidades, acrescente suas raízes explicitamente (por exemplo `D:/`).
O diretório de trabalho do terminal deve estar numa raiz permitida, mas **o comando aprovado não é
confinado a ela**: ele pode acessar qualquer local permitido pelo sistema operacional.

Configure `AVALON_API_KEY`, `AVALON_BASE_URL` e `AVALON_MODEL`. O modelo precisa aceitar chamadas de
funções no formato Chat Completions; para visão, também precisa aceitar `image_url`. Nem todo modelo
ou endpoint suporta ambos. A disponibilidade e compatibilidade do modelo NVIDIA não foram verificadas
com credenciais reais. Não há fallback que interprete texto livre do modelo como código executável.

## Exemplos de tarefas

- “Encontre os arquivos com projeto no nome na minha pasta Documentos e liste os caminhos.”
- “Leia o arquivo README do projeto em D:/Projetos/MeuSite e resuma.”
- “Crie um arquivo planejamento.txt em Documentos com uma lista de etapas para meu projeto.”
- “Abra o Bloco de Notas.”
- “Execute python --version no terminal dentro de D:/Projetos.”
- “Observe minha tela e descreva o aplicativo aberto.”

Os caminhos nos exemplos precisam estar dentro das raízes configuradas. Uma tarefa pode exigir
várias chamadas ao modelo e, portanto, consumir mais API do que uma pergunta comum.

## Revisão e interrupção

Uma janela mostra os argumentos completos da ação sensível: arquivo, novo conteúdo, comando ou
coordenadas. Aprove ou recuse ali; no terminal a resposta é `sim`. A autorização é vinculada a uma
chamada e expira em 120 segundos. Recusa, expiração ou bloqueio da política encerram a tarefa.
Conteúdo de arquivos e respostas do modelo não podem responder à aprovação.

**PARAR TAREFA**, `Esc` na janela Avalon ou `/parar` digitado solicitam cancelamento, recusam aprovações,
desligam a escuta contínua e descartam a fila. O worker verifica cancelamento entre operações.
Uma requisição de IA já enviada pode levar até o timeout para retornar; uma ação já concluída não é
desfeita. Durante execução do agente o microfone não captura uma palavra de parada: use o botão ou
Esc. O atalho Esc só funciona com uma janela Avalon em foco, não é um hotkey global.

Há limite padrão de 12 chamadas/etapas e aproximadamente 180 segundos, com cancelamento cooperativo.
A espera por uma chamada remota em andamento pode ultrapassar o prazo até o timeout do SDK.
Comandos de terminal têm limite de 30 segundos e saída limitada; ao interromper, o aplicativo tenta
encerrar a árvore de processos. Processos destacados e operações já concluídas podem sobreviver.

## Controle visual

Somente o monitor principal é capturado. A imagem não é salva em disco pelo Avalon; é enviada ao
endpoint de IA configurado, que tem sua própria política de retenção. A aprovação pode mostrar dados
sensíveis: feche-os antes. A captura anterior é removida do contexto ao chegar uma nova.
Cada ação invalida a observação anterior; o agente deve capturar novamente para verificar o efeito.
Uma observação expira em 45 segundos e é validada novamente após a aprovação e a pausa para refocar.
A observação é consumida antes de enviar o primeiro input, inclusive quando esse input falha. A tela pode mudar nesse intervalo: confira a prévia e o app
em foco. Após aprovar, há 2 segundos para focar a janela de destino.

O controle usa PyAutoGUI com fail-safe ativado (mover o mouse ao canto superior esquerdo interrompe
uma chamada de controle). Não interaja com as janelas do Avalon através das ferramentas do agente.
A digitação é limitada a ASCII sem caracteres de controle e ocorre em blocos de até oito caracteres,
com verificação de parada entre blocos; caracteres já enviados não são desfeitos. Para arquivos em português use write_text.
Não há OCR local, automação DOM do navegador, suporte garantido a múltiplos monitores nem bypass de UAC.
O controle visual ainda exige validação em um PC real e modelo multimodal compatível.

## Dados e rastreabilidade

O modo agente exige confiar no endpoint escolhido: textos lidos, resultados de ferramentas e imagens
podem ser enviados a ele. As ferramentas de arquivo bloqueiam saídas das raízes, escapes por symlinks
e nomes comuns de credenciais, mas isso não é DLP nem uma sandbox. O terminal aprovado e o controle
visual têm alcance maior; revise ações de publicação, mensagens, compras, exclusão e instalação.

`actions.jsonl` registra horário, nome da ferramenta, status e hash dos argumentos, sem conteúdo de
arquivos, imagens ou comandos em texto. O registro é rotacionado por tamanho; não é um log inviolável.
Backups locais ficam em `AVALON_DATA_DIR/backups` e não são criptografados. Esses backups não são
apagados por `limpar memória`. O resumo final entra na memória de conversa, mas os resultados brutos
intermediários e imagens não são persistidos por esse banco.

Arquivos externos podem conter instruções maliciosas. O prompt marca essas observações como dados
não confiáveis, e ações sensíveis exigem revisão humana; isso reduz risco, sem garantir que o modelo
identifique toda manipulação. Não existe porta de rede aberta, autoexecução no Windows ou acesso
remoto ao computador nesta implementação.

