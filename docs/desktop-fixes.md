# Correções antes da nova interface

Este incremento mantém a interface atual. A bolinha flutuante e seus sprites não fazem parte dele.

## Capturas de tela

- `None` indica que não existe uma observação; zero continua sendo um horário válido de captura.
- A observação precisa ter entre zero e 45 segundos antes da aprovação, depois dela e após a pausa para refocar.
- Uma observação ausente ou expirada bloqueia a ação e encerra o agente, sem tentar outra ferramenta.
- A observação é consumida antes do primeiro input, inclusive se o driver falhar após um efeito parcial.

Os testes usam relógio controlado: incluem o caso que falhou na CI quando o relógio monotônico estava
abaixo de 45 segundos e a captura que expira enquanto o usuário revisa a ação.

## Digitação e parada

A digitação é dividida em blocos de até oito caracteres. O cancelamento é verificado antes de cada
bloco e após o último. Se houver parada, o resultado informa quantos caracteres foram enviados.
Caracteres já digitados não são desfeitos. O atraso do bloco atual e do driver continua existindo;
não há promessa de cancelamento instantâneo ou de um atalho Esc global.

## Interface e CI

Há cinco smoke tests usando Tk real: eventos e envio de mensagens, aprovação/recusa pelo broker real,
acesso ao botão de parada sem diálogo modal, preservação de foco durante animação e encerramento
com uma aprovação pendente. Timers de animação e de eventos são cancelados ao destruir a janela.

A CI executa os smoke tests com Xvfb no Linux e com Tk no Windows, em Python 3.11 e 3.12.
`AVALON_REQUIRE_GUI=1` transforma ausência de display em falha, evitando um resultado verde obtido
somente por pular os testes. A matriz usa `fail-fast: false` para obter o resultado de todas as plataformas.

Validação local: 55 testes aprovados; cinco testes de GUI pulados por ausência de display.
Compilação de `avalon` e `tests` sem erros. A validação da GUI depende da execução correspondente da CI.
Os testes não usam API, microfone, mouse ou teclado reais do usuário. Testes de input de desktop usam
adaptadores simulados; os testes de terminal existentes executam somente um comando inofensivo local.

Isso não valida transparência, drag-and-drop ou sprites da futura interface; essas verificações pertencem
à integração posterior. O foco da janela de destino do agente ainda precisa ser conferido pelo usuário,
conforme o guia do agente; a validade temporal da captura não garante que a tela permaneceu igual.
