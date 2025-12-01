"""API endpoints for support tickets."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.support_ticket import SupportTicket, TicketStatus, TicketPriority, TicketCategory
from datetime import datetime
from typing import Optional
import random
import string

router = APIRouter()


def generate_ticket_number() -> str:
    """Generate a unique ticket number."""
    prefix = "LIC"
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    random_suffix = ''.join(random.choices(string.digits, k=6))
    return f"{prefix}-{timestamp}-{random_suffix}"


class TicketCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    company: Optional[str] = None
    subject: str
    message: str
    category: Optional[TicketCategory] = TicketCategory.GENERAL
    priority: Optional[TicketPriority] = TicketPriority.MEDIUM


class TicketResponse(BaseModel):
    id: int
    email: str
    name: Optional[str]
    company: Optional[str]
    subject: str
    message: str
    category: str
    priority: str
    status: str
    ticket_number: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/support/tickets", response_model=TicketResponse, status_code=201)
async def create_ticket(ticket: TicketCreate, db: Session = Depends(get_db)):
    """
    Create a new support ticket.
    """
    try:
        ticket_number = generate_ticket_number()
        
        # Ensure ticket number is unique
        while db.query(SupportTicket).filter(SupportTicket.ticket_number == ticket_number).first():
            ticket_number = generate_ticket_number()
        
        new_ticket = SupportTicket(
            email=ticket.email,
            name=ticket.name,
            company=ticket.company,
            subject=ticket.subject,
            message=ticket.message,
            category=ticket.category or TicketCategory.GENERAL,
            priority=ticket.priority or TicketPriority.MEDIUM,
            status=TicketStatus.OPEN,
            ticket_number=ticket_number,
        )
        
        db.add(new_ticket)
        db.commit()
        db.refresh(new_ticket)
        
        return new_ticket
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating ticket: {str(e)}")


@router.get("/support/tickets", response_model=list[TicketResponse])
async def list_tickets(
    email: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List support tickets. Can filter by email.
    """
    query = db.query(SupportTicket)
    
    if email:
        query = query.filter(SupportTicket.email == email)
    
    tickets = query.order_by(SupportTicket.created_at.desc()).offset(skip).limit(limit).all()
    return tickets


@router.get("/support/tickets/{ticket_number}", response_model=TicketResponse)
async def get_ticket(ticket_number: str, db: Session = Depends(get_db)):
    """
    Get a specific ticket by ticket number.
    """
    ticket = db.query(SupportTicket).filter(SupportTicket.ticket_number == ticket_number).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

