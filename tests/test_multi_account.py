from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from douyin_creator_mcp.accounts import (
    BROWSER_DEFAULT_ACCOUNT_ID,
    browser_profile_dir,
    validate_account_id,
)
from douyin_creator_mcp.config import Settings
from douyin_creator_mcp.cli import _configured_browser_available
from douyin_creator_mcp.browser.commands import LoginStart
from douyin_creator_mcp.browser.executor import (
    BrowserExecutor,
    DefaultBrowserBackend,
)
from douyin_creator_mcp.browser.profile_lock import ProfileLock
from douyin_creator_mcp.browser.session import BrowserSession
from douyin_creator_mcp.errors import AppError
from douyin_creator_mcp.services.browser_service import BrowserService
from douyin_creator_mcp.storage.db import Database


class MultiAccountTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.settings = Settings(
            data_dir=root / "data",
            douyin_browser_profile_dir=root / "data" / "browser-profile",
            douyin_browser_profiles_dir=root / "data" / "browser-profiles",
        )
        self.db = Database(self.settings.data_dir / "douyin.sqlite")
        self.db.init_schema()
        self.service = BrowserService(self.settings, self.db)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_named_accounts_get_isolated_profile_directories(self) -> None:
        legacy = browser_profile_dir(
            self.settings.douyin_browser_profile_dir,
            self.settings.douyin_browser_profiles_dir,
            BROWSER_DEFAULT_ACCOUNT_ID,
        )
        xiaojing = browser_profile_dir(
            self.settings.douyin_browser_profile_dir,
            self.settings.douyin_browser_profiles_dir,
            "xiaojing",
        )
        gaobei = browser_profile_dir(
            self.settings.douyin_browser_profile_dir,
            self.settings.douyin_browser_profiles_dir,
            "gaobei",
        )
        self.assertEqual(legacy, self.settings.douyin_browser_profile_dir)
        self.assertEqual(
            xiaojing, self.settings.douyin_browser_profiles_dir / "xiaojing"
        )
        self.assertEqual(
            gaobei, self.settings.douyin_browser_profiles_dir / "gaobei"
        )
        self.assertEqual(len({legacy, xiaojing, gaobei}), 3)

    def test_account_id_rejects_path_traversal(self) -> None:
        for value in ("../gaobei", "a/b", "", "account name"):
            with self.subTest(value=value), self.assertRaises(AppError):
                validate_account_id(value)

    def test_missing_account_id_fails_closed_when_multiple_exist(self) -> None:
        for account_id in ("xiaojing", "gaobei"):
            self.db.execute(
                "INSERT INTO browser_account_bindings "
                "(account_id,fingerprint_salt,anchor_hashes_json,anchor_count,"
                "created_at,last_verified_at) VALUES (?,?,?,?,?,?)",
                (
                    account_id,
                    "salt",
                    '["hash"]',
                    1,
                    "2026-07-23T00:00:00Z",
                    "2026-07-23T00:00:00Z",
                ),
            )
        with self.assertRaises(AppError) as captured:
            self.service._resolve_account_id(None)
        self.assertEqual(
            captured.exception.extra["available_accounts"],
            ["gaobei", "xiaojing"],
        )
        self.assertEqual(self.service._resolve_account_id("gaobei"), "gaobei")

    def test_single_existing_account_remains_backward_compatible(self) -> None:
        self.db.execute(
            "INSERT INTO browser_account_bindings "
            "(account_id,fingerprint_salt,anchor_hashes_json,anchor_count,"
            "created_at,last_verified_at) VALUES (?,?,?,?,?,?)",
            (
                "xiaojing",
                "salt",
                '["hash"]',
                1,
                "2026-07-23T00:00:00Z",
                "2026-07-23T00:00:00Z",
            ),
        )
        self.assertEqual(self.service._resolve_account_id(None), "xiaojing")

    def test_executor_keeps_independent_sessions_and_locks(self) -> None:
        created: list[object] = []

        class FakeSession:
            def __init__(
                self, settings: Settings, headless: bool, profile_dir: Path
            ) -> None:
                del settings, headless
                self.profile_dir = profile_dir
                self.is_running = True
                self.closed = False
                created.append(self)

            def open_creator_home(self) -> object:
                return object()

            def close(self) -> None:
                self.closed = True
                self.is_running = False

        class FakeLock:
            def __init__(self, profile_dir: Path, filename: str) -> None:
                del filename
                self.profile_dir = profile_dir
                self.released = False

            def acquire(self) -> None:
                return None

            def release(self) -> None:
                self.released = True

        snapshot = {
            "login_status": "logged_in",
            "title": "creator",
            "source_url": "https://creator.douyin.com/",
            "video_candidates": [],
        }
        with (
            patch(
                "douyin_creator_mcp.browser.executor.BrowserSession",
                FakeSession,
            ),
            patch(
                "douyin_creator_mcp.browser.executor.ProfileLock",
                FakeLock,
            ),
            patch(
                "douyin_creator_mcp.browser.executor.extract_page_snapshot",
                return_value=snapshot,
            ),
        ):
            backend = DefaultBrowserBackend(self.settings, self.db)
            backend.handle(LoginStart(account_id="xiaojing"))
            backend.handle(LoginStart(account_id="gaobei"))
            self.assertEqual(set(backend.sessions), {"xiaojing", "gaobei"})
            self.assertNotEqual(
                backend.sessions["xiaojing"].profile_dir,
                backend.sessions["gaobei"].profile_dir,
            )
            backend.close("xiaojing")
            self.assertNotIn("xiaojing", backend.sessions)
            self.assertIn("gaobei", backend.sessions)
            self.assertTrue(created[0].closed)
            self.assertFalse(created[1].closed)
            backend.close()

    def test_qr_capture_prefers_square_login_element(self) -> None:
        expected = b"qr-png"
        test_case = self

        class FakeNode:
            def bounding_box(self) -> dict[str, int]:
                return {"width": 240, "height": 240}

            def screenshot(self, type: str) -> bytes:
                test_case.assertEqual(type, "png")
                return expected

        class FakeLocator:
            def count(self) -> int:
                return 1

            def nth(self, index: int) -> FakeNode:
                test_case.assertEqual(index, 0)
                return FakeNode()

        class FakePage:
            def locator(self, selector: str) -> FakeLocator:
                test_case.assertIn("qrcode", selector)
                return FakeLocator()

            def screenshot(self, **kwargs: object) -> bytes:
                raise AssertionError("full-page fallback should not be used")

        session = BrowserSession(self.settings, headless=True)
        self.assertEqual(session.capture_login_qr(FakePage()), expected)

    def test_login_qr_uses_named_headless_profile(self) -> None:
        class FakeExecutor:
            def __init__(self) -> None:
                self.command: LoginStart | None = None

            def execute(self, command: LoginStart) -> dict[str, object]:
                self.command = command
                return {
                    "account_id": command.account_id,
                    "browser_running": True,
                    "login_status": "login_required",
                    "title": "抖音创作者中心",
                    "source_url": "https://creator.douyin.com/",
                    "video_candidate_count": 0,
                    "qr_image": b"qr-png",
                }

        executor = FakeExecutor()
        service = BrowserService(
            self.settings,
            self.db,
            browser_executor=executor,
        )
        with patch(
            "douyin_creator_mcp.services.browser_service."
            "require_platform_risk_acknowledgement"
        ):
            result = service.login_qr("gaobei")
        self.assertIsNotNone(executor.command)
        self.assertEqual(executor.command.account_id, "gaobei")
        self.assertTrue(executor.command.headless)
        self.assertTrue(executor.command.capture_qr)
        self.assertEqual(result["qr_image"], b"qr-png")

    def test_executor_allows_ephemeral_qr_bytes(self) -> None:
        BrowserExecutor._validate_pure_value(
            {"account_id": "gaobei", "qr_image": b"qr-png"}
        )

    def test_profile_lock_reclaims_reused_sandbox_pid(self) -> None:
        profile_dir = self.settings.douyin_browser_profiles_dir / "gaobei"
        profile_dir.mkdir(parents=True)
        lock_path = profile_dir / ".douyin-mcp.lock"
        lock_path.write_text(
            json.dumps(
                {
                    "owner": "interrupted-turn",
                    "pid": os.getpid(),
                    "process_start_ticks": "previous-process",
                    "acquired_at": "2026-07-23T00:00:00+00:00",
                }
            ),
            encoding="utf-8",
        )

        lock = ProfileLock(profile_dir, stale_grace_seconds=3600)
        with (
            patch.object(ProfileLock, "_pid_is_alive", return_value=True),
            patch.object(
                ProfileLock,
                "_linux_process_start_ticks",
                return_value="current-process",
            ),
        ):
            lock.acquire()
        self.assertTrue(lock._acquired)
        lock.release()
        self.assertFalse(lock_path.exists())

    def test_doctor_checks_configured_browser_executable(self) -> None:
        with patch("douyin_creator_mcp.cli.shutil.which") as which:
            which.side_effect = lambda name: (
                "/usr/bin/google-chrome" if name == "google-chrome" else None
            )
            self.assertTrue(_configured_browser_available("chrome"))
            self.assertFalse(_configured_browser_available("msedge"))
            self.assertFalse(_configured_browser_available("unknown-channel"))


if __name__ == "__main__":
    unittest.main()
