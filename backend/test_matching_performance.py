#!/usr/bin/env python3
"""Test script to measure matching performance and identify bottlenecks."""
import time
import sys
from datetime import datetime
from app.core.db import SessionLocal
from app.models.tender import Tender
from app.models.company_experience import CompanyExperience
from app.services.experience_matching import match_tender_against_experiences
from sqlalchemy import func, or_

def test_matching_performance():
    """Test matching performance with different scenarios."""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("🧪 TEST DE PERFORMANCE DE MATCHING")
        print("=" * 80)
        print()
        
        # Get experiences
        print("1. Cargando experiencias...")
        experiences = db.query(CompanyExperience).filter(
            CompanyExperience.company_name.ilike("%BEC%")
        ).all()
        print(f"   ✅ {len(experiences)} experiencias cargadas")
        print()
        
        if not experiences:
            print("❌ ERROR: No hay experiencias. Sube un Excel primero.")
            return
        
        # Test 1: Filter by interventoría keywords
        print("2. Filtrando licitaciones por keywords de interventoría...")
        interventoria_keywords = [
            'interventoría', 'interventoria', 
            'supervisión', 'supervision'
        ]
        keyword_filters = [
            func.lower(Tender.object_text).contains(keyword.lower())
            for keyword in interventoria_keywords
        ]
        
        interventoria_tenders = db.query(Tender).filter(
            or_(*keyword_filters)
        ).order_by(
            Tender.publication_date.desc().nulls_last()
        ).limit(20).all()  # Match the API limit
        
        print(f"   ✅ {len(interventoria_tenders)} licitaciones de interventoría (últimas 20 - límite del API)")
        print()
        
        if not interventoria_tenders:
            print("❌ ERROR: No hay licitaciones de interventoría.")
            return
        
        # Test 2: Measure matching time
        print("3. Probando matching con IA...")
        print(f"   Procesando {len(interventoria_tenders)} licitaciones...")
        print()
        
        start_time = time.time()
        matched_count = 0
        total_matches = 0
        batch_size = 5  # Match the API batch size
        min_score = 0.55
        limit = 50  # Match the API default limit
        
        # Process in batches (like the API does)
        for i in range(0, len(interventoria_tenders), batch_size):
            batch = interventoria_tenders[i:i + batch_size]
            batch_start = time.time()
            
            for tender in batch:
                match_score, matching_experiences = match_tender_against_experiences(
                    tender, experiences, min_score=min_score
                )
                
                if match_score >= min_score:
                    matched_count += 1
                    total_matches += len(matching_experiences) if matching_experiences else 0
            
            batch_time = time.time() - batch_start
            elapsed = time.time() - start_time
            
            print(f"   Batch {i//batch_size + 1}: {len(batch)} licitaciones procesadas en {batch_time:.2f}s | "
                  f"Total: {matched_count} matches | Tiempo acumulado: {elapsed:.2f}s")
            
            # Early exit test (like API)
            if matched_count >= limit:  # Stop when we have enough for one page
                print(f"   ⚡ Early exit activado: {matched_count} matches encontrados (target: {limit})")
                break
            
            # Safety: stop if taking too long
            if elapsed > 90:  # Stop before 120s timeout
                print(f"   ⚠️  Deteniendo por seguridad (cerca del timeout de 120s)")
                break
        
        total_time = time.time() - start_time
        
        print()
        print("=" * 80)
        print("📊 RESULTADOS:")
        print("=" * 80)
        print(f"   Licitaciones procesadas: {min(i + batch_size, len(interventoria_tenders))}")
        print(f"   Matches encontrados: {matched_count}")
        print(f"   Tiempo total: {total_time:.2f} segundos")
        print(f"   Tiempo promedio por licitación: {total_time / min(i + batch_size, len(interventoria_tenders)):.3f}s")
        print()
        
        if total_time > 120:
            print("❌ PROBLEMA: Tiempo excede 120 segundos (timeout)")
            print(f"   Recomendación: Reducir MAX_TENDERS_FOR_MATCHING a {int(len(interventoria_tenders) * 0.5)}")
        elif total_time > 90:
            print("⚠️  ADVERTENCIA: Tiempo cerca del límite (90-120s)")
            print(f"   Recomendación: Reducir MAX_TENDERS_FOR_MATCHING a {int(len(interventoria_tenders) * 0.6)}")
        else:
            print("✅ ÉXITO: Tiempo dentro del límite (< 90s)")
            print(f"   El sistema debería funcionar correctamente")
        
        print()
        print("=" * 80)
        print("💡 RECOMENDACIONES:")
        print("=" * 80)
        
        if total_time > 0:
            time_per_tender = total_time / min(i + batch_size, len(interventoria_tenders))
            max_tenders_safe = int(90 / time_per_tender)  # Safe limit for 90s
            
            print(f"   1. Tiempo por licitación: {time_per_tender:.3f}s")
            print(f"   2. Límite seguro (90s): {max_tenders_safe} licitaciones")
            print(f"   3. Límite actual: 200 licitaciones")
            
            if max_tenders_safe < 200:
                print(f"   ⚠️  Reducir MAX_TENDERS_FOR_MATCHING a {max_tenders_safe}")
            else:
                print(f"   ✅ El límite actual (200) es seguro")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_matching_performance()

