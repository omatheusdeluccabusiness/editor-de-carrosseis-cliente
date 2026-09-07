from pathlib import Path
import tempfile
import unittest
import json
import urllib.request

from scripts.hub_sessions import create_hub_session, refresh_hub_session
from scripts.template_catalog import get_template
from tests.test_hub_server import running_test_server, mutation_headers


class AnbTemplateTest(unittest.TestCase):
    def test_vortex_uses_same_shader_as_stories(self):
        root = Path(__file__).resolve().parent.parent
        anb = (root / 'templates/anb_editor.html').read_text(encoding='utf-8')
        stories = (root / 'templates/stories_background_editor.html').read_text(encoding='utf-8')
        start = '  function compileRadialBlurShader('
        end = '  async function drawHaloGrainEffect('
        shader = stories[stories.index(start):stories.index(end)].strip()
        self.assertIn(shader, anb)

    def test_hub_can_create_serve_and_delete_anb(self):
        with running_test_server() as base:
            req = urllib.request.Request(base + '/api/sessoes',
                data=json.dumps({'template': 'anb'}).encode(),
                headers=mutation_headers(base), method='POST')
            with urllib.request.urlopen(req) as response:
                payload = json.load(response)
            self.assertTrue(payload.get('ok'))
            with urllib.request.urlopen(base + payload['url']) as response:
                self.assertIn('ANB Style', response.read().decode())
            delete = urllib.request.Request(base + '/api/sessoes/' + payload['session_id'],
                headers=mutation_headers(base), method='DELETE')
            with urllib.request.urlopen(delete) as response:
                self.assertTrue(json.load(response)['ok'])
            with urllib.request.urlopen(base + '/assets/fonts/Anton-Regular.ttf') as response:
                self.assertEqual(response.headers.get_content_type(), 'font/ttf')
                self.assertGreater(len(response.read()), 1000)

    def test_catalog_and_session(self):
        self.assertEqual(get_template('anb').name, 'ANB Style')
        with tempfile.TemporaryDirectory() as folder:
            session = create_hub_session('anb', Path(folder))
            html = session.path.read_text(encoding='utf-8')
            self.assertIn('ANB Style', html)
            self.assertIn('<canvas', html)
            self.assertNotIn('{{DOC_KEY}}', html)
            self.assertEqual(refresh_hub_session(session.id, Path(folder)).id, session.id)

    def test_template_accepts_imported_slides(self):
        root = Path(__file__).resolve().parent.parent
        anb = (root / 'templates/anb_editor.html').read_text(encoding='utf-8')
        self.assertIn('const importedSlides={{ANB_SLIDES_JSON}};', anb)
        self.assertIn('loadInitialPhotos()', anb)

    def test_template_has_direct_editing_and_local_autosave(self):
        root = Path(__file__).resolve().parent.parent
        anb = (root / 'templates/anb_editor.html').read_text(encoding='utf-8')
        self.assertIn('id="directLayer"', anb)
        self.assertIn('contenteditable="true"', anb)
        self.assertIn("indexedDB.open('carrossel-anb-style'", anb)
        self.assertIn('id="resetCarousel"', anb)
        self.assertIn('restoreLocal()', anb)
        self.assertIn('id="sendTelegram"', anb)
        self.assertIn('id="lineHeight"', anb)
        self.assertIn('id="letterSpacing"', anb)
        self.assertIn('id="fontSize"', anb)
        self.assertNotIn('id="openProject"', anb)
        self.assertNotIn('id="saveProject"', anb)
        self.assertNotIn('id="bold"', anb)
        self.assertNotIn('id="accent"', anb)


if __name__ == '__main__':
    unittest.main()
