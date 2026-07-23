from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from douyin_creator_mcp.tools.browser_tools import (
    _upload_qr_to_multica,
    _write_qr_delivery_file,
)


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

    def test_multica_upload_returns_attachment_fields(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=(
                '{"filename":"qr.png","id":"attachment-id",'
                '"markdown":"![qr](https://example.test/qr)",'
                '"markdown_url":"https://example.test/qr"}\n'
                "Uploaded: qr.png\n"
            ),
            stderr="",
        )
        with (
            patch.dict(os.environ, {"MULTICA_TASK_ID": "task-id"}),
            patch(
                "douyin_creator_mcp.tools.browser_tools.shutil.which",
                return_value="/usr/bin/multica",
            ),
            patch(
                "douyin_creator_mcp.tools.browser_tools.subprocess.run",
                return_value=completed,
            ) as run,
        ):
            result = _upload_qr_to_multica(Path("/task/output/qr.png"))

        self.assertEqual(result["id"], "attachment-id")
        self.assertEqual(result["markdown"], "![qr](https://example.test/qr)")
        run.assert_called_once_with(
            [
                "/usr/bin/multica",
                "attachment",
                "upload",
                "/task/output/qr.png",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_multica_upload_is_optional_outside_task_context(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(_upload_qr_to_multica(Path("/tmp/qr.png")))


if __name__ == "__main__":
    unittest.main()
