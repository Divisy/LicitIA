"""Feedback model for user feedback collection."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, Enum as SQLEnum
import enum
from app.core.db import Base


class FeedbackType(str, enum.Enum):
    NPS = "nps"
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"
    GENERAL = "general"
    USABILITY = "usability"


class FeedbackStatus(str, enum.Enum):
    NEW = "new"
    REVIEWED = "reviewed"
    IMPLEMENTED = "implemented"
    REJECTED = "rejected"


class Feedback(Base):
    """Feedback model for collecting user feedback."""
    
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    type = Column(SQLEnum(FeedbackType), nullable=False, default=FeedbackType.GENERAL)
    score = Column(Integer, nullable=True)  # For NPS: 0-10
    message = Column(Text, nullable=False)
    context = Column(Text, nullable=True)  # JSON string with page, action, etc.
    status = Column(SQLEnum(FeedbackStatus), nullable=False, default=FeedbackStatus.NEW)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

