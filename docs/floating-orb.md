# Avalon 2.2 — bolinha flutuante

A interface principal agora é um núcleo dourado em pixel art, sem borda, sempre sobre as janelas
normais do desktop. A conversa e os controles aparecem somente quando solicitados. O programa não
inicia automaticamente com o Windows nem permanece ativo depois de escolher Sair.

## Controles

| Gesto | Ação |
|---|---|
| Arrastar com botão esquerdo | Mover a bolinha |
| Um clique | Abrir o painel de conversa |
| Dois cliques | Ouvir um comando pelo microfone |
| Botão direito | Menu de voz, agente, tamanho, animação, parada e saída |
| Quadrado vermelho, visível ao passar o mouse | Parar a tarefa atual |
| Esc, com uma janela Avalon em foco | Parar a tarefa atual |
| Fechar o painel de conversa | Esconder o painel e manter a bolinha |
| Menu → Sair do Avalon | Encerrar o programa de forma cooperativa |

O botão de parada também fica visível durante uma aprovação. A janela de aprovação abre sobre as
outras janelas mesmo com a conversa fechada e mantém Recusar, Aprovar e PARAR TAREFA. O cancelamento,
a validação de captura e a digitação interrompível da versão 2.1 continuam no backend.

## Animações

- Repouso: núcleo dourado com pequenas faíscas.
- Escuta: raios verdes.
- Processamento e fala: raios verdes e vermelhos.
- Erro ou aprovação pendente: raios vermelhos; o alerta não substitui a revisão escrita.

O atlas contém 16 quadros (quatro por linha), em PNG RGBA, empacotado junto do módulo. Os quadros são
renderizados com nearest-neighbor e máscara de pixels, sem borrar a arte. Os estados de processamento
e fala compartilham a terceira linha, com ritmos diferentes. O menu permite desativar animações.

## Tamanho e posição

Pequena: 96 pixels; normal: 144; grande: 192. Posição, tamanho e preferência de animação são salvos em
`AVALON_DATA_DIR/overlay.json`. As coordenadas são limitadas à tela principal e reajustadas se a resolução
mudar. O menu permite reposicionar no canto. Não há navegação garantida por múltiplos monitores.

A transparência de fundo usa a chave de cor do Tk no Windows. Em outros sistemas ou se a chave não
for suportada, há fundo escuro. A opção topmost não garante sobreposição em jogos de tela cheia
exclusiva, telas protegidas de UAC ou desktops de segurança.

## Instalação e validação

Atualize a instalação do projeto com `pip install -e .` (ou `pip install -e ".[voice,desktop]"` para voz
e ferramentas visuais) e execute `python -m avalon`. Pillow agora é dependência básica e os assets
estão incluídos no pacote. Não há download de imagens durante a execução.

Os testes incluem estados/temporização de sprites, preferências, transparência RGBA, arraste com
limites, redimensionamento, clique duplo, foco durante animação, histórico com painel escondido,
limpeza de memória, aprovações reais pelo broker e encerramento dos timers.
A CI exige Tk real no Windows e Xvfb no Linux. Testes de GUI não precisam de chave de API, microfone
nem controle de mouse real. Isso não substitui a validação manual no desktop do autor, especialmente
escala de DPI, múltiplos monitores e tela cheia.

No modo agente, a bolinha pode aparecer em capturas de tela. O agente não deve clicar nas próprias
janelas; confira as coordenadas e o aplicativo de destino ao revisar ações de desktop. O widget não
cria um hotkey global de parada e não abre o microfone automaticamente.
