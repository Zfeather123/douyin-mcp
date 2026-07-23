from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from douyin_creator_mcp.tools.browser_tools import _write_qr_delivery_file


class BrowserToolDeliveryTest(unittest.TestCase):
    def test_qr_delivery_file_is_private_and_inside_task_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task_dir = Path(temp)
            with patch("pathlib.Path.cwd", return_value=task_dir):
                path = _write_qr_delivery_file(b"qr-png", "wanghuan-chat")

            self.assertEqual(path.parent, task_dir / "output")
            self.assertEqual(path.read_bytes(), b"qr-png")
            self.assertTrue(path.name.startswith("douyin-login-qr-wanghuan-chat-"))
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)

    def test_qr_delivery_file_rejects_unsafe_account_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with (
                patch("pathlib.Path.cwd", return_value=Path(temp)),
                self.assertRaises(Exception),
            ):
                _write_qr_delivery_file(b"qr-png", "../outside")


if __name__ == "__main__":
    unittest.main()
