from __future__ import annotations

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
from douyin_creator_mcp.browser.commands import LoginStart
from douyin_creator_mcp.browser.executor import DefaultBrowserBackend
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


if __name__ == "__main__":
    unittest.main()
