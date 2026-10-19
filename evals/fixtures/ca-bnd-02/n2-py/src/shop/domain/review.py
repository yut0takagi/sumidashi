class Review:
    def __init__(self, product_id: str, rating: int) -> None:
        if not 1 <= rating <= 5:
            raise ValueError("rating must be 1..5")
        self._product_id = product_id
        self._rating = rating
