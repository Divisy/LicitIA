"""One-time login codes for returning users."""
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String
from app.core.db import Base


class LoginCode(Base):
    __tablename__ = "login_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, index=True)
    code_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    consumed_at = Column(DateTime, nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
