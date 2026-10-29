# Próximas etapas

1. Validar no PC do autor: Windows, microfone, NVIDIA, disponibilidade do modelo e Edge TTS.
2. Medir latência de captura/transcrição/LLM/voz antes de escolher um detector de wake word dedicado.
3. Adicionar streaming de texto, interrupção de inferência e configurações editáveis pela interface.
4. Criar integração Home Assistant com escopo de entidades e confirmação por tipo de ação.
5. Adicionar busca web com fontes e memória de preferências explicitamente autorizada.
6. Preparar instalador assinado, lockfiles por plataforma e política de atualização.

Itens desta lista ainda não foram implementados. O núcleo atual é uma base funcional para evolução,
não uma declaração de que todas as capacidades de um assistente geral já existem.

## Depois do modo agente 2.1

- Validar controle de desktop e function calling no Windows do autor com modelo real.
- Automatizar navegador por DOM, com perfis e consentimento por ação externa.
- Identificar janelas e restaurar foco com APIs de acessibilidade do Windows.
- Detector de wake word dedicado e parada por voz durante a execução.
- Confinamento de processos para trabalhos de código e rollback mais abrangente.
