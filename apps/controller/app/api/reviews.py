from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.review_service import ReviewService
from app.services.permission_service import PermissionChecker
from app.models.user import User

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.post("/")
async def submit_review(request: Request, session: AsyncSession = Depends(get_db)):
    """提交审核"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    body = await request.json()
    document_id = body.get("document_id")
    action = body.get("action")
    content = body.get("content")

    if not all([document_id, action]):
        raise HTTPException(status_code=400, detail="document_id and action are required")

    review_service = ReviewService(session)
    review = await review_service.submit_review(document_id, user_id, action, content)

    return JSONResponse(content={
        "id": review.id,
        "document_id": review.document_id,
        "user_id": review.user_id,
        "action": review.action,
        "content": review.content,
        "status": review.status
    })


@router.get("/")
async def get_reviews(request: Request, status: str = None, session: AsyncSession = Depends(get_db)):
    """获取审核列表"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    permission_checker = PermissionChecker(session, User(id=user_id))
    if not await permission_checker.is_admin():
        raise HTTPException(status_code=403, detail="Permission denied")

    review_service = ReviewService(session)
    reviews = await review_service.get_reviews(status)

    return JSONResponse(content={
        "reviews": [{
            "id": r.id,
            "document_id": r.document_id,
            "user_id": r.user_id,
            "action": r.action,
            "content": r.content,
            "status": r.status,
            "review_comment": r.review_comment,
            "reviewed_by": r.reviewed_by,
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None
        } for r in reviews]
    })


@router.post("/{review_id}/approve")
async def approve_review(request: Request, review_id: int, session: AsyncSession = Depends(get_db)):
    """审核通过"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    permission_checker = PermissionChecker(session, User(id=user_id))
    if not await permission_checker.is_admin():
        raise HTTPException(status_code=403, detail="Permission denied")

    body = await request.json()
    comment = body.get("comment", "")

    review_service = ReviewService(session)
    review = await review_service.approve_review(review_id, user_id, comment)

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    return JSONResponse(content={
        "id": review.id,
        "status": review.status,
        "review_comment": review.review_comment
    })


@router.post("/{review_id}/reject")
async def reject_review(request: Request, review_id: int, session: AsyncSession = Depends(get_db)):
    """审核拒绝"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    permission_checker = PermissionChecker(session, User(id=user_id))
    if not await permission_checker.is_admin():
        raise HTTPException(status_code=403, detail="Permission denied")

    body = await request.json()
    comment = body.get("reason", "")

    if not comment:
        raise HTTPException(status_code=400, detail="Reason is required for rejection")

    review_service = ReviewService(session)
    review = await review_service.reject_review(review_id, user_id, comment)

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    return JSONResponse(content={
        "id": review.id,
        "status": review.status,
        "review_comment": review.review_comment
    })
