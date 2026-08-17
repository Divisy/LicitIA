"""Tender API endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime
from uuid import UUID

from app.core.db import get_db
from app.core.logging import get_logger
from app.models.tender import Tender
from app.models.tender_document import TenderDocument
from app.models.company_experience import CompanyExperience
from app.services.document_storage import get_document_storage
from app.schemas.tender import (
    TenderResponse,
    TenderListResponse,
    TenderDocumentResponse,
    TenderDocumentListResponse,
)
from app.services.experience_matching import match_tender_against_experiences, MIN_MATCH_THRESHOLD

router = APIRouter()
logger = get_logger(__name__)


@router.get("/tenders", response_model=TenderListResponse)
async def list_tenders(
    department: Optional[str] = Query(None, description="Filter by department"),
    contract_type: Optional[str] = Query(None, description="Filter by contract type (Tipo de contrato)"),
    contract_modality: Optional[str] = Query(None, description="Filter by contract modality (Modalidad de contratación)"),
    date_from: Optional[date] = Query(None, description="Filter by publication date from"),
    date_to: Optional[date] = Query(None, description="Filter by publication date to"),
    match_experience: bool = Query(False, description="Only show tenders matching company experiences"),
    only_interventoria: bool = Query(False, description="Filter by interventoría/supervisión keywords before matching (reduces processing time)"),
    min_match_score: float = Query(0.55, ge=0.0, le=1.0, description="Minimum match score (0-1), default 0.55 for better quality"),
    company_name: Optional[str] = Query(None, description="Company name for experience matching"),
    limit: int = Query(50, ge=1, le=1000, description="Number of results (higher limit allowed for experience matching)"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """List tenders with optional filters and experience matching."""
    query = db.query(Tender)
    
    # Apply filters (relevance filter removed - experience matching is the main feature)
    
    if department:
        # Search in both department and municipality fields
        # This allows users to search for cities (municipios) as well as departments
        query = query.filter(
            (Tender.department.ilike(f"%{department}%")) |
            (Tender.municipality.ilike(f"%{department}%"))
        )
    
    if contract_type:
        query = query.filter(Tender.contract_type.ilike(f"%{contract_type}%"))
    
    if contract_modality:
        query = query.filter(Tender.contract_modality.ilike(f"%{contract_modality}%"))
    
    if date_from:
        query = query.filter(Tender.publication_date >= date_from)
    
    if date_to:
        query = query.filter(Tender.publication_date <= date_to)
    
    # OPTIMIZATION: Filter by interventoría keywords BEFORE matching (reduces AI processing time)
    # This reduces the dataset from ~1,748 to ~479 tenders (27% reduction)
    if only_interventoria:
        from sqlalchemy import func, or_
        interventoria_keywords = [
            'interventoría', 'interventoria', 
            'supervisión', 'supervision'
        ]
        # Build OR conditions for each keyword
        keyword_filters = [
            func.lower(Tender.object_text).contains(keyword.lower())
            for keyword in interventoria_keywords
        ]
        query = query.filter(or_(*keyword_filters))
        # Count filtered tenders (without executing full query)
        filtered_count = query.count()
        logger.info(f"Filtered by interventoría keywords: {filtered_count} tenders remaining")
    
    # Experience matching setup
    experiences = []
    if match_experience or company_name:
        exp_query = db.query(CompanyExperience)
        if company_name:
            exp_query = exp_query.filter(CompanyExperience.company_name.ilike(f"%{company_name}%"))
        experiences = exp_query.all()
    
    # If matching is required, we need to match tenders first, then paginate
    # OPTIMIZATION: 
    # - If only_interventoria is enabled, we already filtered to ~479 tenders (much faster)
    # - But we still limit to most recent to avoid timeout with AI processing
    # Process in smaller batches for better performance
    if match_experience and experiences:
        # OPTIMIZATION: Process 100 most recent tenders (as per SOLUCION_TIMEOUT_504.md)
        # With optimizations (truncated text, normalized embeddings, batches), this should be manageable
        # Processing in batches of 50 to avoid memory issues
        MAX_TENDERS_FOR_MATCHING = 100  # Process 100 most recent tenders as per optimization doc
        all_tenders = query.order_by(
            Tender.publication_date.desc().nulls_last()
        ).limit(MAX_TENDERS_FOR_MATCHING).all()
        
        # Match and filter tenders (process in batches for better performance)
        matched_items = []
        BATCH_SIZE = 50  # Process in batches of 50 as per SOLUCION_TIMEOUT_504.md
        
        # Process in batches and stop early if we have enough matches
        for i in range(0, len(all_tenders), BATCH_SIZE):
            batch = all_tenders[i:i + BATCH_SIZE]
            for tender in batch:
                match_score, matching_experiences = match_tender_against_experiences(
                    tender, experiences, min_score=min_match_score
                )
                
                # Only include if matches threshold
                if match_score >= min_match_score:
                    tender_response = TenderResponse.model_validate(tender)
                    tender_response.experience_match_score = match_score
                    tender_response.matching_experiences = matching_experiences if matching_experiences else None
                    matched_items.append(tender_response)
            
            # Early exit if we have enough matches (optimization)
            # Only stop early if we have significantly more than needed (2x limit) to ensure good results
            # This allows pagination to work properly
            if len(matched_items) >= limit * 2:  # Stop when we have 2x the limit for better pagination
                logger.info(f"Early exit: Found {len(matched_items)} matches (target: {limit * 2})")
                break
        
        # Sort by closing_date (most distant in future first), then by match score (highest first)
        # Handle None dates by putting them at the end
        # Use a tuple where first element is 0 for None dates (so they sort last when reverse=True)
        # and 1 for dates (so they sort first)
        matched_items.sort(
            key=lambda x: (
                0 if x.closing_date is None else 1,  # Put None closing dates last
                x.closing_date if x.closing_date is not None else datetime.min,  # Most distant future first
                -(x.experience_match_score or 0.0)  # Negative for descending (highest match first)
            ),
            reverse=True  # Reverse to get most distant future dates first
        )
        
        # Now apply pagination to matched results
        total = len(matched_items)
        items = matched_items[offset:offset + limit]
        
    else:
        # Normal flow: paginate first, then match (for display purposes only)
        # Order by closing_date DESC (most distant future first), with NULL values last
        total = query.count()
        # Order by closing date DESC (most distant future first), then by entity name ASC
        tenders = query.order_by(
            Tender.closing_date.desc().nulls_last(),
            Tender.entity_name.asc()
        ).offset(offset).limit(limit).all()
        
        # Build response with match scores (optional, for display)
        items = []
        for tender in tenders:
            tender_response = TenderResponse.model_validate(tender)
            
            if experiences:
                match_score, matching_experiences = match_tender_against_experiences(
                    tender, experiences, min_score=min_match_score
                )
                tender_response.experience_match_score = match_score if match_score > 0 else None
                tender_response.matching_experiences = matching_experiences if matching_experiences else None
            
            items.append(tender_response)
        
        # Sort items by closing_date (most distant future first), then by match score (highest first)
        items.sort(
            key=lambda x: (
                0 if x.closing_date is None else 1,  # Put None closing dates last
                x.closing_date if x.closing_date is not None else datetime.min,  # Most distant future first
                -(x.experience_match_score or 0.0)  # Negative for descending (highest match first)
            ),
            reverse=True  # Reverse to get most distant future dates first
        )
    
    return TenderListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/tenders/{tender_id}", response_model=TenderResponse)
async def get_tender(
    tender_id: UUID,
    company_name: Optional[str] = Query(None, description="Company name for experience matching"),
    db: Session = Depends(get_db),
):
    """Get a single tender by ID with optional experience matching."""
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    tender_response = TenderResponse.model_validate(tender)
    
    # Add experience matching if company_name provided
    if company_name:
        experiences = db.query(CompanyExperience).filter(
            CompanyExperience.company_name.ilike(f"%{company_name}%")
        ).all()
        
        if experiences:
            match_score, matching_experiences = match_tender_against_experiences(
                tender, experiences, min_score=MIN_MATCH_THRESHOLD
            )
            tender_response.experience_match_score = match_score if match_score > 0 else None
            tender_response.matching_experiences = matching_experiences if matching_experiences else None
    
    return tender_response


@router.get("/tenders/{tender_id}/documents", response_model=TenderDocumentListResponse)
async def list_tender_documents(
    tender_id: UUID,
    db: Session = Depends(get_db),
):
    """List downloaded key documents for a tender."""
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    documents = (
        db.query(TenderDocument)
        .filter(TenderDocument.tender_id == tender_id)
        .order_by(TenderDocument.document_type, TenderDocument.file_name)
        .all()
    )

    return TenderDocumentListResponse(
        items=[TenderDocumentResponse.model_validate(doc) for doc in documents],
        total=len(documents),
    )


@router.get("/tenders/{tender_id}/documents/{document_id}/download")
async def download_tender_document(
    tender_id: UUID,
    document_id: UUID,
    db: Session = Depends(get_db),
):
    """Download a stored tender document file."""
    document = (
        db.query(TenderDocument)
        .filter(
            TenderDocument.id == document_id,
            TenderDocument.tender_id == tender_id,
        )
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    storage = get_document_storage()
    try:
        if not storage.exists(document.file_path):
            raise HTTPException(status_code=404, detail="Document file not found on server")
        return storage.build_download_response(document.file_path, document.file_name)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document path")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Document file not found on server")

