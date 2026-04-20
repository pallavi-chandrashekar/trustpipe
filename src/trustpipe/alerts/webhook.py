"""Webhook and Slack alerts for trust score drops and integrity failures.

Usage:
    from trustpipe.alerts.webhook import AlertManager, SlackAlert, WebhookAlert

    alerts = AlertManager()
    alerts.add(SlackAlert(webhook_url="https://hooks.slack.com/..."))
    alerts.add(WebhookAlert(url="https://myapp.com/api/alerts"))

    # Check and alert (call after scoring)
    alerts.check_score(dataset_name="training_set", score=score, threshold=70)
    alerts.check_integrity(verify_result=result)

    # Or wire into TrustPipe config:
    # trustpipe.yaml:
    #   alerts:
    #     slack_webhook: https://hooks.slack.com/services/...
    #     webhook_url: https://myapp.com/api/alerts
    #     score_threshold: 70
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError


class Alert(ABC):
    """Base class for alert destinations."""

    @abstractmethod
    def send(self, message: dict[str, Any]) -> bool:
        """Send an alert. Returns True if successful."""
        ...


class WebhookAlert(Alert):
    """Send alerts to a generic webhook URL (POST JSON)."""

    def __init__(self, url: str, headers: Optional[dict[str, str]] = None) -> None:
        self._url = url
        self._headers = headers or {}

    def send(self, message: dict[str, Any]) -> bool:
        try:
            payload = json.dumps(message, default=str).encode()
            headers = {"Content-Type": "application/json", **self._headers}
            req = Request(self._url, data=payload, headers=headers, method="POST")
            with urlopen(req, timeout=10) as resp:
                return 200 <= resp.status < 300
        except (URLError, Exception):
            return False


class SlackAlert(Alert):
    """Send alerts to Slack via incoming webhook."""

    def __init__(self, webhook_url: str) -> None:
        self._url = webhook_url

    def send(self, message: dict[str, Any]) -> bool:
        event = message.get("event", "unknown")
        dataset = message.get("dataset", "unknown")

        if event == "score_drop":
            score = message.get("score", 0)
            threshold = message.get("threshold", 70)
            grade = message.get("grade", "?")
            text = f":warning: *TrustPipe Alert — Score Drop*\n\n" \
                   f"Dataset: `{dataset}`\n" \
                   f"Score: *{score}/100* ({grade}) — below threshold of {threshold}\n"
            if message.get("warnings"):
                text += "\nIssues:\n"
                for w in message["warnings"][:5]:
                    text += f"• {w}\n"

        elif event == "integrity_failure":
            failed = message.get("failed_count", 0)
            total = message.get("total", 0)
            text = f":rotating_light: *TrustPipe Alert — Integrity Failure*\n\n" \
                   f"Project: `{message.get('project', 'default')}`\n" \
                   f"Failed records: *{failed}/{total}*\n" \
                   f"Chain may be compromised. Run `trustpipe verify` for details."

        else:
            text = f":bell: *TrustPipe Alert*\n\n```{json.dumps(message, indent=2, default=str)}```"

        slack_payload = {"text": text}
        try:
            data = json.dumps(slack_payload).encode()
            req = Request(self._url, data=data, headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except (URLError, Exception):
            return False


class AlertManager:
    """Manages multiple alert destinations and triggers."""

    def __init__(self) -> None:
        self._alerts: list[Alert] = []

    def add(self, alert: Alert) -> None:
        self._alerts.append(alert)

    def check_score(
        self,
        dataset_name: str,
        score: Any,
        threshold: int = 70,
    ) -> list[bool]:
        """Alert if trust score is below threshold."""
        composite = score.composite if hasattr(score, "composite") else score
        grade = score.grade if hasattr(score, "grade") else "?"
        warnings = score.warnings if hasattr(score, "warnings") else []

        if composite >= threshold:
            return []  # no alert needed

        message = {
            "event": "score_drop",
            "dataset": dataset_name,
            "score": composite,
            "grade": grade,
            "threshold": threshold,
            "warnings": warnings,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return [a.send(message) for a in self._alerts]

    def check_integrity(self, verify_result: dict[str, Any]) -> list[bool]:
        """Alert if chain integrity check fails."""
        if verify_result.get("integrity") == "OK":
            return []

        message = {
            "event": "integrity_failure",
            "project": verify_result.get("project", "default"),
            "total": verify_result.get("total", 0),
            "failed_count": verify_result.get("failed", 0),
            "failed_ids": verify_result.get("failed_ids", [])[:10],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return [a.send(message) for a in self._alerts]

    def send_custom(self, message: dict[str, Any]) -> list[bool]:
        """Send a custom alert message."""
        return [a.send(message) for a in self._alerts]
