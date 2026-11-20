"""Run dependency-free JavaScript client tests with real LAMBDA3 event data."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from solver import Solver


class ClientTests(unittest.TestCase):
    def test_javascript_client(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Install Node.js 18+ to run client tests (not needed to run the app)")
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "events.json"
            fixture.write_text(json.dumps(list(Solver().events(4))), encoding="utf-8")
            environment = {**os.environ, "QUEENS_TEST_FIXTURE": str(fixture)}
            result = subprocess.run(
                [node, "--test", str(Path(__file__).with_name("client.test.mjs"))],
                env=environment, capture_output=True, text=True, encoding="utf-8",
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
