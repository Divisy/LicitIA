"""API endpoints for user feedback."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.feedback import Feedback, FeedbackType, FeedbackStatus
from datetime import datetime
from typing import Optional
import json

router = APIRouter()


class FeedbackCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    company: Optional[str] = None
    type: FeedbackType
    score: Optional[int] = None  # For NPS: 0-10
    message: str
    context: Optional[dict] = None  # Page, action, etc.


class FeedbackResponse(BaseModel):
    id: int
    email: str
    name: Optional[str]
    company: Optional[str]
    type: str
    score: Optional[int]
    message: str
    context: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackStats(BaseModel):
    total: int
    by_type: dict[str, int]
    average_nps: Optional[float]
    by_status: dict[str, int]


@router.post("/feedback", response_model=FeedbackResponse, status_code=201)
async def create_feedback(feedback: FeedbackCreate, db: Session = Depends(get_db)):
    """
    Create a new feedback entry.
    """
    try:
        # Validate NPS score if type is NPS
        if feedback.type == FeedbackType.NPS:
            if feedback.score is None or not (0 <= feedback.score <= 10):
                raise HTTPException(
                    status_code=400,
                    detail="NPS score must be between 0 and 10"
                )
        
        context_str = json.dumps(feedback.context) if feedback.context else None
        
        new_feedback = Feedback(
            email=feedback.email,
            name=feedback.name,
            company=feedback.company,
            type=feedback.type,
            score=feedback.score,
            message=feedback.message,
            context=context_str,
            status=FeedbackStatus.NEW,
        )
        
        db.add(new_feedback)
        db.commit()
        db.refresh(new_feedback)
        
        return new_feedback
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating feedback: {str(e)}")


@router.get("/feedback", response_model=list[FeedbackResponse])
async def list_feedback(
    email: Optional[str] = None,
    type: Optional[FeedbackType] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List feedback entries. Can filter by email and type.
    """
    query = db.query(Feedback)
    
    if email:
        query = query.filter(Feedback.email == email)
    if type:
        query = query.filter(Feedback.type == type)
    
    feedbacks = query.order_by(Feedback.created_at.desc()).offset(skip).limit(limit).all()
    return feedbacks


@router.get("/feedback/stats", response_model=FeedbackStats)
async def get_feedback_stats(db: Session = Depends(get_db)):
    """
    Get feedback statistics.
    """
    total = db.query(Feedback).count()
    
    # Count by type
    by_type = {}
    for feedback_type in FeedbackType:
        count = db.query(Feedback).filter(Feedback.type == feedback_type).count()
        by_type[feedback_type.value] = count
    
    # Average NPS
    nps_feedbacks = db.query(Feedback).filter(
        Feedback.type == FeedbackType.NPS,
        Feedback.score.isnot(None)
    ).all()
    average_nps = None
    if nps_feedbacks:
        scores = [f.score for f in nps_feedbacks if f.score is not None]
        if scores:
            average_nps = sum(scores) / len(scores)
    
    # Count by status
    by_status = {}
    for status in FeedbackStatus:
        count = db.query(Feedback).filter(Feedback.status == status).count()
        by_status[status.value] = count
    
    return FeedbackStats(
        total=total,
        by_type=by_type,
        average_nps=average_nps,
        by_status=by_status
    )

