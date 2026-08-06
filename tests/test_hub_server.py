from __future__ import annotations

import json
import base64
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


def mutation_headers(base_url: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Origin": base_url,
        "X-Carrossel-CSRF": serve_carrossel.CSRF_TOKEN,
    }


class HubServerTest(unittest.TestCase):
    def test_root_http_returns_hub_without_redirect(self) -> None:
        with running_test_server() as base_url:
            with urllib.request.urlopen(base_url + "/") as response:
                html = response.read().decode("utf-8")
                status = response.status
                final_url = response.geturl()
                content_type = response.headers.get_content_type()

            self.assertEqual(status, 200)
            self.assertEqual(final_url, base_url + "/")
            self.assertEqual(content_type, "text/html")
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
                headers=mutation_headers(base_url),
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
                headers=mutation_headers(base_url),
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
                headers=mutation_headers(base_url),
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
                    headers=mutation_headers(base_url),
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

    def test_mutations_require_same_origin_and_csrf_token(self) -> None:
        with running_test_server() as base_url:
            for headers in (
                {"Content-Type": "application/json"},
                {
                    "Content-Type": "application/json",
                    "Origin": "http://evil.example",
                    "X-Carrossel-CSRF": serve_carrossel.CSRF_TOKEN,
                },
            ):
                with self.subTest(headers=headers):
                    request = urllib.request.Request(
                        base_url + "/api/sessoes",
                        data=b'{"template":"tweet"}',
                        headers=headers,
                        method="POST",
                    )
                    with self.assertRaises(urllib.error.HTTPError) as raised:
                        urllib.request.urlopen(request)
                    self.assertEqual(raised.exception.code, 403)

    def test_telegram_config_is_never_served_to_browser(self) -> None:
        with running_test_server() as base_url:
            secret_path = Path(serve_carrossel.DIR) / "telegram-config.json"
            secret_path.write_text('{"botToken":"secret-token","chatId":"secret-chat"}')
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(base_url + "/telegram-config.json")
            self.assertEqual(raised.exception.code, 404)
            body = raised.exception.read().decode("utf-8", errors="replace")
            self.assertNotIn("secret-token", body)
            self.assertNotIn("secret-chat", body)

    def test_telegram_status_is_redacted_and_send_is_server_side(self) -> None:
        png = base64.b64encode(b"png-0").decode("ascii")
        with running_test_server() as base_url, patch.object(
            serve_carrossel, "_read_telegram_config", return_value=("server-token", "server-chat")
        ), patch.object(
            serve_carrossel, "_telegram_api_request", return_value={"ok": True}
        ) as telegram_request:
            with urllib.request.urlopen(base_url + "/api/telegram/status") as response:
                status_body = response.read().decode("utf-8")
            self.assertEqual(json.loads(status_body), {"configured": True})
            self.assertNotIn("server-token", status_body)
            self.assertNotIn("server-chat", status_body)

            request = urllib.request.Request(
                base_url + "/api/telegram/send",
                data=json.dumps({"images_b64": [png], "caption": "teste"}).encode(),
                headers=mutation_headers(base_url),
                method="POST",
            )
            with urllib.request.urlopen(request) as response:
                result = json.loads(response.read())
            self.assertEqual(result, {"ok": True, "sent": 1})
            method, fields, images = telegram_request.call_args.args
            self.assertEqual(method, "sendPhoto")
            self.assertEqual(
                fields,
                {"chat_id": "server-chat", "photo": "attach://file0", "caption": "teste"},
            )
            self.assertEqual(images, [b"png-0"])

    def test_telegram_batches_variable_slide_counts_in_order(self) -> None:
        for count, expected_methods, expected_sizes in (
            (10, ["sendMediaGroup"], [10]),
            (11, ["sendMediaGroup", "sendPhoto"], [10, 1]),
            (22, ["sendMediaGroup", "sendMediaGroup", "sendMediaGroup"], [10, 10, 2]),
        ):
            with self.subTest(count=count), running_test_server() as base_url, patch.object(
                serve_carrossel,
                "_read_telegram_config",
                return_value=("server-token", "server-chat"),
            ), patch.object(
                serve_carrossel,
                "_telegram_api_request",
                return_value={"ok": True},
            ) as telegram_request:
                encoded = [base64.b64encode(f"png-{index}".encode()).decode() for index in range(count)]
                request = urllib.request.Request(
                    base_url + "/api/telegram/send",
                    data=json.dumps({"images_b64": encoded, "caption": "legenda"}).encode(),
                    headers=mutation_headers(base_url),
                    method="POST",
                )
                with urllib.request.urlopen(request) as response:
                    result = json.loads(response.read())

                self.assertEqual(result, {"ok": True, "sent": count})
                calls = telegram_request.call_args_list
                self.assertEqual([call.args[0] for call in calls], expected_methods)
                self.assertEqual([len(call.args[2]) for call in calls], expected_sizes)
                sent = [image for call in calls for image in call.args[2]]
                self.assertEqual(sent, [f"png-{index}".encode() for index in range(count)])
                self.assertEqual(calls[0].args[1]["chat_id"], "server-chat")
                first_fields = calls[0].args[1]
                first_media = json.loads(first_fields["media"])
                self.assertEqual(first_media[0]["caption"], "legenda")
                for call in calls[1:]:
                    fields = call.args[1]
                    self.assertNotIn("caption", fields)
                    if "media" in fields:
                        self.assertTrue(all("caption" not in item for item in json.loads(fields["media"])))
                self.assertNotIn("server-token", json.dumps(result))
                self.assertNotIn("server-chat", json.dumps(result))

    def test_delete_removes_only_valid_hub_session(self) -> None:
        session_id = "hub-tweet-0123456789ab"
        with running_test_server() as base_url:
            hub_file = Path(serve_carrossel.DIR) / f"{session_id}.html"
            technical_file = Path(serve_carrossel.DIR) / "editor-tecnico.html"
            hub_file.write_text("hub", encoding="utf-8")
            technical_file.write_text("tecnico", encoding="utf-8")

            request = urllib.request.Request(
                base_url + "/api/sessoes/" + session_id,
                headers=mutation_headers(base_url),
                method="DELETE",
            )
            with urllib.request.urlopen(request) as response:
                self.assertEqual(response.status, 200)
            self.assertFalse(hub_file.exists())
            self.assertTrue(technical_file.exists())

            invalid = urllib.request.Request(
                base_url + "/api/sessoes/editor-tecnico",
                headers=mutation_headers(base_url),
                method="DELETE",
            )
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(invalid)
            self.assertEqual(raised.exception.code, 404)
            self.assertTrue(technical_file.exists())

    def test_runtime_binds_only_to_ipv4_loopback(self) -> None:
        source = Path(serve_carrossel.__file__).read_text(encoding="utf-8")
        self.assertIn('ReusableThreadingTCPServer(("127.0.0.1", PORT)', source)
        self.assertNotIn('ReusableThreadingTCPServer(("", PORT)', source)


if __name__ == "__main__":
    unittest.main()
