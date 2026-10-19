class Account:
    def __init__(self, account_id: str, owner: str) -> None:
        self._id = account_id
        self._owner = owner
        self._tags: tuple[str, ...] = ()

    @property
    def id(self) -> str:
        return self._id

    @property
    def owner(self) -> str:
        return self._owner

    @owner.setter
    def owner(self, value: str) -> None:
        if not value:
            raise ValueError("owner is required")
        self._owner = value

    @property
    def tags(self) -> tuple[str, ...]:
        return self._tags

    def tag(self, label: str) -> None:
        if label in self._tags:
            return
        self._tags = self._tags + (label,)
