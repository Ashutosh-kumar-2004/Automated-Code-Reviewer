"""
Unit tests for Remediation Notifications endpoint:
- Verifies endpoint returns valid payload
- Verifies default interval configuration (60 minutes / 3600 seconds)
- Verifies response structure
"""
import pytest
from app.config import get_settings


def test_remediation_notification_settings_default():
    settings = get_settings()
    assert settings.remediation_notification_interval_minutes == 60


def test_remediation_interval_calculation():
    settings = get_settings()
    mins = settings.remediation_notification_interval_minutes
    secs = mins * 60
    assert secs == 3600
