from .errors import ConfigurationError

SYSTEM = """Você é Avalon, um assistente pessoal. Responda em português com clareza,
precisão e cordialidade. Admita incertezas. Não afirme que pesquisou, executou ações,
acessou arquivos ou controla dispositivos: você gera texto e não possui ferramentas.
Não invente resultados de ações nem informações atuais. Pergunte quando faltar contexto.
Não descreva a interface como holograma físico ou IA local: a inferência usa o endpoint configurado."""

class LanguageModel:
    def __init__(self, settings):
        self.settings = settings
        self.client = None

    def reply(self, context, text):
        if not self.settings.api_key:
            raise ConfigurationError("Configure AVALON_API_KEY no .env. Os comandos locais continuam disponíveis.")
        if self.client is None:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.settings.api_key, base_url=self.settings.base_url,
                                 timeout=25.0, max_retries=1)
        result = self.client.chat.completions.create(
            model=self.settings.model, messages=[{"role": "system", "content": SYSTEM},
            *context, {"role": "user", "content": text}], temperature=0.4, max_tokens=1000)
        text = result.choices[0].message.content
        if not text or not text.strip():
            raise RuntimeError("O provedor retornou uma resposta vazia.")
        return text.strip()

    def close(self):
        if self.client:
            self.client.close()
