from datetime import date, timedelta


class Period:
    def __init__(self, start: date, end: date) -> None:
        if end < start:
            raise ValueError("end must not be before start")
        self._start = start
        self._end = end

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Period)
            and self._start == other._start
            and self._end == other._end
        )

    def __hash__(self) -> int:
        return hash((self._start, self._end))

    def extend(self, days: int) -> None:
        self._end = self._end + timedelta(days=days)
