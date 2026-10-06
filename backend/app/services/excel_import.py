"""Excel import service for company experiences."""
import json
import pandas as pd
from typing import List, Tuple, Optional
from datetime import datetime
from app.core.db import SessionLocal
from app.models.company_experience import CompanyExperience
from app.services.experience_matching import extract_keywords
from app.core.logging import get_logger

logger = get_logger(__name__)


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string in various formats."""
    if not date_str or pd.isna(date_str):
        return None
    
    try:
        # Try parsing as Excel date
        if isinstance(date_str, (int, float)):
            return pd.to_datetime(date_str, origin='1899-12-30', unit='D').date()
        
        # Try common date formats
        date_str_clean = str(date_str).strip()
        for fmt in ['%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d', '%m-%d-%Y', '%d-%m-%Y']:
            try:
                return datetime.strptime(date_str_clean, fmt).date()
            except ValueError:
                continue
        
        # Try pandas auto-parse
        return pd.to_datetime(date_str_clean).date()
    except Exception as e:
        logger.warning(f"Could not parse date '{date_str}': {e}")
        return None


def parse_amount(amount_str: str) -> Optional[float]:
    """Parse amount string, handling currency symbols and commas."""
    if not amount_str or pd.isna(amount_str):
        return None
    
    try:
        # Convert to string and clean
        amount_str = str(amount_str).strip()
        
        # Remove currency symbols and spaces
        amount_str = amount_str.replace('$', '').replace(',', '').replace(' ', '')
        
        # Try to convert to float
        return float(amount_str)
    except (ValueError, AttributeError) as e:
        logger.warning(f"Could not parse amount '{amount_str}': {e}")
        return None


def import_experiences_from_excel(
    file_path: str,
    company_name: str = "BEC",
    owner_email: Optional[str] = None,
) -> Tuple[int, List[str]]:
    """
    Import company experiences from Excel file.
    
    Expected columns:
    - EMPRESA
    - CONTRATO No.
    - OBRA (project description)
    - ENTIDAD CONTRATANTE
    - FECHA FINALIZACIÓN
    - VALOR ACTUAL
    - CATEGORÍA
    - ÁREA DE LA INGENIERÍA CIVIL
    
    Args:
        file_path: Path to Excel file
        company_name: Company name (defaults to first row if not provided)
        
    Returns:
        Tuple of (imported_count, list_of_errors)
    """
    db = SessionLocal()
    errors = []
    imported = 0
    
    try:
        # Read Excel file
        logger.info(f"Reading Excel file: {file_path}")
        
        # Try reading with header=0 first (standard case)
        df = pd.read_excel(file_path, header=0)
        
        # Check if we got unnamed columns (means headers might be missing or in wrong row)
        unnamed_cols = [col for col in df.columns if str(col).startswith('Unnamed')]
        if len(unnamed_cols) > 0 and len(unnamed_cols) == len(df.columns):
            # All columns are unnamed, try to find headers in first few rows
            logger.info("All columns are unnamed, searching for header row")
            df_raw = pd.read_excel(file_path, header=None)
            
            # Look for a row that contains "obra" or similar keywords (likely the header row)
            header_row_idx = None
            for idx in range(min(5, len(df_raw))):  # Check first 5 rows
                row_values = [str(val).lower().strip() for val in df_raw.iloc[idx].values if pd.notna(val)]
                row_text = ' '.join(row_values)
                # Check if this row looks like headers (contains expected column names)
                if any(keyword in row_text for keyword in ['obra', 'empresa', 'contrato', 'entidad', 'fecha', 'valor']):
                    header_row_idx = idx
                    logger.info(f"Found potential header row at index {idx}: {row_values}")
                    break
            
            if header_row_idx is not None:
                # Use the found row as headers
                df.columns = df_raw.iloc[header_row_idx]
                df = df_raw.iloc[header_row_idx + 1:].reset_index(drop=True)
                logger.info(f"Using row {header_row_idx} as headers: {list(df.columns)}")
            else:
                # Fallback: use first row as headers
                logger.info("No header row found, using first row as headers")
                df.columns = df_raw.iloc[0]
                df = df_raw.iloc[1:].reset_index(drop=True)
                logger.info(f"Using first row as headers: {list(df.columns)}")
        
        # Normalize column names (remove extra spaces, handle NaN)
        df.columns = [str(col).strip() if pd.notna(col) and str(col) != 'nan' else f"Column_{i}" for i, col in enumerate(df.columns)]
        
        # Log all columns found in the file
        logger.info(f"All columns in Excel file: {list(df.columns)}")
        
        # Map expected column names (case-insensitive, with multiple variations)
        column_mapping = {
            'empresa': 'EMPRESA',
            'contrato no.': 'CONTRATO No.',
            'contrato no': 'CONTRATO No.',
            'contrato': 'CONTRATO No.',
            'obra': 'OBRA',
            'obras': 'OBRA',
            'descripcion': 'OBRA',
            'descripción': 'OBRA',
            'proyecto': 'OBRA',
            'entidad contratante': 'ENTIDAD CONTRATANTE',
            'entidad': 'ENTIDAD CONTRATANTE',
            'fecha finalización': 'FECHA FINALIZACIÓN',
            'fecha finalizacion': 'FECHA FINALIZACIÓN',
            'fecha': 'FECHA FINALIZACIÓN',
            'valor actual': 'VALOR ACTUAL',
            'valor': 'VALOR ACTUAL',
            'monto': 'VALOR ACTUAL',
            'categoría': 'CATEGORÍA',
            'categoria': 'CATEGORÍA',
            'área de la ingeniería civil': 'ÁREA DE LA INGENIERÍA CIVIL',
            'area de la ingenieria civil': 'ÁREA DE LA INGENIERÍA CIVIL',
            'area': 'ÁREA DE LA INGENIERÍA CIVIL',
            'área': 'ÁREA DE LA INGENIERÍA CIVIL',
        }
        
        # Find actual column names (case-insensitive, handle accents)
        actual_columns = {}
        for col in df.columns:
            # Normalize: lowercase, strip, remove accents for matching
            col_normalized = col.lower().strip()
            # Remove common accents
            col_normalized = col_normalized.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
            col_normalized = col_normalized.replace('ñ', 'n')
            
            # Try exact match first
            if col_normalized in column_mapping:
                actual_columns[column_mapping[col_normalized]] = col
            else:
                # Try partial match for OBRA (most important)
                if 'obra' in col_normalized and 'OBRA' not in actual_columns:
                    actual_columns['OBRA'] = col
                    logger.info(f"Matched '{col}' to OBRA by partial match")
        
        logger.info(f"Mapped columns: {actual_columns}")
        logger.info(f"Found expected columns: {list(actual_columns.keys())}")
        
        # Check required columns
        required = ['OBRA']  # Only OBRA is strictly required
        missing = [req for req in required if req not in actual_columns]
        if missing:
            # Provide helpful error message with available columns
            available_cols = ', '.join(df.columns.tolist())
            errors.append(
                f"Missing required columns: {', '.join(missing)}. "
                f"Available columns in file: {available_cols}"
            )
            logger.error(f"Missing required columns. Available: {available_cols}")
            return 0, errors
        
        # Process each row
        for idx, row in df.iterrows():
            try:
                # Get company name (from row or parameter)
                row_company = company_name
                if 'EMPRESA' in actual_columns:
                    emp_col = actual_columns['EMPRESA']
                    if emp_col in df.columns and not pd.isna(row[emp_col]):
                        row_company = str(row[emp_col]).strip()
                
                # Get project description (required)
                obra_col = actual_columns.get('OBRA')
                if not obra_col or obra_col not in df.columns:
                    errors.append(f"Row {idx + 2}: Missing OBRA column")
                    continue
                
                project_desc = str(row[obra_col]).strip()
                if not project_desc or project_desc.lower() in ['nan', 'none', '']:
                    errors.append(f"Row {idx + 2}: Empty OBRA")
                    continue
                
                # Extract other fields
                contract_num = None
                if 'CONTRATO No.' in actual_columns:
                    contract_col = actual_columns['CONTRATO No.']
                    if contract_col in df.columns:
                        contract_val = row[contract_col]
                        if not pd.isna(contract_val):
                            contract_num = str(contract_val).strip()
                
                contracting_entity = None
                if 'ENTIDAD CONTRATANTE' in actual_columns:
                    entity_col = actual_columns['ENTIDAD CONTRATANTE']
                    if entity_col in df.columns:
                        entity_val = row[entity_col]
                        if not pd.isna(entity_val):
                            contracting_entity = str(entity_val).strip()
                
                completion_date = None
                if 'FECHA FINALIZACIÓN' in actual_columns:
                    date_col = actual_columns['FECHA FINALIZACIÓN']
                    if date_col in df.columns:
                        completion_date = parse_date(row[date_col])
                
                amount = None
                if 'VALOR ACTUAL' in actual_columns:
                    amount_col = actual_columns['VALOR ACTUAL']
                    if amount_col in df.columns:
                        amount = parse_amount(row[amount_col])
                
                category = None
                if 'CATEGORÍA' in actual_columns:
                    cat_col = actual_columns['CATEGORÍA']
                    if cat_col in df.columns:
                        cat_val = row[cat_col]
                        if not pd.isna(cat_val):
                            category = str(cat_val).strip()
                
                engineering_area = None
                if 'ÁREA DE LA INGENIERÍA CIVIL' in actual_columns:
                    area_col = actual_columns['ÁREA DE LA INGENIERÍA CIVIL']
                    if area_col in df.columns:
                        area_val = row[area_col]
                        if not pd.isna(area_val):
                            engineering_area = str(area_val).strip()
                
                # Extract keywords from project description
                keywords = extract_keywords(project_desc)
                keywords_json = json.dumps(keywords) if keywords else None
                
                # Check if experience already exists (by contract number or description)
                existing = None
                if contract_num:
                    existing = db.query(CompanyExperience).filter(
                        CompanyExperience.contract_number == contract_num,
                        CompanyExperience.company_name == row_company,
                        *(
                            [CompanyExperience.owner_email == owner_email]
                            if owner_email
                            else []
                        ),
                    ).first()
                
                if not existing:
                    # Create new experience
                    experience = CompanyExperience(
                        company_name=row_company,
                        owner_email=owner_email,
                        contract_number=contract_num,
                        project_description=project_desc,
                        contracting_entity=contracting_entity,
                        completion_date=completion_date,
                        amount=amount,
                        category=category,
                        engineering_area=engineering_area,
                        keywords=keywords_json,
                    )
                    db.add(experience)
                    imported += 1
                else:
                    # Update existing (don't count as imported)
                    existing.project_description = project_desc
                    existing.contracting_entity = contracting_entity
                    existing.completion_date = completion_date
                    existing.amount = amount
                    existing.category = category
                    existing.engineering_area = engineering_area
                    existing.keywords = keywords_json
                    existing.updated_at = datetime.utcnow()
                    logger.info(f"Updated existing experience: {contract_num}")
            
            except Exception as e:
                error_msg = f"Row {idx + 2}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"Error processing row {idx + 2}: {e}", exc_info=True)
                continue
        
        # Commit all changes
        db.commit()
        logger.info(f"Successfully imported {imported} experiences")
        
        return imported, errors
    
    except Exception as e:
        db.rollback()
        error_msg = f"Error reading Excel file: {str(e)}"
        errors.append(error_msg)
        logger.error(error_msg, exc_info=True)
        return 0, errors
    
    finally:
        db.close()

