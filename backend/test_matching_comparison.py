"""Test script to compare old vs new hybrid matching approach."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.db import SessionLocal
from app.models.tender import Tender
from app.models.company_experience import CompanyExperience
from app.services.experience_matching import (
    match_tender_against_experiences,
    calculate_semantic_similarity,
    SEMANTIC_AI_AVAILABLE
)
from app.core.logging import get_logger
import json

logger = get_logger(__name__)


def calculate_old_matching_score(tender: Tender, experience: CompanyExperience) -> float:
    """
    Simulate the OLD matching algorithm (before improvements).
    This is a simplified version of what it was before.
    """
    # Old algorithm: simple keyword matching only
    tender_text = (tender.object_text or "").lower()
    experience_keywords = json.loads(experience.keywords) if experience.keywords else []
    
    if not experience_keywords:
        return 0.0
    
    # Simple keyword count (no synonyms)
    matches = sum(1 for keyword in experience_keywords if keyword in tender_text)
    
    if matches == 0:
        return 0.0
    
    # Simple ratio
    match_ratio = matches / len(experience_keywords)
    
    # Old weights (simplified)
    keyword_score = match_ratio
    amount_score = 0.5  # Neutral (no inflation adjustment)
    entity_score = 0.5   # Neutral (no normalization)
    location_score = 0.5  # Not considered
    category_score = 0.5  # Neutral
    
    # Old total (only keywords mattered)
    total_score = (
        0.50 * keyword_score +  # Only keywords
        0.25 * amount_score +
        0.15 * entity_score +
        0.10 * category_score
    )
    
    return total_score


def test_matching_comparison():
    """Compare old vs new matching approach."""
    db = SessionLocal()
    
    try:
        # Get tenders related to interventoría/supervisión (more relevant for testing)
        tenders = db.query(Tender).filter(
            Tender.object_text.isnot(None),
            Tender.object_text != "",
            (
                Tender.object_text.ilike('%interventoría%') | 
                Tender.object_text.ilike('%interventoria%') |
                Tender.object_text.ilike('%supervisión%') |
                Tender.object_text.ilike('%supervision%') |
                Tender.object_text.ilike('%vial%') |
                Tender.object_text.ilike('%carretera%')
            )
        ).limit(10).all()
        
        # If not enough, get any tenders
        if len(tenders) < 5:
            tenders = db.query(Tender).filter(
                Tender.object_text.isnot(None),
                Tender.object_text != ""
            ).limit(10).all()
        
        # Get experiences
        experiences = db.query(CompanyExperience).filter(
            CompanyExperience.keywords.isnot(None),
            CompanyExperience.keywords != ""
        ).all()
        
        if not tenders:
            print("❌ No tenders found in database")
            return
        
        if not experiences:
            print("❌ No experiences found in database")
            return
        
        print("=" * 80)
        print("🧪 TEST: Comparación Matching Antiguo vs Nuevo (Híbrido IA)")
        print("=" * 80)
        print(f"\n📊 Datos:")
        print(f"   • Tenders a probar: {len(tenders)}")
        print(f"   • Experiencias disponibles: {len(experiences)}")
        print(f"   • IA Semántica disponible: {'✅ SÍ' if SEMANTIC_AI_AVAILABLE else '❌ NO'}")
        print()
        
        results = []
        
        for tender in tenders:
            print(f"\n{'='*80}")
            print(f"📋 LICITACIÓN: {tender.entity_name}")
            print(f"   Objeto: {tender.object_text[:100]}...")
            print(f"   Departamento: {tender.department or 'N/A'}")
            print(f"   Monto: ${tender.amount:,.0f} COP" if tender.amount else "   Monto: N/A")
            print()
            
            # OLD matching
            old_scores = []
            for exp in experiences:
                old_score = calculate_old_matching_score(tender, exp)
                if old_score >= 0.60:  # Old threshold
                    old_scores.append((exp, old_score))
            
            old_scores.sort(key=lambda x: x[1], reverse=True)
            old_matches = len(old_scores)
            old_best_score = old_scores[0][1] if old_scores else 0.0
            
            # NEW matching (hybrid)
            new_score, new_matches_list = match_tender_against_experiences(
                tender, experiences, min_score=0.60
            )
            new_matches = len(new_matches_list)
            
            # Show comparison
            print(f"   🔴 ANTIGUO:")
            print(f"      • Matches encontrados: {old_matches}")
            print(f"      • Mejor score: {old_best_score:.3f}")
            if old_scores:
                print(f"      • Mejor match: {old_scores[0][0].project_description[:60]}...")
            
            print(f"   🟢 NUEVO (Híbrido IA):")
            print(f"      • Matches encontrados: {new_matches}")
            print(f"      • Mejor score: {new_score:.3f}")
            if new_matches_list:
                best_match = new_matches_list[0]
                print(f"      • Mejor match: {best_match['project_description']}")
                print(f"      • Desglose de scores:")
                scores = best_match.get('scores', {})
                print(f"         - Semántica (IA): {scores.get('semantic', 0):.3f}")
                print(f"         - Keywords: {scores.get('keyword', 0):.3f}")
                print(f"         - Monto: {scores.get('amount', 0):.3f}")
                print(f"         - Entidad: {scores.get('entity', 0):.3f}")
                print(f"         - Ubicación: {scores.get('location', 0):.3f}")
                print(f"         - Categoría: {scores.get('category', 0):.3f}")
            
            # Calculate improvement
            if old_matches > 0 or new_matches > 0:
                score_improvement = new_score - old_best_score
                matches_improvement = new_matches - old_matches
                
                print(f"   📈 MEJORA:")
                print(f"      • Score: {score_improvement:+.3f} ({score_improvement/old_best_score*100:+.1f}%)" if old_best_score > 0 else f"      • Score: {score_improvement:+.3f} (nuevo match)")
                print(f"      • Matches: {matches_improvement:+d}")
            
            results.append({
                'tender_id': str(tender.id),
                'entity': tender.entity_name,
                'old_matches': old_matches,
                'old_best_score': old_best_score,
                'new_matches': new_matches,
                'new_best_score': new_score,
                'score_improvement': new_score - old_best_score,
                'matches_improvement': new_matches - old_matches
            })
        
        # Summary
        print(f"\n{'='*80}")
        print("📊 RESUMEN DE RESULTADOS")
        print("=" * 80)
        
        total_old_matches = sum(r['old_matches'] for r in results)
        total_new_matches = sum(r['new_matches'] for r in results)
        avg_old_score = sum(r['old_best_score'] for r in results) / len(results) if results else 0
        avg_new_score = sum(r['new_best_score'] for r in results) / len(results) if results else 0
        
        print(f"\n   Total matches encontrados:")
        print(f"   🔴 Antiguo: {total_old_matches}")
        print(f"   🟢 Nuevo:   {total_new_matches}")
        print(f"   📈 Mejora:  {total_new_matches - total_old_matches:+d} ({((total_new_matches - total_old_matches) / total_old_matches * 100) if total_old_matches > 0 else float('inf'):+.1f}%)")
        
        print(f"\n   Score promedio:")
        print(f"   🔴 Antiguo: {avg_old_score:.3f}")
        print(f"   🟢 Nuevo:   {avg_new_score:.3f}")
        print(f"   📈 Mejora:  {avg_new_score - avg_old_score:+.3f} ({((avg_new_score - avg_old_score) / avg_old_score * 100) if avg_old_score > 0 else float('inf'):+.1f}%)")
        
        # Cases improved
        improved_cases = sum(1 for r in results if r['new_best_score'] > r['old_best_score'])
        new_matches_found = sum(1 for r in results if r['new_matches'] > r['old_matches'])
        
        print(f"\n   Casos mejorados:")
        print(f"   • Score mejorado: {improved_cases}/{len(results)} ({improved_cases/len(results)*100:.1f}%)")
        print(f"   • Nuevos matches encontrados: {new_matches_found}/{len(results)} ({new_matches_found/len(results)*100:.1f}%)")
        
        print(f"\n{'='*80}")
        print("✅ Test completado")
        print("=" * 80)
        
    except Exception as e:
        logger.error(f"Error in test: {e}", exc_info=True)
        print(f"❌ Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    test_matching_comparison()

