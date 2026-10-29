from dataclasses import replace
from pathlib import Path
from queue import Queue
from tempfile import TemporaryDirectory
from threading import Event, Thread
from types import SimpleNamespace
from unittest.mock import patch
import json
import sys
import time
import unittest
from avalon.agent import Agent, Turn
from avalon.approvals import Approvals
from avalon.computer import ComputerTools, Result
from avalon.config import Settings
from avalon.llm import LanguageModel

class ApprovalsTests(unittest.TestCase):
    def test_manual_answer_bound_to_id_and_first_answer(self):
        events=Queue(); result=[]
        broker=Approvals(lambda k,v:events.put((k,v)),timeout=2)
        thread=Thread(target=lambda:result.append(broker.ask('Action','preview',Event())))
        thread.start(); _,request=events.get(timeout=1)
        self.assertFalse(broker.resolve('wrong',True))
        self.assertTrue(broker.resolve(request['id'],True))
        self.assertFalse(broker.resolve(request['id'],False))
        thread.join(1); self.assertEqual(result,[True])
        self.assertFalse(broker.resolve(request['id'],True))
    def test_timeout_denies(self):
        broker=Approvals(lambda *args:None,timeout=.01)
        self.assertFalse(broker.ask('Action','preview',Event()))
    def test_cancel_denies(self):
        cancel=Event(); cancel.set()
        broker=Approvals(lambda *args:None)
        self.assertFalse(broker.ask('Action','preview',cancel))

class Decision:
    def __init__(self,allowed=True,hook=None): self.allowed=allowed; self.calls=[]; self.hook=hook
    def ask(self,title,preview,cancel):
        self.calls.append((title,preview))
        if self.hook: self.hook()
        return self.allowed

class ComputerTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(); self.root=Path(self.temp.name)
        self.files=self.root/'files'; self.files.mkdir()
        self.settings=Settings(self.root/'data',file_roots=(self.files,))
        self.approve=Decision(); self.tools=ComputerTools(self.settings,self.approve)
        self.cancel=Event()
    def tearDown(self): self.temp.cleanup()
    def call(self,name,**args): return self.tools.execute(name,args,self.cancel)
    def test_write_requires_review_and_backup(self):
        path=self.files/'draft.txt'; path.write_text('old')
        result=self.call('write_text',path=str(path),content='new')
        self.assertEqual(path.read_text(),'new')
        self.assertEqual(Path(result.data['backup']).read_text(),'old')
        preview=json.loads(self.approve.calls[0][1])
        self.assertEqual(preview['content'],'new'); self.assertEqual(preview['previous_text'],'old')
    def test_denied_write_has_no_effect(self):
        self.approve.allowed=False
        result=self.call('write_text',path='draft.txt',content='new')
        self.assertTrue(result.denied); self.assertFalse((self.files/'draft.txt').exists())
    def test_change_after_approval_is_detected(self):
        path=self.files/'draft.txt'; path.write_text('old')
        self.approve.hook=lambda:path.write_text('intervening edit')
        result=self.call('write_text',path=str(path),content='new')
        self.assertIn('error',result.data); self.assertEqual(path.read_text(),'intervening edit')
    def test_outside_root_and_sensitive_paths_stop_execution(self):
        for path in (str(self.root/'outside.txt'),'.env','.ssh/id_rsa','private.key'):
            with self.subTest(path=path):
                self.assertTrue(self.call('read_text',path=path).denied)
        self.assertEqual(self.approve.calls,[])
    def test_symlink_escape_blocked(self):
        outside=self.root/'secret.txt'; outside.write_text('secret')
        link=self.files/'shortcut.txt'
        try: link.symlink_to(outside)
        except OSError: self.skipTest('Symlinks unavailable on this account')
        self.assertTrue(self.call('read_text',path=str(link)).denied)
    def test_capabilities_not_exposed_when_disabled(self):
        names={s['function']['name'] for s in self.tools.schemas()}
        self.assertNotIn('run_terminal',names); self.assertNotIn('observe_screen',names)
        self.assertNotIn('desktop_click',names)
        with self.assertRaises(ValueError): self.call('run_terminal',command='echo test',cwd=str(self.files))
    def test_terminal_approval_exact_and_cancel(self):
        self.tools.settings=replace(self.settings,shell_enabled=True)
        self.approve.allowed=False
        with patch.object(self.tools,'_terminal') as terminal:
            result=self.call('run_terminal',command='echo test',cwd=str(self.files))
            self.assertTrue(result.denied); terminal.assert_not_called()
        preview=json.loads(self.approve.calls[-1][1])
        self.assertEqual(preview['command'],'echo test')
    def test_terminal_real_local_process(self):
        self.tools.settings=replace(self.settings,shell_enabled=True)
        command='Write-Output avalon-test' if sys.platform=='win32' else 'printf avalon-test'
        result=self.call('run_terminal',command=command,cwd=str(self.files))
        self.assertEqual(result.data['exit_code'],0); self.assertEqual(result.data['output'].strip(),'avalon-test')
    def test_move_never_overwrites_destination(self):
        source=self.files/'a.txt'; source.write_text('a')
        target=self.files/'b.txt'; target.write_text('b')
        result=self.call('move_file',source=str(source),destination=str(target))
        self.assertIn('error',result.data)
        self.assertEqual(target.read_text(),'b'); self.assertEqual(source.read_text(),'a')
    def test_move_and_find_read(self):
        (self.files/'a.txt').write_text('body')
        self.call('move_file',source='a.txt',destination='b.txt')
        self.assertEqual(self.call('read_text',path='b.txt').data['text'],'body')
        self.assertEqual(len(self.call('find_files',path='.',query='.txt').data['files']),1)
    def test_audit_has_no_plaintext_content(self):
        self.call('write_text',path='draft.txt',content='private-test-body')
        audit=(self.settings.data_dir/'actions.jsonl').read_text()
        self.assertNotIn('private-test-body',audit); self.assertNotIn('draft.txt',audit)
        self.assertIn('write_text',audit)
    def test_cancellation_before_execution(self):
        self.cancel.set()
        self.assertTrue(self.call('write_text',path='draft.txt',content='x').denied)
        self.assertFalse((self.files/'draft.txt').exists())
    def test_desktop_requires_recent_observation(self):
        self.tools.settings=replace(self.settings,desktop_enabled=True,vision_enabled=True)
        with patch.object(self.tools,'_desktop') as desktop:
            result=self.call('desktop_click',x=1,y=1)
            self.assertIn('error',result.data); desktop.assert_not_called()
    def test_no_control_characters_in_typing(self):
        self.tools.settings=replace(self.settings,desktop_enabled=True,vision_enabled=True)
        self.tools.screen_at=time.monotonic()
        with patch.object(self.tools,'_desktop') as desktop:
            result=self.call('desktop_type',text='command\n')
            self.assertIn('error',result.data); desktop.assert_not_called()

    def enable_desktop(self):
        self.tools.settings=replace(self.settings,desktop_enabled=True,vision_enabled=True)

    def test_no_capture_is_blocked_even_with_small_monotonic_clock(self):
        self.enable_desktop()
        with patch('avalon.computer.time.monotonic',return_value=10), patch.object(self.tools,'_desktop') as desktop:
            result=self.call('desktop_click',x=10,y=10)
        self.assertTrue(result.denied)
        desktop.assert_not_called()
        self.assertEqual(self.approve.calls,[])

    def test_real_capture_at_time_zero_is_valid(self):
        self.enable_desktop(); self.tools.screen_at=0.0
        with patch('avalon.computer.time.monotonic',return_value=10), patch.object(self.tools,'_desktop') as desktop, patch.object(self.cancel,'wait',return_value=False):
            desktop.return_value.onScreen.return_value=True
            result=self.call('desktop_click',x=10,y=10)
        self.assertTrue(result.data.get('input_sent'))
        desktop.return_value.click.assert_called_once_with(10,10)

    def test_capture_expiring_during_review_cannot_click(self):
        self.enable_desktop(); self.tools.screen_at=100
        clock=[110]
        self.approve.hook=lambda:clock.__setitem__(0,160)
        with patch('avalon.computer.time.monotonic',side_effect=lambda:clock[0]), patch.object(self.tools,'_desktop') as desktop, patch.object(self.cancel,'wait',return_value=False):
            desktop.return_value.onScreen.return_value=True
            result=self.call('desktop_click',x=10,y=10)
        self.assertTrue(result.denied)
        desktop.return_value.click.assert_not_called()
        self.assertIsNone(self.tools.screen_at)

    def test_capture_expiring_during_focus_delay_cannot_click(self):
        self.enable_desktop(); self.tools.screen_at=100
        clock=[144]
        def wait(seconds):
            clock[0]=146
            return False
        with patch('avalon.computer.time.monotonic',side_effect=lambda:clock[0]), patch.object(self.tools,'_desktop') as desktop, patch.object(self.cancel,'wait',side_effect=wait):
            desktop.return_value.onScreen.return_value=True
            result=self.call('desktop_click',x=10,y=10)
        self.assertTrue(result.denied)
        desktop.return_value.click.assert_not_called()

    def test_cancel_after_review_prevents_all_input(self):
        self.enable_desktop(); self.tools.screen_at=100
        self.approve.hook=self.cancel.set
        with patch('avalon.computer.time.monotonic',return_value=110), patch.object(self.tools,'_desktop') as desktop:
            result=self.call('desktop_type',text='hello')
        self.assertTrue(result.denied)
        desktop.return_value.write.assert_not_called()

    def test_stop_typing_prevents_remaining_chunks(self):
        self.enable_desktop(); self.tools.screen_at=100
        with patch('avalon.computer.time.monotonic',return_value=110), patch.object(self.tools,'_desktop') as desktop, patch.object(self.cancel,'wait',return_value=False):
            desktop.return_value.write.side_effect=lambda *args,**kwargs:self.cancel.set()
            result=self.call('desktop_type',text='a'*40)
        self.assertTrue(result.denied)
        self.assertTrue(result.data['interrupted'])
        self.assertEqual(result.data['characters_sent'],8)
        desktop.return_value.write.assert_called_once_with('a'*8,interval=.01)
        self.assertIsNone(self.tools.screen_at)

    def test_typing_preserves_text_order_without_cancellation(self):
        self.enable_desktop(); self.tools.screen_at=100
        text='abcdefgh12345678XYZ'
        with patch('avalon.computer.time.monotonic',return_value=110), patch.object(self.tools,'_desktop') as desktop, patch.object(self.cancel,'wait',return_value=False):
            result=self.call('desktop_type',text=text)
        pieces=[call.args[0] for call in desktop.return_value.write.call_args_list]
        self.assertEqual(''.join(pieces),text)
        self.assertTrue(all(len(piece)<=8 for piece in pieces))
        self.assertEqual(result.data['characters_sent'],len(text))
        self.assertFalse(result.denied)
        self.assertIsNone(self.tools.screen_at)

    def test_input_failure_invalidates_previous_capture(self):
        self.enable_desktop(); self.tools.screen_at=100
        with patch('avalon.computer.time.monotonic',return_value=110), patch.object(self.tools,'_desktop') as desktop, patch.object(self.cancel,'wait',return_value=False):
            desktop.return_value.onScreen.return_value=True
            desktop.return_value.click.side_effect=OSError('input failed')
            result=self.call('desktop_click',x=10,y=10)
        self.assertIn('error',result.data)
        self.assertIsNone(self.tools.screen_at)

class FakeTools:
    def __init__(self,denied=False): self.calls=[]; self.denied=denied
    def environment(self): return 'test'
    def schemas(self): return []
    def execute(self,name,args,cancel):
        self.calls.append((name,args))
        return Result({'result':'observed'},denied=self.denied)

class AgentTests(unittest.TestCase):
    def test_loop_feeds_results_back_to_model(self):
        seen=[]
        def turn(messages,schemas):
            seen.append(list(messages))
            if len(seen)==1:
                return Turn('Vou verificar.',[{'id':'1','name':'system_info','arguments':'{}'}])
            self.assertEqual(messages[-1]['role'],'tool')
            self.assertIn('observed',messages[-1]['content'])
            return Turn('Concluído.',[])
        tools=FakeTools(); agent=Agent(SimpleNamespace(tool_turn=turn),tools,lambda *args:None)
        self.assertEqual(agent.run('tarefa',[],Event()),'Concluído.')
        self.assertEqual(len(tools.calls),1)
    def test_denial_stops_instead_of_attempting_another_tool(self):
        calls=[{'id':'1','name':'write_text','arguments':'{}'}, {'id':'2','name':'run_terminal','arguments':'{}'}]
        tools=FakeTools(denied=True)
        agent=Agent(SimpleNamespace(tool_turn=lambda *args:Turn('',calls)),tools,lambda *args:None)
        self.assertIn('recusada',agent.run('tarefa',[],Event()))
        self.assertEqual(len(tools.calls),1)
    def test_invalid_json_cannot_execute(self):
        tools=FakeTools()
        agent=Agent(SimpleNamespace(tool_turn=lambda *args:Turn('',[{'id':'1','name':'x','arguments':'{bad'}])),tools,lambda *args:None)
        self.assertIn('inválida',agent.run('tarefa',[],Event())); self.assertEqual(tools.calls,[])
    def test_action_limit(self):
        tools=FakeTools()
        model=SimpleNamespace(tool_turn=lambda *args:Turn('',[{'id':'1','name':'x','arguments':'{}'}]))
        agent=Agent(model,tools,lambda *args:None,max_steps=2)
        self.assertIn('Limite',agent.run('tarefa',[],Event())); self.assertEqual(len(tools.calls),2)
    def test_deadline_stops_tool_execution_after_slow_model(self):
        def turn(*args):
            time.sleep(.03)
            return Turn('',[{'id':'1','name':'x','arguments':'{}'}])
        tools=FakeTools()
        agent=Agent(SimpleNamespace(tool_turn=turn),tools,lambda *args:None,max_seconds=.01)
        self.assertIn('interrompida',agent.run('x',[],Event()))
        self.assertEqual(tools.calls,[])
    def test_cancelled_agent_never_calls_model(self):
        cancel=Event(); cancel.set()
        model=SimpleNamespace(tool_turn=lambda *args:self.fail('model called after cancellation'))
        self.assertIn('interrompida',Agent(model,FakeTools(),lambda *args:None).run('x',[],cancel))
    def test_sdk_tool_call_mapping(self):
        message=SimpleNamespace(content='plan',tool_calls=[SimpleNamespace(id='call1',function=SimpleNamespace(name='system_info',arguments='{}'))])
        model=LanguageModel(Settings(Path('.'),api_key='fake'))
        recorded=[]
        def create(**kwargs): recorded.append(kwargs); return SimpleNamespace(choices=[SimpleNamespace(message=message)])
        model.client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        turn=model.tool_turn([{'role':'user','content':'hello'}],[])
        self.assertEqual(turn.calls[0]['name'],'system_info')
        self.assertEqual(recorded[0]['tool_choice'],'auto')

if __name__=='__main__': unittest.main()

