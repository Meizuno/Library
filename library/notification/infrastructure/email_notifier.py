from email.message import EmailMessage

import aiosmtplib

from library.notification.domain import Notification
from library.shared.infrastructure.structlog_logger import get_logger


logger = get_logger(__name__)


class EmailNotifier:
    """Notifier adapter that delivers via SMTP email.

    `recipient` is interpreted as an email address. `notification.subject`
    and `notification.body` map to the email's Subject header and message
    body respectively.

    If `smtp_host` is None (typical local-dev setup with no SMTP server),
    the email is logged at INFO level instead of sent. This keeps the dev
    experience working without requiring a real mail server, while still
    emitting an audit trail.

    `use_tls` controls whether the SMTP session upgrades via STARTTLS.
    It's independent of `username`/`password`: TLS-only relays exist
    without auth, and authenticated-but-plaintext local relays exist too.
    The caller passes the explicit choice.

    Failures during the SMTP send raise — callers (e.g. AddMemberUseCase)
    decide whether to roll back when the notification fails. The current
    setup treats notification failure as registration failure (same SQL
    session is committed only if everything succeeds).
    """

    def __init__(
        self,
        *,
        smtp_host: str | None,
        smtp_port: int,
        sender: str,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = False,
    ):
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._sender = sender
        self._username = username
        self._password = password
        self._use_tls = use_tls

    async def send(
        self, recipient: str, notification: Notification
    ) -> None:
        if self._smtp_host is None:
            logger.info(
                "email_skipped_no_smtp",
                recipient=recipient,
                subject=notification.subject,
            )
            return

        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = recipient
        message["Subject"] = notification.subject
        message.set_content(notification.body)

        await aiosmtplib.send(
            message,
            hostname=self._smtp_host,
            port=self._smtp_port,
            username=self._username,
            password=self._password,
            start_tls=self._use_tls,
        )
        logger.info(
            "email_sent",
            recipient=recipient,
            subject=notification.subject,
        )
