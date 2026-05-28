from typing import Protocol

from library.notification.domain.model import Notification


class Notifier(Protocol):
    """Port for delivering a `Notification` to a recipient.

    `recipient` is a channel-specific identifier; its interpretation is the
    adapter's responsibility:

    - EmailNotifier: an email address
    - SmsNotifier:   a phone number (E.164)
    - PushNotifier:  a device token
    - SlackNotifier: a channel id or member id

    Adapters consume the `Notification` payload and map its fields onto
    their channel as appropriate (see `Notification` for the contract).
    """

    async def send(
        self, recipient: str, notification: Notification
    ) -> None: ...
