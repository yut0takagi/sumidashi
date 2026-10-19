from sqlalchemy.orm import Session


class UnitOfWork:
    def __init__(self, session: Session) -> None:
        self._session = session
        self.stocks = None

    def __enter__(self) -> "UnitOfWork":
        return self

    def __exit__(self, *exc) -> None:
        self._session.rollback()

    def commit(self) -> None:
        self._session.commit()
