from email.message import EmailMessage
from unittest.mock import AsyncMock, patch

import pytest

from library.notification.domain import Notification
from library.notification.infrastructure import EmailNotifier


def _make_notifier(**overrides) -> EmailNotifier:
    defaults = {
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "sender": "library@example.com",
    }
    return EmailNotifier(**{**defaults, **overrides})


_SEND_PATH = (
    "library.notification.infrastructure.email_notifier.aiosmtplib.send"
)


class TestEmailNotifierFallback:
    """When smtp_host is None (typical local-dev setup), the notifier
    logs instead of sending. No SMTP call should be attempted."""

    async def test_no_smtp_host_does_not_call_aiosmtplib(self):
        notifier = _make_notifier(smtp_host=None)
        with patch(_SEND_PATH, new_callable=AsyncMock) as mock_send:
            await notifier.send(
                "alice@example.com",
                Notification(subject="Welcome", body="Hi"),
            )
            mock_send.assert_not_called()


class TestEmailNotifierSend:
    async def test_send_calls_aiosmtplib_with_message(self):
        notifier = _make_notifier()
        with patch(_SEND_PATH, new_callable=AsyncMock) as mock_send:
            await notifier.send(
                "alice@example.com",
                Notification(subject="Welcome", body="Hi Alice"),
            )

            mock_send.assert_called_once()
            (message,), kwargs = mock_send.call_args
            assert isinstance(message, EmailMessage)
            assert message["From"] == "library@example.com"
            assert message["To"] == "alice@example.com"
            assert message["Subject"] == "Welcome"
            assert message.get_content().strip() == "Hi Alice"
            assert kwargs["hostname"] == "smtp.example.com"
            assert kwargs["port"] == 587

    async def test_credentials_forwarded_to_aiosmtplib(self):
        notifier = _make_notifier(
            username="user@example.com", password="secret"
        )
        with patch(_SEND_PATH, new_callable=AsyncMock) as mock_send:
            await notifier.send(
                "alice@example.com",
                Notification(subject="s", body="b"),
            )
            _, kwargs = mock_send.call_args
            assert kwargs["username"] == "user@example.com"
            assert kwargs["password"] == "secret"

    async def test_use_tls_true_enables_starttls(self):
        # TLS is independent of credentials: allow TLS even when anonymous.
        notifier = _make_notifier(use_tls=True)
        with patch(_SEND_PATH, new_callable=AsyncMock) as mock_send:
            await notifier.send(
                "alice@example.com",
                Notification(subject="s", body="b"),
            )
            _, kwargs = mock_send.call_args
            assert kwargs["start_tls"] is True

    async def test_use_tls_default_is_false(self):
        # Defaults to plaintext; explicit opt-in required for STARTTLS.
        notifier = _make_notifier()
        with patch(_SEND_PATH, new_callable=AsyncMock) as mock_send:
            await notifier.send(
                "alice@example.com",
                Notification(subject="s", body="b"),
            )
            _, kwargs = mock_send.call_args
            assert kwargs["start_tls"] is False

    async def test_use_tls_decoupled_from_credentials(self):
        # Authenticated but plaintext (e.g. local relay with auth).
        notifier = _make_notifier(
            username="user@example.com",
            password="secret",
            use_tls=False,
        )
        with patch(_SEND_PATH, new_callable=AsyncMock) as mock_send:
            await notifier.send(
                "alice@example.com",
                Notification(subject="s", body="b"),
            )
            _, kwargs = mock_send.call_args
            assert kwargs["start_tls"] is False
            assert kwargs["username"] == "user@example.com"

    async def test_smtp_failure_propagates(self):
        notifier = _make_notifier()
        with patch(_SEND_PATH, new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = ConnectionError("smtp down")
            with pytest.raises(ConnectionError):
                await notifier.send(
                    "alice@example.com",
                    Notification(subject="s", body="b"),
                )
