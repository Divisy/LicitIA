"""Tender API endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, Form
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
from app.services.document_extraction import deduplicate_visible_documents
from app.services.secop_documents import is_archive_filename
from app.schemas.tender import (
    TenderResponse,
    TenderListResponse,
    TenderDocumentResponse,
    TenderDocumentListResponse,
)
from app.config import settings
from app.models.tender_summary import TenderSummary
from app.schemas.tender_summary import TenderSummaryResponse, TenderSummaryFieldResponse
from app.services.experience_matching import match_tender_against_experiences, MIN_MATCH_THRESHOLD
from app.services.tender_summary.contract_kind import apply_contract_kind_filter, parse_contract_kind
from app.services.tender_summary.service import build_tender_summary, persist_tender_summary
from app.services.manual_document_upload import save_manual_tender_document, validate_document_type

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
    only_interventoria: bool = Query(False, description="Deprecated: use contract_kind=interventoria"),
    contract_kind: Optional[str] = Query(
        None,
        description="Filter by category: estudios_disenos, interventoria, ejecucion_obra",
    ),
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
    
    kind = parse_contract_kind(contract_kind)
    if kind is not None:
        query = apply_contract_kind_filter(query, kind)
        logger.info("Filtered by contract_kind=%s", kind.value)
    elif only_interventoria:
        kind = parse_contract_kind("interventoria")
        if kind is not None:
            query = apply_contract_kind_filter(query, kind)
        logger.info("Filtered by only_interventoria (legacy): %s tenders", query.count())
    
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
    visible_documents = [
        document for document in documents if not is_archive_filename(document.file_name)
    ]
    visible_documents = deduplicate_visible_documents(visible_documents)

    return TenderDocumentListResponse(
        items=[TenderDocumentResponse.model_validate(doc) for doc in visible_documents],
        total=len(visible_documents),
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


@router.post(
    "/tenders/{tender_id}/documents/upload",
    response_model=TenderDocumentResponse,
    status_code=201,
)
async def upload_tender_document(
    tender_id: UUID,
    document_type: str = Form(..., description="pliego_condiciones | anexo_tecnico | presupuesto"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a missing key document manually (PDF/XLSX)."""
    if not settings.MANUAL_DOCUMENT_UPLOAD_ENABLED:
        raise HTTPException(status_code=503, detail="Manual document upload is disabled")

    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    try:
        doc_type = validate_document_type(document_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    storage = get_document_storage()
    try:
        record = await save_manual_tender_document(db, tender, doc_type, file, storage)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(
            "Manual document upload failed for tender %s: %s",
            tender.external_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to store uploaded document") from exc

    if settings.TENDER_SUMMARY_EXTRACTION_ENABLED:
        try:
            db.expire(tender)
            payload = build_tender_summary(tender)
            persist_tender_summary(db, tender, payload)
        except Exception as exc:
            logger.warning(
                "Summary refresh after manual upload failed for %s: %s",
                tender.external_id,
                exc,
            )

    return TenderDocumentResponse.model_validate(record)


@router.get("/tenders/{tender_id}/summary", response_model=TenderSummaryResponse)
async def get_tender_summary(
    tender_id: UUID,
    refresh: bool = Query(False, description="Recompute summary from stored documents"),
    db: Session = Depends(get_db),
):
    """Return extracted general tender information (US 1.4)."""
    if not settings.TENDER_SUMMARY_EXTRACTION_ENABLED:
        raise HTTPException(status_code=503, detail="Tender summary extraction is disabled")

    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    cached = None if refresh else db.query(TenderSummary).filter(TenderSummary.tender_id == tender_id).first()
    if cached and cached.summary_json:
        payload = cached.summary_json
        return TenderSummaryResponse(
            tender_id=tender.id,
            contract_kind=payload["contract_kind"],
            contract_kind_label=payload["contract_kind_label"],
            extracted_at=cached.extracted_at,
            fields=[TenderSummaryFieldResponse(**field) for field in payload["fields"]],
            cached=True,
        )

    payload = build_tender_summary(tender)
    record = persist_tender_summary(db, tender, payload)
    return TenderSummaryResponse(
        tender_id=tender.id,
        contract_kind=payload["contract_kind"],
        contract_kind_label=payload["contract_kind_label"],
        extracted_at=record.extracted_at,
        fields=[TenderSummaryFieldResponse(**field) for field in payload["fields"]],
        cached=False,
    )

