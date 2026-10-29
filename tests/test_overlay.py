from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from avalon.overlay_state import Preferences, VisualState
from avalon.sprites import SpriteAtlas

class PreferencesTests(unittest.TestCase):
    def test_invalid_and_missing_preferences_use_defaults(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'overlay.json'
            self.assertEqual(Preferences.load(path).size,144)
            path.write_text('{broken')
            self.assertEqual(Preferences.load(path).size,144)
            path.write_text('{"x":true,"y":"oops","size":5000,"animate":0}')
            self.assertEqual(Preferences.load(path),Preferences())
    def test_roundtrip_and_reposition_after_screen_change(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'overlay.json'
            prefs=Preferences(x=9000,y=9000,size=192,animate=False)
            prefs.fit(1280,720); prefs.save(path)
            restored=Preferences.load(path)
            self.assertEqual((restored.x,restored.y),(1088,528))
            self.assertFalse(restored.animate)
    def test_default_position_is_on_screen(self):
        prefs=Preferences(); x,y=prefs.fit(1920,1080)
        self.assertGreaterEqual(x,0); self.assertGreaterEqual(y,0)
        self.assertLessEqual(x+prefs.size,1920)

class VisualTests(unittest.TestCase):
    def test_states_follow_backend_activity(self):
        visual=VisualState()
        for status,expected in [('Escutando','listening'),('Processando','working'),
            ('Agente: etapa 2/12','working'),('Falando','speaking'),('Pronto','idle')]:
            visual.observe('status',status,now=10)
            self.assertEqual(visual.current(now=10),expected)
    def test_approval_stays_visible_across_status_events(self):
        visual=VisualState()
        visual.observe('approval',{'id':'request1'},now=10)
        visual.observe('status','Pronto',now=11)
        self.assertEqual(visual.current(now=11),'alert')
        visual.observe('approval_done','wrong',now=12)
        self.assertEqual(visual.current(now=12),'alert')
        visual.observe('approval_done','request1',now=13)
        self.assertEqual(visual.current(now=13),'idle')
    def test_errors_have_limited_alert_duration(self):
        visual=VisualState(); visual.observe('error','oops',now=10)
        self.assertEqual(visual.current(now=12),'alert')
        self.assertEqual(visual.current(now=17),'idle')

class SpriteTests(unittest.TestCase):
    def test_atlas_rgba_and_all_states_render(self):
        atlas=SpriteAtlas()
        self.assertEqual(atlas.image.mode,'RGBA')
        self.assertEqual(atlas.image.getchannel('A').getextrema(),(0,255))
        for state in atlas.states:
            for index in range(4):
                frame=atlas.frame(state,index,144)
                self.assertEqual(frame.size,(144,144))
                self.assertEqual(frame.mode,'RGBA')
                self.assertTrue(frame.getbbox())
                self.assertLessEqual(set(frame.getchannel('A').tobytes()),{0,255})
    def test_frame_timing_pause_and_unknown_state(self):
        atlas=SpriteAtlas()
        self.assertEqual(atlas.index('idle',440),2)
        self.assertEqual(atlas.index('idle',440,animate=False),0)
        self.assertEqual(atlas.frame('missing',0,96).size,(96,96))
    def test_render_size_validation(self):
        with self.assertRaises(ValueError): SpriteAtlas().frame('idle',0,4096)

if __name__=='__main__': unittest.main()
