"""check-mcp-updates.sh reports OSV advisories and never edits files (agent-harness-platform R10.5)."""
# Validates: agent-harness-platform/R10.5
import http.server
import json
import subprocess
import threading
import unittest

from tests._support import ROOT, TemplateCopy

FIXTURES = ROOT / "tests/fixtures/osv"


def serve(osv_body: bytes):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):  # PyPI
            body = json.dumps({"info": {"version": "9.9.9"}}).encode()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):  # OSV
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(osv_body)

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class OsvLookup(unittest.TestCase):
    def run_script(self, body):
        server = serve(body)
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with TemplateCopy() as root:
                before = (root / ".kiro/settings/mcp.json").read_bytes()
                result = subprocess.run(["sh", str(root / "scripts/check-mcp-updates.sh")], capture_output=True, text=True, timeout=60,
                                        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "HARNESS_PYPI_URL": base, "HARNESS_OSV_URL": base + "/v1/query"})
                self.assertEqual((root / ".kiro/settings/mcp.json").read_bytes(), before)
                return result
        finally:
            server.shutdown()
            server.server_close()

    def test_advisory_is_listed_and_fails(self):
        result = self.run_script((FIXTURES / "vulnerable.json").read_bytes())
        self.assertEqual(result.returncode, 1)
        self.assertIn("advisories for git", result.stdout)
        self.assertIn("PYSEC-2026-1", result.stdout)

    def test_clean_response_has_no_advisory_section(self):
        result = self.run_script((FIXTURES / "clean.json").read_bytes())
        self.assertNotIn("advisories for", result.stdout)
        self.assertIn("update available", result.stdout)


if __name__ == "__main__":
    unittest.main()
