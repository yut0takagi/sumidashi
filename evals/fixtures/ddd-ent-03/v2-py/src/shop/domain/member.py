class Member:
    def __init__(self, member_id: str, name: str) -> None:
        self.id = member_id
        self.name = name
        self._rank = "regular"
        self._points = 0

    @property
    def rank(self) -> str:
        return self._rank

    @rank.setter
    def rank(self, value: str) -> None:
        self._rank = value

    def set_points(self, points: int) -> None:
        self._points = points

    def add_points(self, points: int) -> None:
        if points <= 0:
            raise ValueError("points must be positive")
        self._points += points
