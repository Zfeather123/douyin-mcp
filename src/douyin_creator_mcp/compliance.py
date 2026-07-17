"""Platform-terms acknowledgement for browser automation entrypoints."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .errors import PLATFORM_TERMS_ACKNOWLEDGEMENT_REQUIRED, AppError


ACKNOWLEDGEMENT_VERSION = "douyin-automation-risk-v1"
ACKNOWLEDGEMENT_FILENAME = ".platform-risk-acknowledgement.json"
DOUYIN_TERMS_URL = (
    "https://www.douyin.com/agreements/?id=6773906068725565448"
)
PROJECT_COMPLIANCE_URL = (
    "https://github.com/Kuhakucai/douyin-mcp/blob/main/PLATFORM_COMPLIANCE.md"
)
PLATFORM_COMPLIANCE_NOTICE = (
    "本项目是非官方社区工具，未获抖音授权或背书。抖音用户服务协议第 5.1 条"
    "限制使用自动化程序接入并收集或处理平台信息。项目许可证仅授权使用本项目"
    "代码，不授予访问抖音、处理平台数据或使用抖音商标的权利。启动浏览器自动化"
    "前，请阅读 PLATFORM_COMPLIANCE.md，并自行确认已获得必要授权且符合适用条款。"
)
ACKNOWLEDGEMENT_STATEMENT = (
    "我已阅读抖音用户服务协议第 5.1 条及 PLATFORM_COMPLIANCE.md，理解自动化访问、"
    "收集或处理平台信息可能违反平台条款，并自行负责确认授权与合规性。"
)


def platform_compliance_status(data_dir: Path) -> dict[str, Any]:
    """Return public acknowledgement state without exposing local paths."""

    payload = _read_acknowledgement(data_dir)
    acknowledged = bool(
        payload and payload.get("version") == ACKNOWLEDGEMENT_VERSION
    )
    return {
        "acknowledged": acknowledged,
        "acknowledgement_version": ACKNOWLEDGEMENT_VERSION,
        "acknowledged_at": payload.get("acknowledged_at") if acknowledged else None,
        "terms_url": DOUYIN_TERMS_URL,
        "project_compliance_url": PROJECT_COMPLIANCE_URL,
        "notice": PLATFORM_COMPLIANCE_NOTICE,
        "next_action": None
        if acknowledged
        else "运行 douyin-mcp acknowledge-platform-risk --yes 后再启动登录或同步。",
    }


def record_platform_risk_acknowledgement(data_dir: Path) -> dict[str, Any]:
    """Persist an explicit, versioned acknowledgement in the local data directory."""

    data_dir.mkdir(parents=True, exist_ok=True)
    target = data_dir / ACKNOWLEDGEMENT_FILENAME
    temporary = target.with_suffix(".tmp")
    payload = {
        "version": ACKNOWLEDGEMENT_VERSION,
        "acknowledged_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "terms_url": DOUYIN_TERMS_URL,
        "statement": ACKNOWLEDGEMENT_STATEMENT,
    }
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)
    return platform_compliance_status(data_dir)


def require_platform_risk_acknowledgement(data_dir: Path) -> None:
    """Block browser automation until the current risk notice is acknowledged."""

    status = platform_compliance_status(data_dir)
    if status["acknowledged"]:
        return
    raise AppError(
        PLATFORM_TERMS_ACKNOWLEDGEMENT_REQUIRED,
        "启动浏览器自动化前必须明确确认平台条款风险。",
        retryable=True,
        extra={"platform_compliance": status},
    )


def _read_acknowledgement(data_dir: Path) -> dict[str, Any] | None:
    target = data_dir / ACKNOWLEDGEMENT_FILENAME
    if not target.is_file():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None
