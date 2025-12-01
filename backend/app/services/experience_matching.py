"""Experience matching service - matches tenders against company experiences."""
from __future__ import annotations
import json
import re
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from app.models.tender import Tender
from app.models.company_experience import CompanyExperience
from app.core.logging import get_logger

logger = get_logger(__name__)

# Try to import sentence-transformers for semantic matching
# Make it more robust to handle version compatibility issues
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SEMANTIC_AI_AVAILABLE = True
    logger.info("Semantic AI (sentence-transformers) is available")
except (ImportError, AttributeError, Exception) as e:
    SEMANTIC_AI_AVAILABLE = False
    np = None  # Set to None if not available
    logger.warning(f"Semantic AI (sentence-transformers) not available: {e}. System will use rules-based matching only.")

# Matching weights for hybrid approach (sum should be ~1.0)
# Phase 1: Improved rules-based weights
# Phase 2: Semantic AI enabled (40% weight)
WEIGHTS = {
    "semantic": 0.50 if SEMANTIC_AI_AVAILABLE else 0.00,  # 50% when AI enabled (increased for quality)
    "keyword": 0.15 if SEMANTIC_AI_AVAILABLE else 0.40,     # Reduced when AI enabled
    "amount": 0.15,    # Reduced from 0.20
    "entity": 0.10,    # Maintained
    "location": 0.10,   # Maintained
    "category": 0.00,  # Covered by semantic AI
}

# Minimum match threshold
MIN_MATCH_THRESHOLD = 0.60

# Synonyms dictionary for improved keyword matching
SYNONYMS = {
    "vial": ["vías", "vias", "carretera", "malla vial", "infraestructura vial", "ruta"],
    "interventoría": ["interventoria", "supervisión", "supervision", "control", "fiscalización"],
    "obra": ["obras", "construcción", "construccion", "proyecto", "trabajo"],
    "mantenimiento": ["conservación", "conservacion", "rehabilitación", "rehabilitacion", "reparación"],
    "mejoramiento": ["mejora", "adecuación", "adecuacion", "modernización"],
    "diseño": ["diseno", "estudio", "estudios", "planificación"],
    "técnica": ["tecnica", "ingeniería", "ingenieria", "técnico"],
    "administrativa": ["administración", "gestion", "gestión"],
    "ambiental": ["medio ambiente", "ecología", "sostenibilidad"],
    "puente": ["puentes", "viaducto", "paso elevado"],
    "infraestructura": ["infraestructuras", "equipamiento"],
}

# Entity name normalizations (common Colombian entities)
ENTITY_NORMALIZATIONS = {
    "invias": ["instituto nacional de vías", "instituto nacional de vias", "instituto nacional de vias invias"],
    "idu": ["instituto de desarrollo urbano", "instituto distrital de desarrollo urbano"],
    "idrd": ["instituto distrital de recreación y deporte", "instituto distrital de recreacion y deporte"],
    "ani": ["agencia nacional de infraestructura", "aní"],
    "findeter": ["financiera de desarrollo territorial"],
    "fondo adaptación": ["fondo de adaptación", "fondo nacional de adaptación"],
}

# Inflation rates for Colombia (IPC annual, approximate)
# Source: DANE Colombia
INFLATION_RATES = {
    2000: 8.75, 2001: 7.65, 2002: 6.99, 2003: 7.13, 2004: 5.50,
    2005: 4.85, 2006: 4.48, 2007: 5.69, 2008: 7.67, 2009: 2.00,
    2010: 3.17, 2011: 3.73, 2012: 3.23, 2013: 1.94, 2014: 3.66,
    2015: 6.77, 2016: 5.75, 2017: 4.09, 2018: 3.24, 2019: 3.80,
    2020: 1.61, 2021: 5.62, 2022: 13.12, 2023: 11.75, 2024: 7.0,  # Estimated
}


def extract_keywords(text: str) -> List[str]:
    """
    Extract relevant keywords from text for matching.
    
    Focuses on interventoría-related terms and technical keywords.
    """
    if not text:
        return []
    
    text_lower = text.lower()
    
    # Common interventoría-related keywords
    interventoria_keywords = [
        "interventoría", "interventoria", "supervisión", "supervision",
        "vial", "vías", "vias", "carretera", "malla vial",
        "obra", "obras", "construcción", "construccion",
        "mantenimiento", "mejoramiento", "rehabilitación", "rehabilitacion",
        "diseño", "diseno", "estudio", "estudios",
        "técnica", "tecnica", "administrativa", "ambiental",
        "puente", "puentes", "infraestructura",
    ]
    
    # Extract words that match our keywords
    words = re.findall(r'\b\w+\b', text_lower)
    keywords = [word for word in words if word in interventoria_keywords]
    
    # Also extract significant words (length > 5, not common stop words)
    stop_words = {"para", "del", "los", "las", "con", "por", "que", "una", "uno"}
    significant_words = [
        word for word in words 
        if len(word) > 5 and word not in stop_words and word not in keywords
    ]
    
    # Combine and deduplicate
    all_keywords = list(set(keywords + significant_words[:10]))  # Limit significant words
    
    return all_keywords


def find_keyword_with_synonyms(keyword: str, text: str) -> bool:
    """
    Check if keyword or any of its synonyms exist in text.
    
    Returns True if keyword or synonym found.
    """
    text_lower = text.lower()
    
    # Direct match
    if keyword in text_lower:
        return True
    
    # Check synonyms
    if keyword in SYNONYMS:
        for synonym in SYNONYMS[keyword]:
            if synonym in text_lower:
                return True
    
    return False


def calculate_keyword_score(tender_text: str, experience_keywords: List[str]) -> float:
    """
    Calculate keyword matching score with synonyms support.
    
    Returns score between 0.0 and 1.0.
    """
    if not experience_keywords:
        return 0.0
    
    tender_lower = tender_text.lower()
    
    # Count matches (including synonyms)
    matches = sum(1 for keyword in experience_keywords 
                  if find_keyword_with_synonyms(keyword, tender_lower))
    
    if matches == 0:
        return 0.0
    
    # Score based on percentage of keywords matched
    match_ratio = matches / len(experience_keywords)
    
    # Boost score if multiple matches (exponential)
    if matches >= 3:
        return min(1.0, match_ratio * 1.3)
    elif matches >= 2:
        return min(1.0, match_ratio * 1.2)
    
    return match_ratio


def adjust_for_inflation(amount: float, year_from: Optional[int], year_to: Optional[int]) -> float:
    """
    Adjust amount for inflation between two years.
    
    Args:
        amount: Original amount
        year_from: Year of original amount
        year_to: Target year (current year if None)
    
    Returns:
        Adjusted amount
    """
    if not year_from or not year_to or year_from >= year_to:
        return amount
    
    # Calculate cumulative inflation factor
    factor = 1.0
    for year in range(year_from + 1, year_to + 1):
        if year in INFLATION_RATES:
            factor *= (1 + INFLATION_RATES[year] / 100)
        else:
            # Use average inflation if year not in data
            avg_inflation = sum(INFLATION_RATES.values()) / len(INFLATION_RATES)
            factor *= (1 + avg_inflation / 100)
    
    return amount * factor


def calculate_amount_score(
    tender_amount: Optional[float], 
    tender_year: Optional[int],
    experience_amount: Optional[float],
    experience_year: Optional[int]
) -> float:
    """
    Calculate amount similarity score with inflation adjustment.
    
    Returns score between 0.0 and 1.0.
    """
    if not tender_amount or not experience_amount:
        return 0.5  # Neutral score if either is missing
    
    if experience_amount == 0:
        return 0.5
    
    # Adjust experience amount to tender year (or current year)
    target_year = tender_year if tender_year else datetime.now().year
    adjusted_experience = adjust_for_inflation(
        experience_amount,
        experience_year,
        target_year
    )
    
    # Calculate ratio with adjusted amount
    ratio = tender_amount / adjusted_experience if adjusted_experience > 0 else 0
    
    # More precise scoring ranges
    if 0.8 <= ratio <= 1.2:  # Very similar (±20%)
        return 1.0
    elif 0.6 <= ratio <= 1.5:  # Similar (±50%)
        return 0.9
    elif 0.4 <= ratio <= 2.0:  # Acceptable (2x)
        return 0.7
    elif 0.2 <= ratio <= 3.0:  # Wide range (3x)
        return 0.5
    elif 0.1 <= ratio <= 5.0:  # Very wide (5x)
        return 0.3
    else:
        return 0.1


def normalize_entity_name(entity_name: str) -> str:
    """
    Normalize entity name for better matching.
    
    Removes common variations and normalizes to standard form.
    """
    if not entity_name:
        return ""
    
    name_lower = entity_name.lower().strip()
    
    # Remove common prefixes/suffixes
    name_lower = re.sub(r'\s+', ' ', name_lower)  # Normalize spaces
    name_lower = re.sub(r'[^\w\s]', '', name_lower)  # Remove special chars
    
    # Check normalization dictionary
    for normalized, variants in ENTITY_NORMALIZATIONS.items():
        if name_lower == normalized:
            return normalized
        if any(variant in name_lower for variant in variants):
            return normalized
        if normalized in name_lower:
            return normalized
    
    return name_lower


def calculate_entity_score(tender_entity: str, experience_entity: Optional[str]) -> float:
    """
    Calculate entity name similarity score with normalization.
    
    Returns score between 0.0 and 1.0.
    """
    if not experience_entity:
        return 0.5  # Neutral if no experience entity
    
    # Normalize both entities
    tender_norm = normalize_entity_name(tender_entity)
    experience_norm = normalize_entity_name(experience_entity)
    
    # Exact match after normalization
    if tender_norm == experience_norm:
        return 1.0
    
    # Check if one contains the other (after normalization)
    if tender_norm in experience_norm or experience_norm in tender_norm:
        return 0.9
    
    # Word overlap with normalized names
    tender_words = set(tender_norm.split())
    experience_words = set(experience_norm.split())
    common_words = tender_words.intersection(experience_words)
    
    if len(common_words) >= 2:  # At least 2 common words
        return 0.7
    elif len(common_words) == 1:
        return 0.4
    
    # Fuzzy matching for similar names
    from difflib import SequenceMatcher
    similarity = SequenceMatcher(None, tender_norm, experience_norm).ratio()
    
    if similarity >= 0.8:
        return 0.8
    elif similarity >= 0.6:
        return 0.5
    
    return 0.0


def normalize_location(location: str) -> str:
    """
    Normalize location name for matching.
    
    Removes accents, converts to lowercase, handles common variations.
    """
    if not location:
        return ""
    
    # Remove accents and convert to lowercase
    import unicodedata
    location = unicodedata.normalize('NFD', location.lower())
    location = ''.join(c for c in location if unicodedata.category(c) != 'Mn')
    
    # Common location normalizations
    location = location.strip()
    location = re.sub(r'\s+', ' ', location)
    
    return location


def calculate_location_score(
    tender_department: Optional[str],
    tender_municipality: Optional[str],
    experience_department: Optional[str],
    experience_municipality: Optional[str]
) -> float:
    """
    Calculate geographic location similarity score.
    
    Returns score between 0.0 and 1.0.
    """
    # If no location data, return neutral score
    if not tender_department and not tender_municipality:
        return 0.3  # Lower than 0.5 because location is important
    
    if not experience_department and not experience_municipality:
        return 0.3
    
    # Normalize locations
    tender_dept_norm = normalize_location(tender_department or "")
    tender_mun_norm = normalize_location(tender_municipality or "")
    exp_dept_norm = normalize_location(experience_department or "")
    exp_mun_norm = normalize_location(experience_municipality or "")
    
    # Perfect match: same municipality
    if tender_mun_norm and exp_mun_norm:
        if tender_mun_norm == exp_mun_norm:
            return 1.0
    
    # Good match: same department
    if tender_dept_norm and exp_dept_norm:
        if tender_dept_norm == exp_dept_norm:
            return 0.8
    
    # Partial match: municipality contains department name or vice versa
    if tender_mun_norm and exp_dept_norm:
        if tender_mun_norm in exp_dept_norm or exp_dept_norm in tender_mun_norm:
            return 0.6
    
    if tender_dept_norm and exp_mun_norm:
        if tender_dept_norm in exp_mun_norm or exp_mun_norm in tender_dept_norm:
            return 0.6
    
    # No geographic match
    return 0.2  # Low score but not zero (location matters but not everything)


# Global model cache for semantic AI
_semantic_model = None

# Global cache for experience embeddings (key: experience_id, value: embedding)
_experience_embeddings_cache = {}
_experience_cache_timestamp = {}


def get_semantic_model():
    """
    Get or load the semantic model (cached, lazy loading).
    
    The model is only loaded when first needed, not during startup.
    This significantly speeds up application startup time.
    """
    global _semantic_model
    if not SEMANTIC_AI_AVAILABLE:
        return None
    
    if _semantic_model is None:
        try:
            logger.info("Loading semantic model (paraphrase-multilingual-MiniLM-L12-v2) - this may take a minute on first use...")
            print("[SEMANTIC AI] Loading model (first use) - this is normal and will be cached after loading")
            # Use cache_folder to speed up subsequent loads if possible
            _semantic_model = SentenceTransformer(
                'paraphrase-multilingual-MiniLM-L12-v2',
                device='cpu'  # Explicitly use CPU to avoid GPU issues
            )
            logger.info("Semantic model loaded successfully and cached in memory")
            print("[SEMANTIC AI] Model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading semantic model: {e}")
            print(f"[SEMANTIC AI] Error loading model: {e}")
            return None
    
    return _semantic_model


def get_experience_embedding(experience_id: str, experience_text: str) -> Optional[Any]:
    """
    Get cached embedding for an experience, or calculate and cache it.
    
    Returns embedding as numpy array, or None if error.
    """
    global _experience_embeddings_cache, _experience_cache_timestamp
    
    if not SEMANTIC_AI_AVAILABLE or not experience_text:
        return None
    
    # Check cache
    if experience_id in _experience_embeddings_cache:
        return _experience_embeddings_cache[experience_id]
    
    # Calculate and cache
    model = get_semantic_model()
    if not model:
        return None
    
    try:
        max_length = 128
        text_truncated = experience_text[:max_length] if len(experience_text) > max_length else experience_text
        
        embedding = model.encode(
            [text_truncated],
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True
        )[0]
        
        # Cache it
        _experience_embeddings_cache[experience_id] = embedding
        _experience_cache_timestamp[experience_id] = datetime.utcnow()
        
        return embedding
    except Exception as e:
        logger.error(f"Error calculating experience embedding: {e}")
        return None


def calculate_semantic_similarity(text1: str, text2: str, 
                                  cached_embedding2: Optional[Any] = None) -> float:
    """
    Calculate semantic similarity between two texts using embeddings.
    
    If cached_embedding2 is provided, reuse it instead of recalculating.
    This is the key optimization: cache experience embeddings.
    
    Returns score between 0.0 and 1.0.
    """
    if not SEMANTIC_AI_AVAILABLE:
        return 0.0
    
    if not text1 or not text2:
        return 0.0
    
    model = get_semantic_model()
    if not model:
        return 0.0
    
    try:
        # Truncate texts if too long (models have token limits)
        max_length = 128
        text1_truncated = text1[:max_length] if len(text1) > max_length else text1
        
        # Use cached embedding for text2 if available, otherwise calculate
        if cached_embedding2 is not None:
            embedding1 = model.encode(
                [text1_truncated],
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True
            )[0]
            embedding2 = cached_embedding2
        else:
            # Fallback: calculate both (slower)
            text2_truncated = text2[:max_length] if len(text2) > max_length else text2
            embeddings = model.encode(
                [text1_truncated, text2_truncated],
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            embedding1 = embeddings[0]
            embedding2 = embeddings[1]
        
        # Calculate cosine similarity (faster with normalized embeddings)
        similarity = cosine_similarity([embedding1], [embedding2])[0][0]
        
        # Ensure it's between 0 and 1
        similarity = max(0.0, min(1.0, float(similarity)))
        
        return similarity
    except Exception as e:
        logger.error(f"Error calculating semantic similarity: {e}")
        return 0.0


def calculate_category_score(tender: Tender, experience: CompanyExperience) -> float:
    """
    Calculate category/engineering area match score.
    
    Returns score between 0.0 and 1.0.
    """
    # If experience has engineering_area, check if it matches tender keywords
    if experience.engineering_area:
        area_lower = experience.engineering_area.lower()
        tender_text = (tender.object_text or "").lower()
        
        # Check for key terms in engineering area
        if "vial" in area_lower or "vias" in area_lower or "carretera" in area_lower:
            if any(term in tender_text for term in ["vial", "vias", "carretera", "malla"]):
                return 1.0
        
        if "construccion" in area_lower or "obra" in area_lower:
            if any(term in tender_text for term in ["obra", "construccion", "construcción"]):
                return 0.8
    
    # Category match - check if experience category matches tender keywords
    # No longer depends on is_relevant_interventoria_vial - matching is based on actual experience
    if experience.category and "interventoría" in experience.category.lower():
        # Check if tender text contains interventoría-related keywords
        tender_text = (tender.object_text or "").lower()
        if any(term in tender_text for term in ["interventoría", "interventoria", "supervisión", "supervision"]):
            return 1.0
    
    return 0.5  # Neutral if no specific match


def match_tender_against_experiences(
    tender: Tender,
    experiences: List[CompanyExperience],
    min_score: float = MIN_MATCH_THRESHOLD
) -> Tuple[float, List[Dict]]:
    """
    Match a tender against company experiences.
    
    Args:
        tender: The tender to match
        experiences: List of company experiences
        min_score: Minimum score to consider a match
        
    Returns:
        Tuple of (best_match_score, list_of_matching_experiences)
    """
    if not experiences:
        return 0.0, []
    
    matches = []
    
    for experience in experiences:
        # Calculate individual scores
        keyword_score = calculate_keyword_score(
            tender.object_text or "",
            json.loads(experience.keywords) if experience.keywords else []
        )
        
        amount_score = calculate_amount_score(
            float(tender.amount) if tender.amount else None,
            tender.publication_date.year if tender.publication_date else None,
            float(experience.amount) if experience.amount else None,
            experience.completion_date.year if experience.completion_date else None
        )
        
        entity_score = calculate_entity_score(
            tender.entity_name or "",
            experience.contracting_entity
        )
        
        category_score = calculate_category_score(tender, experience)
        
        # Calculate location score (NEW)
        location_score = calculate_location_score(
            tender.department,
            tender.municipality,
            experience.department,
            experience.municipality
        )
        
        # Semantic score using AI (Phase 2)
        # Compare tender object_text with experience project_description
        semantic_score = calculate_semantic_similarity(
            tender.object_text or "",
            experience.project_description or ""
        )
        
        # Calculate weighted total score (hybrid approach)
        # Phase 2: Hybrid AI + Rules (40% semantic AI, 60% rules)
        total_score = (
            WEIGHTS["semantic"] * semantic_score +  # 40% when AI enabled
            WEIGHTS["keyword"] * keyword_score +    # 20% when AI enabled, 40% otherwise
            WEIGHTS["amount"] * amount_score +       # 20%
            WEIGHTS["entity"] * entity_score +       # 10%
            WEIGHTS["location"] * location_score +    # 10%
            WEIGHTS["category"] * category_score     # 0% when AI enabled
        )
        
        # Only include if above threshold
        if total_score >= min_score:
            matches.append({
                "experience_id": str(experience.id),
                "project_description": experience.project_description[:100] + "..." if len(experience.project_description) > 100 else experience.project_description,
                "contracting_entity": experience.contracting_entity,
                "amount": float(experience.amount) if experience.amount else None,
                "score": round(total_score, 3),
                "scores": {
                    "semantic": round(semantic_score, 3),  # Will be > 0 when AI enabled
                    "keyword": round(keyword_score, 3),
                    "amount": round(amount_score, 3),
                    "entity": round(entity_score, 3),
                    "location": round(location_score, 3),  # NEW
                    "category": round(category_score, 3),
                }
            })
    
    # Sort by score descending
    matches.sort(key=lambda x: x["score"], reverse=True)
    
    # Return best score and top matches (limit to 5)
    best_score = matches[0]["score"] if matches else 0.0
    top_matches = matches[:5]
    
    return best_score, top_matches


def match_all_tenders_against_experiences(
    tenders: List[Tender],
    experiences: List[CompanyExperience],
    min_score: float = MIN_MATCH_THRESHOLD
) -> Dict[str, Tuple[float, List[Dict]]]:
    """
    Match multiple tenders against experiences.
    
    Returns a dictionary mapping tender_id to (score, matches).
    """
    results = {}
    
    for tender in tenders:
        score, matches = match_tender_against_experiences(tender, experiences, min_score)
        results[str(tender.id)] = (score, matches)
    
    return results

