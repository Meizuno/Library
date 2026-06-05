"""Event subscribers that produce notifications as a side effect.

Subscribers live here (the notification module) rather than in the
event's producer module because the side-effect is the notification
concern. The reverse dependency (notification → member.events) is
deliberate: a consumer naturally depends on the producer's event
schema, never the other way around.
"""
from library.member.events import MemberRegistered
from library.member.ports import VerificationTokenIssuer
from library.notification.models import Notification
from library.notification.ports import Notifier

_WELCOME_SUBJECT = "Welcome to the library"
_WELCOME_BODY_TEMPLATE = (
    "Hi {name},\n\n"
    "Your library account is ready. Verify your email by opening this link\n"
    "(it includes a single-use token; the verify flow accepts the token\n"
    "via POST /members/verify):\n\n"
    "{link}\n\n"
    "The link expires in 24 hours.\n\n"
    "Happy reading!"
)


class SendVerificationEmailOnRegistration:
    """Reacts to MemberRegistered by sending a welcome+verification email.

    Issues its own verification token (the event itself carries no
    email-shaped data) and composes the verify URL from the configured
    app base URL.

    Failures here do not propagate to the publishing use case — the
    InProcessEventBus catches handler exceptions. Registration succeeds
    even if SMTP is down; the failure is logged. Production setups
    would back this with an outbox + retry so dropped emails surface.
    """

    def __init__(
        self,
        notifier: Notifier,
        verification_tokens: VerificationTokenIssuer,
        app_base_url: str,
    ):
        self._notifier = notifier
        self._verification_tokens = verification_tokens
        self._app_base_url = app_base_url.rstrip("/")

    async def handle(self, event: MemberRegistered) -> None:
        token = self._verification_tokens.issue(event.member_id)
        link = f"{self._app_base_url}/members/verify?token={token}"
        await self._notifier.send(
            recipient=event.email,
            notification=Notification(
                subject=_WELCOME_SUBJECT,
                body=_WELCOME_BODY_TEMPLATE.format(
                    name=event.name, link=link
                ),
            ),
        )
