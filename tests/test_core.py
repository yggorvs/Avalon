from pathlib import Path
from tempfile import TemporaryDirectory
from queue import Empty
from threading import Event, Lock
import time
import unittest
from urllib.parse import urlparse, parse_qs
from avalon.commands import Router, Executor
from avalon.memory import Memory
from avalon.controller import Controller
from avalon.config import Settings
from avalon.llm import LanguageModel

class CommandTests(unittest.TestCase):
    def setUp(self): self.router = Router()
    def test_questions_and_negations_do_not_execute(self):
        for text in ('Quero ouvir sua opinião', 'Explique como funciona o terminal',
                     'Não quero limpar memória', 'não abrir google', 'como tocar violão?',
                     'o que significa github?', 'não desligar o sistema'):
            with self.subTest(text=text): self.assertIsNone(self.router.parse(text))
    def test_explicit_commands(self):
        for text, name in [('Limpar memória!', 'clear'), ('que horas são?', 'time'),
                           ('abrir terminal', 'open'), ('desligar o sistema', 'quit')]:
            self.assertEqual(self.router.parse(text).name, name)
    def test_search_escapes_parameters(self):
        urls=[]
        Executor(opener=lambda url: urls.append(url) or True).execute(
            self.router.parse('pesquisar no google sobre C++ & Python #1'))
        self.assertEqual(parse_qs(urlparse(urls[0]).query), {'q': ['C++ & Python #1']})
    def test_browser_failure_not_reported_as_success(self):
        with self.assertRaises(RuntimeError):
            Executor(opener=lambda url: False).execute(self.router.parse('abrir google'))

class MemoryTests(unittest.TestCase):
    def test_persistence_budget_and_clear(self):
        with TemporaryDirectory() as d:
            path=Path(d)/'memory.sqlite3'
            m=Memory(path); m.append('one','ONE'); m.append('two','TWO'); m.close()
            m=Memory(path)
            self.assertEqual([x['content'] for x in m.context()], ['one','ONE','two','TWO'])
            self.assertEqual([x['content'] for x in m.context(char_budget=6)], ['two','TWO'])
            m.clear(); self.assertEqual(m.context(), []); m.close()
    def test_retention(self):
        with TemporaryDirectory() as d:
            m=Memory(Path(d)/'memory.sqlite3')
            for i in range(505): m.append(str(i),'ok')
            self.assertEqual(len(m.context(turns=1000)),1000)
            self.assertEqual(m.context(turns=1000)[0]['content'],'5'); m.close()

class FakeLLM:
    def __init__(self): self.calls=[]; self.closed=False
    def reply(self,context,text):
        self.calls.append((context,text))
        if text=='falha': raise RuntimeError('secret-do-not-show')
        return 'Resposta: '+text
    def close(self): self.closed=True

class FakeAudio:
    def __init__(self):
        self.entered=Event(); self.release=Event(); self.closed=False
        self.active=0; self.max_active=0; self.lock=Lock(); self.transcript='que horas são'
    def listen(self,stop):
        with self.lock:
            self.active+=1; self.max_active=max(self.max_active,self.active)
        self.entered.set()
        while not self.release.wait(.01):
            if stop.is_set(): break
        with self.lock: self.active-=1
        return self.transcript
    def speak(self,text,stop): pass
    def interrupt(self): self.release.set()
    def close(self): self.closed=True

class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(); self.memory=Memory(Path(self.temp.name)/'memory.sqlite3')
        self.llm=FakeLLM(); self.audio=FakeAudio()
        self.c=Controller(self.memory,self.llm,self.audio)
    def tearDown(self):
        self.c.close(); self.c.thread.join(3)
        self.assertFalse(self.c.thread.is_alive()); self.temp.cleanup()
    def response(self,kind='assistant'):
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            try: event=self.c.events.get(timeout=.1)
            except Empty: continue
            if event[0]==kind: return event[1]
        self.fail('Timed out waiting for '+kind)
    def ask(self,text): self.c.submit(text); return self.response()
    def test_turns_and_failure_are_transactional(self):
        self.assertEqual(self.ask('olá'),'Resposta: olá')
        self.c.submit('falha'); self.assertNotIn('secret',self.response('error'))
        self.assertEqual(len(self.memory.context()),2)
        self.ask('outra pergunta'); self.assertEqual(len(self.llm.calls[-1][0]),2)
    def test_clear_needs_confirmation(self):
        self.ask('olá'); self.assertIn('confirmar',self.ask('limpar memória'))
        self.assertEqual(len(self.memory.context()),2)
        self.assertIn('apagado',self.ask('confirmar')); self.assertEqual(self.memory.context(),[])
    def test_unrelated_message_invalidates_confirmation(self):
        self.ask('olá'); self.ask('limpar memória'); self.ask('ajuda'); self.ask('confirmar')
        self.assertTrue(self.memory.context())
    def test_expired_confirmation(self):
        self.ask('olá'); self.ask('limpar memória'); self.c.pending_clear=time.monotonic()-1
        self.assertIn('expirada',self.ask('confirmar')); self.assertTrue(self.memory.context())
    def test_notes_tasks_stay_local(self):
        self.assertIn('Nota', self.ask('salvar nota Reunião na escola'))
        self.assertIn('Reunião na escola', self.ask('listar notas'))
        self.assertIn('Tarefa 1', self.ask('adicionar tarefa Revisar projeto'))
        self.assertIn('Revisar projeto', self.ask('listar tarefas'))
        self.assertIn('concluída', self.ask('concluir tarefa 1'))
        self.assertIn('Nenhum', self.ask('listar tarefas'))
        self.assertEqual(self.llm.calls, [])
        self.assertEqual(self.memory.context(), [])
    def test_local_command_does_not_call_llm(self):
        self.ask('que horas são'); self.assertEqual(self.llm.calls,[])
        self.assertEqual(self.memory.context(),[])
    def test_only_one_audio_owner(self):
        self.c.set_wake(True); self.assertTrue(self.audio.entered.wait(2))
        self.c.listen_once(); self.c.listen_once(); self.c.set_wake(False); self.audio.release.set()
        self.response(); self.response(); self.assertEqual(self.audio.max_active,1)
    def test_wake_word_and_command_in_one_utterance(self):
        self.audio.transcript='Avalon, que horas são?'
        self.c.set_wake(True); self.assertTrue(self.audio.entered.wait(2)); self.audio.release.set()
        self.assertIn('Agora são',self.response()); self.c.set_wake(False)
    def test_bounded_queue_and_shutdown(self):
        self.c.listen_once(); self.assertTrue(self.audio.entered.wait(2))
        for _ in range(8): self.assertTrue(self.c.submit('olá'))
        self.assertFalse(self.c.submit('excesso')); self.c.close(); self.c.thread.join(2)
        self.assertTrue(self.audio.closed); self.assertTrue(self.llm.closed); self.assertEqual(self.llm.calls,[])
    def test_missing_key_is_lazy(self):
        model=LanguageModel(Settings(data_dir=Path(self.temp.name)))
        self.assertIsNone(model.client)
        with self.assertRaisesRegex(RuntimeError,'AVALON_API_KEY'): model.reply([],'oi')

if __name__=='__main__': unittest.main()
