import smtplib
from enum import Enum


class MailTemplate(Enum):
    RANK_UP = "rank_up"


class SmtpMailer:
    def __init__(self, host: str) -> None:
        self._host = host

    def send(self, template: MailTemplate, to: str) -> None:
        with smtplib.SMTP(self._host) as smtp:
            smtp.sendmail("noreply@example.com", to, template.value)
