from dataclasses import dataclass


@dataclass(frozen=True)
class Notification:
    """Channel-agnostic notification payload.

    Adapters render these fields per their channel's conventions:

    - Email: subject → Subject header, body → message body
    - SMS:   body only (subject prepended or ignored)
    - Push:  subject → notification title, body → notification body
    - Slack/Discord: subject is typically the first bold/heading line

    `subject` is optional (some channels have no concept of it).
    `body` is required.
    """

    subject: str
    body: str

    def __post_init__(self):
        if not self.body:
            raise ValueError("body cannot be empty")
