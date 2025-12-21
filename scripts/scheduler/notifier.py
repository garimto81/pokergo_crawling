"""
Slack/Teams 알림 모듈

PRD-0010: 작업 완료/실패 알림 전송
"""

from __future__ import annotations

import os
from datetime import datetime
from enum import Enum
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()


class NotificationStatus(Enum):
    """알림 상태"""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    WARNING = "WARNING"


class Notifier:
    """Slack/Teams Webhook 알림 발송기"""

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self._enabled = bool(self.webhook_url)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _get_color(self, status: NotificationStatus) -> str:
        """상태별 색상 반환"""
        colors = {
            NotificationStatus.SUCCESS: "#36a64f",  # green
            NotificationStatus.FAILED: "#dc3545",  # red
            NotificationStatus.WARNING: "#ffc107",  # yellow
        }
        return colors.get(status, "#6c757d")

    def _get_emoji(self, status: NotificationStatus) -> str:
        """상태별 이모지 반환"""
        emojis = {
            NotificationStatus.SUCCESS: ":white_check_mark:",
            NotificationStatus.FAILED: ":x:",
            NotificationStatus.WARNING: ":warning:",
        }
        return emojis.get(status, ":information_source:")

    def send(
        self,
        task_name: str,
        status: NotificationStatus,
        details: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> bool:
        """알림 전송

        Args:
            task_name: 작업 이름 (예: "NAMS_Task1_NAS_Scan")
            status: 알림 상태
            details: 추가 정보 (예: {"Duration": "12분 34초", "New Files": 15})
            error_message: 오류 메시지 (FAILED 상태일 때)

        Returns:
            성공 여부
        """
        if not self._enabled:
            print(f"[Notifier] Webhook URL 미설정 - {task_name} ({status.value})")
            return False

        details = details or {}
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Slack 메시지 포맷
        fields = [
            {"title": key, "value": str(value), "short": True}
            for key, value in details.items()
        ]

        if error_message:
            fields.append({"title": "Error", "value": error_message, "short": False})

        message = {
            "text": f"{self._get_emoji(status)} *{task_name}* - {status.value}",
            "attachments": [
                {
                    "color": self._get_color(status),
                    "fields": fields,
                    "footer": f"NAMS Scheduler | {timestamp}",
                }
            ],
        }

        try:
            response = httpx.post(
                self.webhook_url,  # type: ignore
                json=message,
                timeout=10.0,
            )
            response.raise_for_status()
            print(f"[Notifier] 알림 전송 완료: {task_name} ({status.value})")
            return True
        except httpx.HTTPError as e:
            print(f"[Notifier] 알림 전송 실패: {e}")
            return False

    def send_success(
        self,
        task_name: str,
        duration_seconds: float,
        **extra_details: Any,
    ) -> bool:
        """성공 알림 전송 (편의 메서드)"""
        minutes, seconds = divmod(int(duration_seconds), 60)
        details = {"Duration": f"{minutes}분 {seconds}초", **extra_details}
        return self.send(task_name, NotificationStatus.SUCCESS, details)

    def send_failure(
        self,
        task_name: str,
        error_message: str,
        duration_seconds: float | None = None,
        **extra_details: Any,
    ) -> bool:
        """실패 알림 전송 (편의 메서드)"""
        details: dict[str, Any] = {**extra_details}
        if duration_seconds is not None:
            minutes, seconds = divmod(int(duration_seconds), 60)
            details["Duration"] = f"{minutes}분 {seconds}초"
        return self.send(
            task_name, NotificationStatus.FAILED, details, error_message=error_message
        )


# 싱글톤 인스턴스
_notifier: Notifier | None = None


def get_notifier() -> Notifier:
    """Notifier 싱글톤 인스턴스 반환"""
    global _notifier
    if _notifier is None:
        _notifier = Notifier()
    return _notifier


if __name__ == "__main__":
    # 테스트
    notifier = get_notifier()
    print(f"Webhook enabled: {notifier.enabled}")

    if notifier.enabled:
        notifier.send_success(
            "Test_Task",
            duration_seconds=123.5,
            Files=100,
            Updated=10,
        )
