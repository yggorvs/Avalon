# AVALON 2.2

Assistente pessoal desktop em português, reconstruído com núcleo modular, texto e voz,
comandos explícitos, memória SQLite e interface dourada/verde.


## Bolinha flutuante

A interface abre como um núcleo dourado em pixel art, com raios verdes e vermelhos, sempre visível
sobre as janelas normais. Arraste para mover; clique para conversar; clique duas vezes para ouvir;
botão direito abre opções, tamanho, parada e saída. Fechar a conversa mantém a bolinha ativa.
Aprovações de ações continuam em uma janela própria. Veja o [guia da bolinha](docs/floating-orb.md).

## Agente de computador

A nova versão também pode planejar e executar tarefas com ferramentas locais: listar e ler arquivos,
criar/substituir texto com backup, mover arquivos, abrir apps, executar terminal e observar/interagir
com o monitor principal. Ative com `python -m avalon --agent` ou pelo botão da interface.
Ferramentas de terminal e tela exigem configuração adicional, e ações sensíveis exibem aprovação.
Use **PARAR TAREFA** para interromper. Leia o [guia do agente](docs/agent.md) antes de habilitar tela e terminal.

## Instalação no Windows (Python 3.11 ou 3.12)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[voice]"
Copy-Item .env.example .env
notepad .env
python -m avalon
```

Preencha `AVALON_API_KEY` e confira `AVALON_MODEL` no catálogo do seu provedor.
A chave antiga `NVIDIA_API_KEY` também é aceita. Nenhuma chave é incluída no projeto.
Não cole credenciais no chat. O endpoint deve ser confiável: recebe a chave e as mensagens.

Instalação apenas para texto: `pip install -e .`. Terminal: `python -m avalon --cli`.
Diagnóstico sem rede/hardware: `python -m avalon --doctor`.
O Python precisa incluir Tk para a interface. No Linux, Tk e PortAudio podem exigir pacotes do sistema;
use o terminal se Tk não estiver disponível. Aplicativos locais são configurados para Windows.

## Voz

Clique em **Ouvir um comando**. A fala é limitada a 12 segundos, com espera de 2 segundos
pelo início. O carregamento inicial do Whisper pode baixar o modelo e levar tempo.
Ative **voz contínua** para dizer `Avalon` e iniciar uma conversa; diga `dormir` para sair.
`Avalon, que horas são?` funciona em uma única frase. A detecção espera Avalon no começo da fala.
A voz contínua vem desligada e não é identificação biométrica: qualquer pessoa próxima pode ativá-la.
A alternativa sem microfone é digitar na caixa de conversa.

`AVALON_DEVICE=auto` tenta CUDA e retorna à CPU se a inicialização falhar.
Use `cpu` para evitar a tentativa ou `cuda` para exigir GPU. CUDA depende de bibliotecas
NVIDIA compatíveis com CTranslate2; consulte [Faster Whisper](https://github.com/SYSTRAN/faster-whisper#gpu).
Uma falha durante a transcrição é exibida; o fallback automático cobre a inicialização do modelo.

**Ler respostas** usa Edge TTS pela internet. A transcrição Whisper é local; a IA usa o endpoint
configurado (NVIDIA por padrão). É possível usar um servidor local compatível com Chat Completions
alterando URL, modelo e chave conforme o servidor. Esse modo não foi validado aqui.
A interface é uma animação Canvas; não é um holograma físico nem um renderizador 3D por CUDA.

## Comandos disponíveis

- `abrir google`, `abrir youtube`, `abrir github`
- `pesquisar no google sobre engenharia da computação`
- `pesquisar no youtube sobre Python`
- `tocar nome da música` — abre resultados do YouTube Music; não inicia reprodução
- `abrir calculadora`, `abrir bloco de notas`, `abrir terminal` — Windows
- `que horas são`, `que dia é hoje`
- `limpar memória` seguido de `confirmar` em 30 segundos; `cancelar` cancela
- `salvar nota <texto>`, `listar notas` (até 50 notas mais recentes)
- `adicionar tarefa <texto>`, `listar tarefas`, `concluir tarefa <número>` (até 50 pendências)
- `dormir`, `encerrar conversa`, `desligar o sistema` (fecha o aplicativo)

Perguntas comuns vão para a IA. No modo conversa, somente o roteador local executa os comandos acima. No modo agente, o modelo
pode propor ferramentas estruturadas; o aplicativo valida os argumentos e as aprovações antes de
executar. Há leitura de arquivos e terminal opcional. Controle residencial e busca com leitura da web
ainda não foram implementados.

## Memória e privacidade

Somente turnos de conversa concluídos com a IA são persistidos, em `~/.avalon/memory.sqlite3`.
O contexto usa até 10 turnos e 18 mil caracteres; o banco retém os últimos 500 turnos.
Comandos locais não entram no histórico de conversa. Notas e tarefas são armazenadas em tabelas próprias,
não são enviadas automaticamente à IA e não têm lembretes agendados. `limpar memória` apaga somente a
conversa; notas e tarefas permanecem. Para remover todos os dados, feche o Avalon e remova o banco local. Defina `AVALON_DATA_DIR` para mudar o diretório.
Os arquivos são locais e **não criptografados**; o contexto recente é enviado ao endpoint de IA.
A interface exibe a conversa da sessão atual; o contexto de sessões anteriores continua disponível para a IA.

A memória JSON antiga não é importada automaticamente. A conversa anteriormente publicada foi removida
da nova árvore, mas continua no histórico anterior do Git. Reescrever esse histórico exige uma operação separada.

## Qualidade e limites

```powershell
python -m unittest discover -s tests -v
python -m compileall -q avalon
```

Testes usam serviços simulados e SQLite real, sem microfone, navegador ou API reais.
CI configurada para Windows/Linux e Python 3.11/3.12. Dependências têm faixas de compatibilidade;
não há lockfile de ambiente reproduzível nem distribuição executável nesta versão.

Cancelar fala não cancela uma requisição já enviada ao provedor. Fechar a janela aguarda a
operação atual: captura tem limites, mas carregamento inicial do modelo e drivers externos podem demorar.
Erros técnicos são resumidos na interface; logs não incluem texto de conversa, chaves ou payloads remotos.
Não há pesquisa com leitura da web: abrir URLs não é ler fontes. O modo agente pode observar dados locais
atuais usando ferramentas; ele depende de um modelo compatível com function calling e, para tela, visão.

Veja [arquitetura](docs/architecture.md), [validação](docs/validation.md) e [próximas etapas](docs/roadmap.md).
O projeto não recebeu uma nova licença nesta reconstrução; os termos de distribuição devem ser definidos pelo autor.

