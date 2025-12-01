"""Detailed test with lower threshold to show more matches."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.db import SessionLocal
from app.models.tender import Tender
from app.models.company_experience import CompanyExperience
from app.services.experience_matching import match_tender_against_experiences
from app.core.logging import get_logger
import json

logger = get_logger(__name__)


def test_detailed_comparison():
    """Detailed comparison with lower threshold."""
    db = SessionLocal()
    
    try:
        # Get tenders related to interventoría
        tenders = db.query(Tender).filter(
            Tender.object_text.isnot(None),
            Tender.object_text != "",
            (
                Tender.object_text.ilike('%interventoría%') | 
                Tender.object_text.ilike('%interventoria%') |
                Tender.object_text.ilike('%supervisión%') |
                Tender.object_text.ilike('%supervision%')
            )
        ).limit(5).all()
        
        experiences = db.query(CompanyExperience).filter(
            CompanyExperience.keywords.isnot(None),
            CompanyExperience.keywords != ""
        ).all()
        
        if not tenders or not experiences:
            print("❌ No hay suficientes datos para el test")
            return
        
        print("=" * 80)
        print("🔍 TEST DETALLADO: Matching Híbrido IA (umbral 50%)")
        print("=" * 80)
        print(f"\n📊 Datos: {len(tenders)} licitaciones, {len(experiences)} experiencias\n")
        
        total_matches = 0
        detailed_results = []
        
        for tender in tenders:
            print(f"{'='*80}")
            print(f"📋 LICITACIÓN: {tender.entity_name}")
            print(f"   📍 {tender.department or 'N/A'}")
            print(f"   💰 ${tender.amount:,.0f} COP" if tender.amount else "   💰 N/A")
            print(f"   📝 {tender.object_text[:120]}...")
            print()
            
            # Test with 50% threshold (lower to see more matches)
            score, matches = match_tender_against_experiences(
                tender, experiences, min_score=0.50
            )
            
            if matches:
                print(f"   ✅ {len(matches)} matches encontrados (score ≥ 0.50)")
                print()
                
                for i, match in enumerate(matches[:3], 1):  # Show top 3
                    print(f"   🎯 Match #{i} (Score: {match['score']:.3f}):")
                    print(f"      Experiencia: {match['project_description'][:80]}...")
                    print(f"      Entidad: {match.get('contracting_entity', 'N/A')}")
                    print(f"      Desglose:")
                    scores = match.get('scores', {})
                    print(f"         • Semántica (IA): {scores.get('semantic', 0):.3f} (40%)")
                    print(f"         • Keywords: {scores.get('keyword', 0):.3f} (20%)")
                    print(f"         • Monto: {scores.get('amount', 0):.3f} (20%)")
                    print(f"         • Entidad: {scores.get('entity', 0):.3f} (10%)")
                    print(f"         • Ubicación: {scores.get('location', 0):.3f} (10%)")
                    print(f"         • Categoría: {scores.get('category', 0):.3f}")
                    print()
                
                total_matches += len(matches)
                detailed_results.append({
                    'tender': tender.entity_name,
                    'matches': len(matches),
                    'best_score': score,
                    'top_match': matches[0] if matches else None
                })
            else:
                print(f"   ❌ No matches encontrados (score < 0.50)")
                print()
        
        # Summary
        print("=" * 80)
        print("📊 RESUMEN")
        print("=" * 80)
        print(f"\n   Total matches encontrados: {total_matches}")
        print(f"   Licitaciones con matches: {len(detailed_results)}/{len(tenders)}")
        
        if detailed_results:
            avg_score = sum(r['best_score'] for r in detailed_results) / len(detailed_results)
            print(f"   Score promedio: {avg_score:.3f}")
            
            # Show contribution of each component
            print(f"\n   📈 Contribución promedio de cada componente:")
            semantic_avg = sum(
                r['top_match']['scores'].get('semantic', 0) 
                for r in detailed_results if r['top_match']
            ) / len(detailed_results)
            keyword_avg = sum(
                r['top_match']['scores'].get('keyword', 0) 
                for r in detailed_results if r['top_match']
            ) / len(detailed_results)
            amount_avg = sum(
                r['top_match']['scores'].get('amount', 0) 
                for r in detailed_results if r['top_match']
            ) / len(detailed_results)
            
            print(f"      • Semántica (IA): {semantic_avg:.3f} ← Entiende significado")
            print(f"      • Keywords: {keyword_avg:.3f} ← Matching de palabras")
            print(f"      • Monto: {amount_avg:.3f} ← Comparación financiera")
        
        print("\n" + "=" * 80)
        print("✅ Test completado")
        print("=" * 80)
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        print(f"❌ Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    test_detailed_comparison()



