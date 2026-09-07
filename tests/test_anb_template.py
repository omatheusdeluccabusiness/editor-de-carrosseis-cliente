from pathlib import Path
import tempfile
import unittest
import json
import urllib.request

from scripts.hub_sessions import create_hub_session, refresh_hub_session
from scripts.template_catalog import get_template
from tests.test_hub_server import running_test_server, mutation_headers


class AnbTemplateTest(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
