"""Tender ingestion service - fetches, stores, classifies, and notifies."""
from datetime import datetime, timedelta
from app.core.db import SessionLocal
from app.core.logging import get_logger
from app.models.tender import Tender, TenderSource
from app.models.subscription import Subscription
from app.services.secop_client import fetch_recent_tenders
from app.config import settings
# Classification removed - experience matching is the main approach
from app.services.notifications import send_email_alert, send_whatsapp_alert

logger = get_logger(__name__)


def fetch_and_store_new_tenders() -> None:
    """
    Main background job: fetch new tenders, classify, and send notifications.
    
    This function is called periodically by the scheduler.
    """
    db = SessionLocal()
    try:
        logger.info("=" * 60)
        logger.info("🔄 STARTING TENDER FETCH JOB (Scheduled every 2 hours)")
        logger.info("=" * 60)
        
        # Extract licitaciones published from 60 days ago
        since_timestamp = datetime.utcnow() - timedelta(days=60)
        
        logger.info(f"📅 Fetching tenders published in the last 60 days (since {since_timestamp.strftime('%Y-%m-%d %H:%M:%S')})")
        
        # Fetch from SECOP with UNSPSC code filters
        # Include multiple UNSPSC codes related to civil engineering, construction, supervision, and project management
        # 81101500: Ingeniería Civil y Arquitectura
        # 80101600: Gerencia de proyectos
        # 80111600: Servicios de ingeniería especializados
        # 72141100: Construcción de carreteras y pavimentos (includes interventoría de pavimentos)
        # 81101600: Ingeniería de construcción
        unspsc_codes = ["81101500", "80101600", "80111600", "72141100", "81101600"]
        
        all_tenders = []
        for code in unspsc_codes:
            logger.info(f"Fetching tenders with UNSPSC code {code}")
            code_tenders = fetch_recent_tenders(
                since_timestamp=since_timestamp,
                unspsc_code=code,
            )
            logger.info(f"Found {len(code_tenders)} tenders with UNSPSC {code}")
            all_tenders.extend(code_tenders)
        
        # Remove duplicates based on external_id
        seen_ids = set()
        secop_tenders = []
        for tender in all_tenders:
            if tender.external_id not in seen_ids:
                seen_ids.add(tender.external_id)
                secop_tenders.append(tender)
        
        logger.info(f"Total unique tenders found: {len(secop_tenders)} (after removing duplicates)")
        
        new_tenders = []
        updated_count = 0
        
        # Process in batches to avoid memory issues and handle duplicates better
        batch_size = 100
        for i in range(0, len(secop_tenders), batch_size):
            batch = secop_tenders[i:i + batch_size]
            
            # Get existing external_ids for this batch
            batch_external_ids = [t.external_id for t in batch]
            existing_ids = set(
                db.query(Tender.external_id)
                .filter(Tender.external_id.in_(batch_external_ids))
                .all()
            )
            existing_ids = {id[0] for id in existing_ids}  # Convert from list of tuples to set
            
            for secop_tender in batch:
                try:
                    # Check if tender already exists
                    if secop_tender.external_id in existing_ids:
                        # Update existing tender
                        existing = db.query(Tender).filter(
                            Tender.external_id == secop_tender.external_id
                        ).first()
                        
                        if existing:
                            existing.entity_name = secop_tender.entity_name
                            existing.object_text = secop_tender.object_text
                            existing.department = secop_tender.department
                            existing.municipality = secop_tender.municipality
                            existing.amount = secop_tender.amount
                            existing.publication_date = secop_tender.publication_date
                            existing.closing_date = secop_tender.closing_date
                            existing.state = secop_tender.state
                            existing.apertura_estado = secop_tender.apertura_estado
                            existing.process_url = secop_tender.process_url
                            existing.updated_at = datetime.utcnow()
                            updated_count += 1
                        continue
                    
                    # Create new tender
                    new_tender = Tender(
                        external_id=secop_tender.external_id,
                        source=TenderSource(secop_tender.source),
                        entity_name=secop_tender.entity_name,
                        object_text=secop_tender.object_text,
                        department=secop_tender.department,
                        municipality=secop_tender.municipality,
                        amount=secop_tender.amount,
                        publication_date=secop_tender.publication_date,
                        closing_date=secop_tender.closing_date,
                        state=secop_tender.state,
                        apertura_estado=secop_tender.apertura_estado,
                        process_url=secop_tender.process_url,
                        contract_type=secop_tender.contract_type,
                        contract_modality=secop_tender.contract_modality,
                        is_relevant_interventoria_vial=False,  # Will be updated by classification
                    )
                    
                    db.add(new_tender)
                    new_tenders.append(new_tender)
                
                except Exception as e:
                    logger.error(f"Error processing tender {secop_tender.external_id}: {e}")
                    continue
            
            # Commit this batch
            try:
                db.commit()
                logger.debug(f"Committed batch {i//batch_size + 1} ({len(batch)} tenders)")
            except Exception as e:
                logger.error(f"Error committing batch: {e}")
                db.rollback()
                # Try to commit individual items to identify the problematic one
                for secop_tender in batch:
                    try:
                        existing = db.query(Tender).filter(
                            Tender.external_id == secop_tender.external_id
                        ).first()
                        if not existing:
                            new_tender = Tender(
                                external_id=secop_tender.external_id,
                                source=TenderSource(secop_tender.source),
                                entity_name=secop_tender.entity_name,
                                object_text=secop_tender.object_text,
                                department=secop_tender.department,
                                municipality=secop_tender.municipality,
                                amount=secop_tender.amount,
                                publication_date=secop_tender.publication_date,
                                closing_date=secop_tender.closing_date,
                                state=secop_tender.state,
                                apertura_estado=secop_tender.apertura_estado,
                                process_url=secop_tender.process_url,
                                contract_type=secop_tender.contract_type,
                                contract_modality=secop_tender.contract_modality,
                                is_relevant_interventoria_vial=False,
                            )
                            db.merge(new_tender)  # Use merge to handle conflicts
                    except Exception as inner_e:
                        logger.warning(f"Skipping duplicate tender {secop_tender.external_id}: {inner_e}")
                        continue
                try:
                    db.commit()
                except Exception as final_e:
                    logger.error(f"Final commit error: {final_e}")
                    db.rollback()
        
        logger.info(f"✅ Stored {len(new_tenders)} new tenders, updated {updated_count} existing")
        
        # Note: Classification with OpenAI is no longer performed
        # The system now focuses on experience matching, which is more accurate and specific
        # Each company sees only tenders that match their actual experience
        
        # Commit all changes
        db.commit()
        
        logger.info(f"✅ Tender ingestion completed successfully. Experience matching is the main approach for filtering.")
        logger.info(f"⏰ Next fetch scheduled in {settings.FETCH_INTERVAL_HOURS} hours")
        logger.info("=" * 60)
        
        # Send notifications (optional - only if subscriptions are configured)
        # Note: Notifications can still use experience matching if needed
        relevant_tenders = new_tenders  # For now, use all new tenders for notifications
        for tender in relevant_tenders:
            try:
                # Find matching subscriptions
                subscriptions = db.query(Subscription).filter(
                    Subscription.active == True
                ).all()
                
                for subscription in subscriptions:
                    # Apply subscription filters
                    # Note: only_relevant filter is deprecated - experience matching is the main approach
                    # if subscription.only_relevant and not tender.is_relevant_interventoria_vial:
                    #     continue
                    
                    if subscription.min_amount and tender.amount:
                        if tender.amount < subscription.min_amount:
                            continue
                    
                    if subscription.max_amount and tender.amount:
                        if tender.amount > subscription.max_amount:
                            continue
                    
                    if subscription.departments:
                        if tender.department not in subscription.departments:
                            continue
                    
                    # Send notifications
                    send_email_alert(subscription, tender)
                    send_whatsapp_alert(subscription, tender)
            
            except Exception as e:
                logger.error(f"Error sending notifications for tender {tender.id}: {e}")
                continue
        
        logger.info("✅ Tender fetch job completed successfully")
    
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ ERROR in fetch_and_store_new_tenders: {e}", exc_info=True)
        logger.error("=" * 60)
        db.rollback()
    finally:
        db.close()

