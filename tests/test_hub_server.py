from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from scripts import serve_carrossel
from scripts.hub_sessions import HubSession


@contextmanager
def running_test_server():
    previous_dir = serve_carrossel.DIR
    with tempfile.TemporaryDirectory() as tmp:
        serve_carrossel.DIR = tmp
        server = serve_carrossel.ReusableThreadingTCPServer(
            ("127.0.0.1", 0),
            serve_carrossel.CarrosselHandler,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        try:
            yield f"http://{host}:{port}"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
            serve_carrossel.DIR = previous_dir


class HubServerTest(unittest.TestCase):
    def test_root_http_returns_hub_without_redirect(self) -> None:
        with running_test_server() as base_url:
            with urllib.request.urlopen(base_url + "/") as response:
                html = response.read().decode("utf-8")

            self.assertEqual(response.status, 200)
            self.assertEqual(response.geturl(), base_url + "/")
            self.assertEqual(response.headers.get_content_type(), "text/html")
            self.assertIn('"id": "tweet"', html)
            self.assertIn('"id": "stories"', html)

    def test_root_renders_only_official_templates(self) -> None:
        renderer = getattr(serve_carrossel, "_render_hub", None)
        self.assertIsNotNone(renderer, "o servidor ainda não renderiza o HUB")

        html = renderer()

        self.assertIn("Editor de Carrosséis", html)
        self.assertIn('"id": "tweet"', html)
        self.assertIn('"id": "stories"', html)
        self.assertNotIn('"id": "ostentacao"', html)

    def test_create_session_response(self) -> None:
        with running_test_server() as base_url, patch.object(
            serve_carrossel,
            "create_hub_session",
            return_value=HubSession(
                "hub-tweet-abc",
                Path("/tmp/hub-tweet-abc.html"),
                "/hub-tweet-abc.html",
            ),
        ):
            req = urllib.request.Request(
                base_url + "/api/sessoes",
                data=json.dumps({"template": "tweet"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req) as response:
                body = json.loads(response.read())

            self.assertEqual(response.status, 201)
            self.assertEqual(body["url"], "/hub-tweet-abc.html")
            self.assertEqual(body["session_id"], "hub-tweet-abc")

    def test_invalid_template_returns_400(self) -> None:
        with running_test_server() as base_url:
            req = urllib.request.Request(
                base_url + "/api/sessoes",
                data=b'{"template":"inexistente"}',
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(req)

            self.assertEqual(raised.exception.code, 400)
            body = json.loads(raised.exception.read())
            self.assertEqual(body["error"], "template_invalido")

    def test_malformed_json_returns_400(self) -> None:
        with running_test_server() as base_url:
            req = urllib.request.Request(
                base_url + "/api/sessoes",
                data=b"{",
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(req)

            self.assertEqual(raised.exception.code, 400)
            body = json.loads(raised.exception.read())
            self.assertEqual(body["error"], "json_invalido")

    def test_non_object_json_returns_400(self) -> None:
        for payload in (b"null", b"[]"):
            with self.subTest(payload=payload), running_test_server() as base_url:
                req = urllib.request.Request(
                    base_url + "/api/sessoes",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )

                with self.assertRaises(urllib.error.HTTPError) as raised:
                    urllib.request.urlopen(req)

                self.assertEqual(raised.exception.code, 400)
                body = json.loads(raised.exception.read())
                self.assertEqual(body["error"], "payload_invalido")

    def test_focus_indicator_uses_solid_action_blue(self) -> None:
        html = serve_carrossel._render_hub()

        self.assertIn("outline: 3px solid var(--acao);", html)
        self.assertNotIn("outline: 3px solid rgba(0, 122, 255, 0.34);", html)


if __name__ == "__main__":
    unittest.main()
