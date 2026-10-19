from fastapi import APIRouter, HTTPException, Request

from shop.application.post_review import PostReviewCommand, post_review

router = APIRouter()
REVIEWS = []


@router.post("/products/{product_id}/reviews")
async def create_review(product_id: str, request: Request) -> dict:
    body = await request.json()
    try:
        post_review(PostReviewCommand(product_id, int(body["rating"])), REVIEWS)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "created"}
