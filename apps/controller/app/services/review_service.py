from typing import Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.review import ReviewQueue


class ReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def submit_review(self, document_id: int, user_id: int, action: str, content: str) -> ReviewQueue:
        review = ReviewQueue(
            document_id=document_id,
            user_id=user_id,
            action=action,
            content=content,
            status="pending"
        )
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)
        return review

    async def get_reviews(self, status: Optional[str] = None) -> list:
        query = select(ReviewQueue)
        if status:
            query = query.where(ReviewQueue.status == status)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def approve_review(self, review_id: int, reviewer_id: int, comment: str = None) -> Optional[ReviewQueue]:
        result = await self.db.execute(select(ReviewQueue).where(ReviewQueue.id == review_id))
        review = result.scalar_one_or_none()
        if review:
            review.status = "approved"
            review.reviewed_by = reviewer_id
            review.reviewed_at = datetime.now()
            review.review_comment = comment
            await self.db.commit()
            await self.db.refresh(review)
        return review

    async def reject_review(self, review_id: int, reviewer_id: int, comment: str) -> Optional[ReviewQueue]:
        result = await self.db.execute(select(ReviewQueue).where(ReviewQueue.id == review_id))
        review = result.scalar_one_or_none()
        if review:
            review.status = "rejected"
            review.reviewed_by = reviewer_id
            review.reviewed_at = datetime.now()
            review.review_comment = comment
            await self.db.commit()
            await self.db.refresh(review)
        return review

    async def get_review(self, review_id: int) -> Optional[ReviewQueue]:
        result = await self.db.execute(select(ReviewQueue).where(ReviewQueue.id == review_id))
        return result.scalar_one_or_none()
