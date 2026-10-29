"""Real Tk smoke tests, without API, microphone or real desktop input."""
from queue import Queue
from threading import Event, Thread
from types import SimpleNamespace
from unittest.mock import Mock
import os
import tkinter as tk
from tkinter import ttk
import unittest
from avalon.approvals import Approvals
from avalon.ui import App

class FakeController:
    def __init__(self):
        self.events=Queue()
        self.wake=Event()
        self.speak_enabled=False
        self.agent_enabled=False
        self.audio=SimpleNamespace(interrupt=Mock())
        self.alive=True
        self.thread=SimpleNamespace(is_alive=lambda:self.alive)
        self.stop_task=Mock()
        self.submit=Mock(return_value=True)
        self.listen_once=Mock()
        self.close_calls=0
        self.approvals=Approvals(lambda kind,value:self.events.put((kind,value)))
        self.agent=SimpleNamespace(tools=SimpleNamespace(approvals=self.approvals))
    def set_wake(self,active):
        self.wake.set() if active else self.wake.clear()
    def close(self):
        self.close_calls+=1
        self.approvals.cancel()
        self.alive=False
        self.events.put(('closed',''))

def buttons(window):
    for child in window.winfo_children():
        if isinstance(child,ttk.Button): yield child
        yield from buttons(child)

class GuiTests(unittest.TestCase):
    def setUp(self):
        try:
            probe=tk.Tk(); probe.destroy()
        except tk.TclError as error:
            if os.getenv('AVALON_REQUIRE_GUI')=='1': self.fail('GUI is required: '+str(error))
            self.skipTest('No graphical display: '+str(error))
        self.controller=FakeController()
        self.app=App(self.controller)
        self.callback_errors=[]
        self.app.report_callback_exception=lambda kind,value,tb:self.callback_errors.append(str(value))
        self.app.update()
        self.approval_thread=None
        self.destroyed=False
    def tearDown(self):
        if hasattr(self,'controller'):
            self.controller.approvals.cancel()
        if getattr(self,'approval_thread',None) is not None:
            self.approval_thread.join(2)
            self.assertFalse(self.approval_thread.is_alive())
        if hasattr(self,'app') and not self.destroyed:
            self.app.destroy()
        if hasattr(self,'callback_errors'): self.assertEqual(self.callback_errors,[])
    def start_approval(self):
        self.outcome=[]
        def ask():
            self.outcome.append(self.controller.approvals.ask('Autorizar teste','Ação de teste sem efeito externo',Event()))
        self.approval_thread=Thread(target=ask,daemon=True)
        self.approval_thread.start()
        kind,request=self.controller.events.get(timeout=2)
        self.assertEqual(kind,'approval')
        self.controller.events.put((kind,request))
        self.app.poll(); self.app.update()
        return self.app.approval_window
    def answer(self,label):
        button=next(button for button in buttons(self.app.approval_window) if button.cget('text')==label)
        button.invoke()
        self.approval_thread.join(2)
        self.assertFalse(self.approval_thread.is_alive())
        self.app.poll(); self.app.update()
    def test_window_handles_events_and_sends_message(self):
        self.controller.events.put(('status','Processando'))
        self.controller.events.put(('assistant','Resposta de teste'))
        self.app.poll(); self.app.update()
        self.assertEqual(self.app.status.get(),'Processando')
        self.assertIn('Resposta de teste',self.app.chat.get('1.0','end'))
        self.app.entry.insert(0,'ajuda'); self.app.send()
        self.controller.submit.assert_called_once_with('ajuda')
        self.assertEqual(self.app.entry.get(),'')
    def test_approval_uses_real_broker_and_is_not_modal(self):
        window=self.start_approval()
        self.assertTrue(window.winfo_viewable())
        self.assertEqual(str(window.transient()),str(self.app))
        self.assertIsNone(self.app.grab_current())
        stop=next(button for button in buttons(self.app) if button.cget('text')=='PARAR TAREFA')
        stop.invoke(); self.controller.stop_task.assert_called_once()
        self.answer('Aprovar esta ação')
        self.assertEqual(self.outcome,[True])
        self.assertIsNone(self.app.approval_window)
    def test_refusal_and_closing_approval_do_not_authorize(self):
        self.start_approval(); self.answer('Recusar')
        self.assertEqual(self.outcome,[False])
        window=self.start_approval()
        window.tk.call(window.protocol('WM_DELETE_WINDOW'))
        self.approval_thread.join(2)
        self.app.poll(); self.app.update()
        self.assertEqual(self.outcome,[False])
        self.assertIsNone(self.app.approval_window)
    def test_animation_does_not_move_keyboard_focus(self):
        self.app.entry.focus_force(); self.app.update()
        self.assertEqual(self.app.focus_get(),self.app.entry)
        # Run an animation frame; subsequent frames must not steal focus either.
        self.app.after_cancel(self.app.animation_timer)
        self.app.animate(); self.app.update()
        self.assertEqual(self.app.focus_get(),self.app.entry)
    def test_shutdown_cancels_timers_and_closes_approval(self):
        self.start_approval()
        self.app.close(); self.app.poll()
        self.destroyed=True
        self.approval_thread.join(2)
        self.assertEqual(self.outcome,[False])
        self.assertEqual(self.controller.close_calls,1)
        self.assertIsNone(self.app.poll_timer)
        self.assertIsNone(self.app.animation_timer)

if __name__=='__main__': unittest.main()
