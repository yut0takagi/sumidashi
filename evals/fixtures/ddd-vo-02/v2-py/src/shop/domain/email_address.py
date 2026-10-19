class EmailAddress:
    def __init__(self, value: str) -> None:
        if "@" not in value:
            raise ValueError("invalid email address")
        self.value = value.lower()

    def __eq__(self, other: object) -> bool:
        return isinstance(other, EmailAddress) and self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)
