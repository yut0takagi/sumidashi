from dataclasses import dataclass

from shop.domain.review import Review


@dataclass(frozen=True)
class PostReviewCommand:
    product_id: str
    rating: int


def post_review(command: PostReviewCommand, reviews: list[Review]) -> Review:
    review = Review(command.product_id, command.rating)
    reviews.append(review)
    return review
