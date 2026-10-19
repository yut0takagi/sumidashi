from dataclasses import dataclass


@dataclass
class Booking:
    id: str
    status: str = "tentative"

    def confirm(self) -> None:
        self.status = "confirmed"
