"""Tests for webhook and Slack alert system."""

from unittest.mock import MagicMock

from trustpipe.alerts.webhook import AlertManager, SlackAlert, WebhookAlert


class MockScore:
    def __init__(self, composite, grade, warnings=None):
        self.composite = composite
        self.grade = grade
        self.warnings = warnings or []


def test_alert_manager_no_alert_above_threshold():
    mgr = AlertManager()
    mock_alert = MagicMock()
    mgr.add(mock_alert)

    results = mgr.check_score("test", MockScore(85, "A"), threshold=70)
    assert results == []  # no alerts sent
    mock_alert.send.assert_not_called()


def test_alert_manager_triggers_below_threshold():
    mgr = AlertManager()
    mock_alert = MagicMock()
    mock_alert.send.return_value = True
    mgr.add(mock_alert)

    results = mgr.check_score("test", MockScore(50, "C", ["low completeness"]), threshold=70)
    assert len(results) == 1
    assert results[0] is True
    mock_alert.send.assert_called_once()

    # Verify message structure
    call_args = mock_alert.send.call_args[0][0]
    assert call_args["event"] == "score_drop"
    assert call_args["dataset"] == "test"
    assert call_args["score"] == 50
    assert call_args["threshold"] == 70


def test_alert_manager_integrity_ok_no_alert():
    mgr = AlertManager()
    mock_alert = MagicMock()
    mgr.add(mock_alert)

    results = mgr.check_integrity({"integrity": "OK", "total": 10, "failed": 0})
    assert results == []
    mock_alert.send.assert_not_called()


def test_alert_manager_integrity_failure():
    mgr = AlertManager()
    mock_alert = MagicMock()
    mock_alert.send.return_value = True
    mgr.add(mock_alert)

    results = mgr.check_integrity(
        {
            "integrity": "COMPROMISED",
            "total": 10,
            "failed": 2,
            "failed_ids": ["a", "b"],
        }
    )
    assert len(results) == 1
    call_args = mock_alert.send.call_args[0][0]
    assert call_args["event"] == "integrity_failure"
    assert call_args["failed_count"] == 2


def test_multiple_alert_destinations():
    mgr = AlertManager()
    alert1 = MagicMock()
    alert1.send.return_value = True
    alert2 = MagicMock()
    alert2.send.return_value = False
    mgr.add(alert1)
    mgr.add(alert2)

    results = mgr.check_score("test", MockScore(30, "F"), threshold=70)
    assert results == [True, False]
    assert alert1.send.call_count == 1
    assert alert2.send.call_count == 1


def test_webhook_alert_interface():
    alert = WebhookAlert(url="https://example.com/webhook")
    assert hasattr(alert, "send")


def test_slack_alert_interface():
    alert = SlackAlert(webhook_url="https://hooks.slack.com/test")
    assert hasattr(alert, "send")


def test_custom_alert():
    mgr = AlertManager()
    mock_alert = MagicMock()
    mock_alert.send.return_value = True
    mgr.add(mock_alert)

    results = mgr.send_custom({"event": "custom", "message": "hello"})
    assert len(results) == 1
    assert results[0] is True
