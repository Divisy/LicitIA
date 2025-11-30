"""SECOP API client using Socrata."""
import requests
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SecopTenderDTO(BaseModel):
    """DTO for SECOP tender data."""
    external_id: str
    entity_name: str
    object_text: str
    department: Optional[str] = None
    municipality: Optional[str] = None
    amount: Optional[float] = None
    publication_date: Optional[datetime] = None
    closing_date: Optional[datetime] = None
    state: str
    apertura_estado: Optional[str] = None  # Estado de apertura: "Abierto" o "Cerrado"
    process_url: str
    contract_type: Optional[str] = None  # Tipo de contrato
    contract_modality: Optional[str] = None  # Modalidad de contratación
    source: str


def fetch_recent_tenders(
    since_timestamp: datetime,
    keyword_filter: Optional[str] = None,
    department_filter: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    unspsc_code: Optional[str] = None,
) -> List[SecopTenderDTO]:
    """
    Fetch recent tenders from SECOP dataset via Socrata API.
    
    Args:
        since_timestamp: Only fetch tenders published after this timestamp
        keyword_filter: Optional keyword to search in object text (e.g., "interventoría", "vial")
        department_filter: Optional department name to filter by
        min_amount: Optional minimum amount filter
        max_amount: Optional maximum amount filter
        unspsc_code: Optional UNSPSC code to filter by (e.g., "81101500" for civil engineering)
        
    Returns:
        List of SecopTenderDTO objects
    """
    if not settings.SECOP_DATASET_ID:
        logger.warning("SECOP_DATASET_ID not configured, skipping fetch")
        return []
    
    base_url = f"{settings.SECOP_BASE_URL}/{settings.SECOP_DATASET_ID}.json"
    tenders = []
    limit = 1000
    offset = 0
    max_pages = 50  # Increased to fetch more pages and cover 60 days
    page_count = 0
    
    # Format timestamp for Socrata query (YYYY-MM-DD format)
    # Handle None case (when no date filter is provided)
    since_date = since_timestamp.strftime("%Y-%m-%d") if since_timestamp else None
    
    while page_count < max_pages:
        page_count += 1
        try:
            params = {
                "$limit": limit,
                "$offset": offset,
                "$order": "fecha_de_publicacion_del DESC",
            }
            
            # Filter by publication date using Socrata $where clause
            # Note: SECOP API may not apply date filters correctly, so we filter in memory
            # We only use UNSPSC filter in the query, then filter by date in memory
            where_clauses = []
            
            # UNSPSC code filter (always apply this)
            if unspsc_code:
                # Format: V1.81101500 or just 81101500
                where_clauses.append(f"codigo_principal_de_categoria LIKE '%{unspsc_code}%'")
            
            # Department filter
            if department_filter:
                where_clauses.append(f"departamento_entidad LIKE '%{department_filter}%'")
            
            # Note: We don't use date filter in $where because SECOP API may not apply it correctly
            # Instead, we filter by date in memory after fetching
            
            if where_clauses:
                params["$where"] = " AND ".join(where_clauses)
            
            # Add app token if configured
            headers = {}
            if settings.SECOP_APP_TOKEN:
                headers["X-App-Token"] = settings.SECOP_APP_TOKEN
            
            response = requests.get(base_url, params=params, headers=headers, timeout=30)
            
            # Check for 403 errors (common with restricted datasets)
            if response.status_code == 403:
                logger.warning("403 Forbidden - dataset may require app token or have query restrictions")
                logger.info("Fetching without filters and will filter in memory...")
                # Try simpler query
                simple_params = {"$limit": min(limit, 100)}
                response = requests.get(base_url, params=simple_params, headers=headers, timeout=30)
                if response.status_code != 200:
                    logger.error(f"Even simple query failed with {response.status_code}")
                    break
            
            response.raise_for_status()
            raw_data = response.json()
            
            if not raw_data:
                break
            
            # Filter by date in memory (since $where may be restricted)
            filtered_data = []
            oldest_date_in_batch = None
            newest_date_in_batch = None  # Track newest date to verify we're getting recent data
            
            for item in raw_data:
                try:
                    item_date = None
                    has_date = False
                    
                    if "fecha_de_publicacion_del" in item and item["fecha_de_publicacion_del"]:
                        date_str = str(item["fecha_de_publicacion_del"])
                        if "T" in date_str:
                            item_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                        else:
                            item_date = datetime.fromisoformat(date_str)
                        has_date = True
                        
                        # Track oldest and newest dates in this batch
                        if oldest_date_in_batch is None or item_date < oldest_date_in_batch:
                            oldest_date_in_batch = item_date
                        if newest_date_in_batch is None or item_date > newest_date_in_batch:
                            newest_date_in_batch = item_date
                    
                    # Filter by date in memory (since we don't use date filter in $where)
                    # Always require date to be >= since_timestamp when since_timestamp is provided
                    if has_date:
                        if since_timestamp:
                            if item_date < since_timestamp:
                                include_item = False
                            else:
                                include_item = True
                        else:
                            # No date filter, include all
                            include_item = True
                    elif unspsc_code:
                        # Include items without dates when filtering by UNSPSC (will be filtered later)
                        include_item = True
                    else:
                        # Skip items without dates if no UNSPSC filter and date is required
                        include_item = False if since_timestamp else True
                    
                    if include_item:
                            # Apply additional filters
                            if keyword_filter:
                                object_text = str(item.get("descripci_n_del_procedimiento", "") + " " + 
                                                 item.get("nombre_del_procedimiento", "")).lower()
                                if keyword_filter.lower() not in object_text:
                                    continue
                            
                            if department_filter:
                                dept = str(item.get("departamento_entidad", "")).lower()
                                if department_filter.lower() not in dept:
                                    continue
                            
                            if min_amount is not None:
                                amount = item.get("precio_base", 0) or item.get("valor_total_adjudicacion", 0) or 0
                                try:
                                    amount = float(amount)
                                    if amount < min_amount:
                                        continue
                                except:
                                    pass
                            
                            if max_amount is not None:
                                amount = item.get("precio_base", 0) or item.get("valor_total_adjudicacion", 0) or 0
                                try:
                                    amount = float(amount)
                                    if amount > max_amount:
                                        continue
                                except:
                                    pass
                            
                            # Filter by UNSPSC code
                            if unspsc_code:
                                # Check in codigo_principal_de_categoria
                                cat_code = str(item.get("codigo_principal_de_categoria", "")).strip()
                                # UNSPSC codes in SECOP II are in format like "V1.81101500"
                                # Check if the code appears anywhere in the category code
                                if unspsc_code in cat_code or cat_code.endswith(unspsc_code):
                                    # Match found
                                    pass
                                elif "." in cat_code:
                                    # Format is "V1.81101500" - extract the numeric part
                                    numeric_part = cat_code.split(".")[-1] if "." in cat_code else cat_code
                                    if numeric_part == unspsc_code or numeric_part.endswith(unspsc_code):
                                        # Match found
                                        pass
                                    else:
                                        continue
                                else:
                                    # No match
                                    continue
                            
                            filtered_data.append(item)
                except:
                    # If date parsing fails, still try to apply filters if provided
                    should_include = True
                    
                    # Check UNSPSC filter even without date
                    if unspsc_code:
                        cat_code = str(item.get("codigo_principal_de_categoria", "")).strip()
                        if unspsc_code in cat_code or cat_code.endswith(unspsc_code):
                            pass  # Match found
                        elif "." in cat_code:
                            numeric_part = cat_code.split(".")[-1] if "." in cat_code else cat_code
                            if numeric_part == unspsc_code or numeric_part.endswith(unspsc_code):
                                pass  # Match found
                            else:
                                should_include = False
                        else:
                            should_include = False
                    
                    # Check keyword filter
                    if should_include and keyword_filter:
                        object_text = str(item.get("descripci_n_del_procedimiento", "") + " " + 
                                         item.get("nombre_del_procedimiento", "")).lower()
                        if keyword_filter.lower() not in object_text:
                            should_include = False
                    
                    if should_include:
                        filtered_data.append(item)
            
            data = filtered_data
            
            # Log date range for this batch
            if newest_date_in_batch and oldest_date_in_batch:
                logger.debug(f"📅 Batch {page_count}: newest={newest_date_in_batch.strftime('%Y-%m-%d')}, oldest={oldest_date_in_batch.strftime('%Y-%m-%d')}, filtered={len(data)} items")
            
            # Check if we should stop pagination
            # IMPORTANT: SECOP orders by fecha_de_publicacion_del DESC (newest first)
            # So we should continue paginating until we've gotten all recent data
            # Only stop if:
            # 1. We got no data in this batch AND it's the last page
            # 2. The oldest date in batch is significantly older than since_timestamp (with buffer)
            should_stop = False
            
            # If we have dates in this batch, check if we should continue
            if oldest_date_in_batch and newest_date_in_batch:
                # If newest date is still recent, continue (might be more pages with even newer data)
                if newest_date_in_batch >= since_timestamp:
                    # Still getting recent data, continue pagination
                    logger.debug(f"Batch {page_count}: newest={newest_date_in_batch.strftime('%Y-%m-%d')} is recent, continuing...")
                    should_stop = False
                elif oldest_date_in_batch < since_timestamp - timedelta(days=1):
                    # Oldest date is more than 1 day older than threshold, likely past the range
                    logger.info(f"Reached data older than threshold (oldest: {oldest_date_in_batch.strftime('%Y-%m-%d')} < {since_timestamp.strftime('%Y-%m-%d')}), stopping pagination")
                    should_stop = True
                else:
                    # Mixed dates - continue to be safe
                    logger.debug(f"Batch {page_count}: mixed dates (newest: {newest_date_in_batch.strftime('%Y-%m-%d')}, oldest: {oldest_date_in_batch.strftime('%Y-%m-%d')}), continuing...")
                    should_stop = False
            elif len(data) == 0 and len(raw_data) < limit:
                # No more pages and no matching data
                logger.info("No more pages and no matching data found")
                should_stop = True
            
            # Only stop if we got fewer results AND we've reached dates older than threshold
            # Don't stop just because we got fewer results - there might be more recent data
            if len(raw_data) < limit:
                logger.info(f"Got fewer results than limit ({len(raw_data)} < {limit})")
                if oldest_date_in_batch:
                    if oldest_date_in_batch < since_timestamp:
                        logger.info(f"Last page reached and oldest date ({oldest_date_in_batch}) is older than threshold ({since_timestamp}), stopping")
                        should_stop = True
                    else:
                        logger.warning(f"Last page reached but oldest date ({oldest_date_in_batch}) is still recent (>= {since_timestamp}). SECOP API may be limiting results. Continuing to check for more pages...")
                        # Continue to next page to see if there's more data
                else:
                    # No dates in batch, but got fewer results - might be last page
                    logger.info("Last page reached (no dates in batch to verify)")
                    should_stop = True
            
            # Map SECOP II fields to our DTO (even if empty, to continue pagination if needed)
            # Field mappings based on actual SECOP II dataset structure
            for item in data:
                try:
                    # Extract publication date (SECOP II: fecha_de_publicacion_del)
                    pub_date = None
                    if "fecha_de_publicacion_del" in item and item["fecha_de_publicacion_del"]:
                        try:
                            # SECOP II format: 2018-01-22T00:00:00.000
                            date_str = str(item["fecha_de_publicacion_del"])
                            if "T" in date_str:
                                pub_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            else:
                                pub_date = datetime.fromisoformat(date_str)
                        except Exception as e:
                            logger.debug(f"Error parsing publication date: {e}")
                            pass
                    
                    # Extract closing date (fecha de presentación de ofertas)
                    # SECOP II has fecha_de_recepcion_de which is the deadline for submitting offers
                    closing_date = None
                    
                    # First priority: Use fecha_de_recepcion_de (reception date = deadline for offers)
                    if "fecha_de_recepcion_de" in item and item["fecha_de_recepcion_de"]:
                        try:
                            date_str = str(item["fecha_de_recepcion_de"])
                            if "T" in date_str:
                                closing_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            else:
                                closing_date = datetime.fromisoformat(date_str)
                        except Exception as e:
                            logger.debug(f"Error parsing fecha_de_recepcion_de: {e}")
                            pass
                    
                    # Second priority: Use fecha_de_apertura_de_respuesta (opening date, usually close to closing)
                    if not closing_date and "fecha_de_apertura_de_respuesta" in item and item["fecha_de_apertura_de_respuesta"]:
                        try:
                            date_str = str(item["fecha_de_apertura_de_respuesta"])
                            if "T" in date_str:
                                closing_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            else:
                                closing_date = datetime.fromisoformat(date_str)
                        except Exception as e:
                            logger.debug(f"Error parsing fecha_de_apertura_de_respuesta: {e}")
                            pass
                    
                    # Third priority: Use fecha_de_ultima_publicaci if it's different from publication date
                    if not closing_date and "fecha_de_ultima_publicaci" in item and item["fecha_de_ultima_publicaci"]:
                        try:
                            date_str = str(item["fecha_de_ultima_publicaci"])
                            if "T" in date_str:
                                ultima_publicacion = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                                # Only use it if it's different from publication date
                                if pub_date and ultima_publicacion.date() != pub_date.date():
                                    closing_date = ultima_publicacion
                        except Exception as e:
                            logger.debug(f"Error parsing fecha_de_ultima_publicaci: {e}")
                            pass
                    
                    # Last resort: Calculate from duracion (but this is less accurate)
                    # Note: duracion usually refers to contract duration, not deadline for offers
                    if not closing_date and pub_date and "duracion" in item and item["duracion"]:
                        try:
                            duracion = int(item["duracion"])
                            unidad_duracion = item.get("unidad_de_duracion", "").lower()
                            
                            # Only use duration if it's in days and seems reasonable (less than 90 days)
                            # This is a fallback, as duration usually refers to contract duration
                            if ("día" in unidad_duracion or "dia" in unidad_duracion) and duracion <= 90:
                                closing_date = pub_date + timedelta(days=duracion)
                        except (ValueError, TypeError):
                            pass
                    
                    # Extract amount (SECOP II: precio_base or valor_total_adjudicacion)
                    amount = None
                    if "precio_base" in item and item.get("precio_base"):
                        try:
                            amount = float(item["precio_base"])
                        except:
                            pass
                    
                    # If precio_base is 0 or missing, try valor_total_adjudicacion
                    if (not amount or amount == 0) and "valor_total_adjudicacion" in item:
                        try:
                            adj_value = float(item["valor_total_adjudicacion"])
                            if adj_value > 0:
                                amount = adj_value
                        except:
                            pass
                    
                    # Extract process URL (SECOP II: urlproceso is a dict with 'url' key)
                    process_url = ""
                    if "urlproceso" in item:
                        url_data = item["urlproceso"]
                        if isinstance(url_data, dict) and "url" in url_data:
                            process_url = url_data["url"]
                        elif isinstance(url_data, str):
                            process_url = url_data
                    
                    # Build object text from procedure description
                    object_text = ""
                    if "descripci_n_del_procedimiento" in item and item["descripci_n_del_procedimiento"]:
                        object_text = str(item["descripci_n_del_procedimiento"])
                    elif "nombre_del_procedimiento" in item and item["nombre_del_procedimiento"]:
                        object_text = str(item["nombre_del_procedimiento"])
                    
                    # Get state (SECOP II: estado_del_procedimiento or estado_resumen)
                    state = "Unknown"
                    if "estado_del_procedimiento" in item and item["estado_del_procedimiento"]:
                        state = str(item["estado_del_procedimiento"])
                    elif "estado_resumen" in item and item["estado_resumen"]:
                        state = str(item["estado_resumen"])
                    
                    # Get apertura estado (estado_de_apertura_del_proceso)
                    apertura_estado = None
                    if "estado_de_apertura_del_proceso" in item and item["estado_de_apertura_del_proceso"]:
                        apertura_estado = str(item["estado_de_apertura_del_proceso"])
                    
                    # Get contract type and modality
                    contract_type = item.get("tipo_de_contrato")
                    contract_modality = item.get("modalidad_de_contratacion")
                    
                    tender_dto = SecopTenderDTO(
                        external_id=str(item.get("id_del_proceso", "")),
                        entity_name=str(item.get("entidad", "Unknown")),
                        object_text=object_text,
                        department=item.get("departamento_entidad"),
                        municipality=item.get("ciudad_entidad"),
                        amount=amount,
                        publication_date=pub_date,
                        closing_date=closing_date,
                        state=state,
                        apertura_estado=apertura_estado,
                        process_url=process_url,
                        contract_type=str(contract_type) if contract_type else None,
                        contract_modality=str(contract_modality) if contract_modality else None,
                        source="SECOP_II",
                    )
                    
                    # Only add if we have essential fields
                    if tender_dto.external_id and tender_dto.entity_name:
                        tenders.append(tender_dto)
                
                except Exception as e:
                    logger.warning(f"Error parsing tender item: {e}")
                    continue
            
            # Check if we should stop pagination
            if should_stop:
                break
            
            # Check if we got fewer results than limit (last page)
            # But only stop if we've also verified we're past the date threshold
            if len(raw_data) < limit:
                if oldest_date_in_batch and oldest_date_in_batch < since_timestamp:
                    logger.info(f"Reached last page of data and oldest date ({oldest_date_in_batch}) is older than threshold ({since_timestamp})")
                    break
                elif newest_date_in_batch and newest_date_in_batch >= since_timestamp:
                    # We got fewer results but still have recent dates - might be more pages
                    logger.warning(f"Got fewer results ({len(raw_data)}) but newest date ({newest_date_in_batch}) is still recent. SECOP might have pagination limits. Continuing...")
                    # Continue to next page to check
                else:
                    logger.info("Reached last page of data")
                    break
            
            offset += limit
            
            # Safety check
            if page_count >= max_pages:
                logger.info(f"Reached maximum page limit ({max_pages}), stopping pagination")
                break
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.warning("403 Forbidden - dataset may require app token or have query restrictions")
                logger.info("Attempting to fetch without date filter as fallback...")
                # Try without date filter as fallback
                params_fallback = {
                    "$limit": min(limit, 100),  # Smaller limit for fallback
                    "$offset": offset,
                    "$order": "fecha_de_publicacion_del DESC",
                }
                try:
                    response = requests.get(base_url, params=params_fallback, headers=headers, timeout=30)
                    response.raise_for_status()
                    data = response.json()
                    # Filter in memory by date
                    filtered_data = [
                        item for item in data 
                        if item.get("fecha_de_publicacion_del") and 
                        datetime.fromisoformat(str(item["fecha_de_publicacion_del"]).replace("Z", "+00:00")) >= since_timestamp
                    ]
                    data = filtered_data
                    if not data:
                        logger.info("No data found after filtering, stopping pagination")
                        break
                except:
                    logger.error(f"Fallback also failed: {e}")
                    break
            else:
                logger.error(f"HTTP error fetching from SECOP API: {e}")
                break
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching from SECOP API: {e}")
            break
        except Exception as e:
            logger.error(f"Unexpected error in fetch_recent_tenders: {e}")
            break
    
    logger.info(f"Fetched {len(tenders)} tenders from SECOP")
    return tenders

