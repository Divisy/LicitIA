"""Tender general information extraction (US 1.4)."""
from app.services.tender_summary.service import build_tender_summary, persist_tender_summary

__all__ = ["build_tender_summary", "persist_tender_summary"]
