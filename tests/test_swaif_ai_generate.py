import json
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from scripts import swaif_ai_generate


class FakeResponse:
    def __init__(self, payload: dict, status: int = 200):
        self._payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, *args, **kwargs):
        return json.dumps(self._payload).encode("utf-8")

    def getcode(self):
        return self.status


class SwaifAiGenerateTests(unittest.TestCase):
    def test_generate_accepts_http_200_and_writes_file(self):
        payload = {"choices": [{"message": {"content": "ok content"}}]}

        def fake_urlopen(_req, timeout=0):
            self.assertEqual(timeout, 120)
            return FakeResponse(payload=payload, status=200)

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "out.md"
            swaif_ai_generate.generate(
                str(target),
                "prompt",
                api_key="test-key",
                model="gpt-5.2",
                urlopen=fake_urlopen,
            )

            self.assertTrue(target.exists())
            self.assertEqual(target.read_text(encoding="utf-8"), "ok content\n")

    def test_generate_raises_for_non_200_status(self):
        payload = {"choices": [{"message": {"content": "ignored"}}]}

        def fake_urlopen(_req, timeout=0):
            return FakeResponse(payload=payload, status=201)

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "out.md"
            with self.assertRaisesRegex(RuntimeError, "unexpected status code: 201"):
                swaif_ai_generate.generate(
                    str(target),
                    "prompt",
                    api_key="test-key",
                    model="gpt-5.2",
                    urlopen=fake_urlopen,
                )

    def test_generate_converts_http_error_to_runtime_error(self):
        def fake_urlopen(_req, timeout=0):
            import io
            error_body = b'{"error": "Unauthorized"}'
            raise urllib.error.HTTPError(
                url="https://api.openai.com/v1/chat/completions",
                code=401,
                msg="Unauthorized",
                hdrs=None,
                fp=io.BytesIO(error_body),
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "out.md"
            with self.assertRaisesRegex(RuntimeError, r"HTTP 401"):
                swaif_ai_generate.generate(
                    str(target),
                    "prompt",
                    api_key="test-key",
                    model="gpt-5.2",
                    urlopen=fake_urlopen,
                )


if __name__ == "__main__":
    unittest.main()
