from pathlib import Path
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch
import sys
import unittest
from avalon.audio import Audio
from avalon.config import Settings
from avalon.llm import LanguageModel

class AdapterTests(unittest.TestCase):
    def test_auto_device_fallback(self):
        calls=[]; notices=[]
        def model(name, **kwargs):
            calls.append(kwargs)
            if kwargs['device']=='cuda': raise RuntimeError('driver')
            return object()
        audio=Audio(Settings(Path('/tmp/not-used')), notices.append)
        with patch.dict(sys.modules, {'faster_whisper': SimpleNamespace(WhisperModel=model)}):
            audio._load_model(); audio._load_model()
        self.assertEqual([c['device'] for c in calls], ['cuda','cpu'])
        self.assertEqual(len(notices),1)

    def test_explicit_cuda_does_not_silently_fallback(self):
        def model(*args, **kwargs): raise RuntimeError('driver')
        audio=Audio(Settings(Path('/tmp/not-used'),device='cuda'))
        with patch.dict(sys.modules, {'faster_whisper': SimpleNamespace(WhisperModel=model)}):
            with self.assertRaises(RuntimeError): audio._load_model()

    def test_capture_temp_is_deleted_on_transcription_failure(self):
        paths=[]
        class Mic:
            def __enter__(self): return self
            def __exit__(self,*args): pass
        class Recognizer:
            def adjust_for_ambient_noise(self,*args,**kwargs): pass
            def listen(self,*args,**kwargs):
                return SimpleNamespace(get_wav_data=lambda: b'audio')
        def transcribe(path, **kwargs):
            self.assertTrue(Path(path).exists()); paths.append(path)
            raise RuntimeError('transcription failed')
        audio=Audio(Settings(Path('/tmp/not-used')))
        audio.model=SimpleNamespace(transcribe=transcribe)
        module=SimpleNamespace(Recognizer=Recognizer,Microphone=Mic,WaitTimeoutError=TimeoutError)
        with patch.dict(sys.modules, {'speech_recognition':module}):
            with self.assertRaises(RuntimeError): audio.listen(Event())
        self.assertFalse(Path(paths[0]).exists())

    def test_llm_uses_context_and_rejects_empty_reply(self):
        calls=[]
        def create(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='  hello  '))])
        model=LanguageModel(Settings(Path('/tmp/not-used'),api_key='fake',model='test-model'))
        model.client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        context=[{'role':'user','content':'before'},{'role':'assistant','content':'response'}]
        self.assertEqual(model.reply(context,'now'),'hello')
        self.assertEqual(calls[0]['messages'][1:3],context)
        self.assertEqual(calls[0]['model'],'test-model')
        model.client.chat.completions.create=lambda **kwargs: SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=None))])
        with self.assertRaises(RuntimeError): model.reply([], 'now')

    def test_configuration_rejects_invalid_device(self):
        with patch.dict('os.environ', {'AVALON_DEVICE':'invalid'}):
            with self.assertRaises(ValueError): Settings.load()

if __name__=='__main__': unittest.main()
