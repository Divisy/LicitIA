#!/usr/bin/env python3
"""Script para verificar el retraso en la actualización del dataset SECOP II."""
from app.core.db import SessionLocal
from app.models.tender import Tender
from app.config import settings
from sqlalchemy import func
from datetime import datetime

def check_secop_delay():
    """Verifica el retraso en la actualización del dataset SECOP."""
    print("=" * 70)
    print("🔍 VERIFICACIÓN DE ACTUALIZACIÓN DEL DATASET SECOP II")
    print("=" * 70)

    db = SessionLocal()
    try:
        # Get the most recent publication date from our database
        max_date = db.query(func.max(Tender.publication_date)).scalar()
        today = datetime.now()

        if max_date:
            # Calculate days behind
            if isinstance(max_date, datetime):
                latest_date = max_date
            else:
                latest_date = datetime.combine(max_date, datetime.min.time())

            days_behind = (today - latest_date).days

            print(f"\n📅 FECHA MÁS RECIENTE EN NUESTRA BASE DE DATOS:")
            print(f"   {latest_date.strftime('%Y-%m-%d')}")
            print(f"\n📅 FECHA ACTUAL:")
            print(f"   {today.strftime('%Y-%m-%d')}")
            print(f"\n" + "=" * 70)

            if days_behind > 0:
                print(f"\n⚠️  RETRASO DETECTADO: {days_behind} días")
                print(f"\n❌ La API de SECOP está {days_behind} días desactualizada")
                print(f"   Los datos más recientes disponibles son del {latest_date.strftime('%Y-%m-%d')}")
                print(f"   Fecha actual: {today.strftime('%Y-%m-%d')}")

                if days_behind >= 3:
                    print(f"\n🔴 ALERTA: Retraso significativo ({days_behind} días)")
                    print(f"   Esto afecta la disponibilidad de licitaciones recientes")
                    print(f"   Las licitaciones publicadas en los últimos {days_behind} días")
                    print(f"   NO están disponibles en la API aún")
            else:
                print(f"\n✅ La API está actualizada")

            # Get count of tenders from the latest date
            count_latest = db.query(Tender).filter(
                func.date(Tender.publication_date) == latest_date.date()
            ).count()

            total = db.query(Tender).count()

            print(f"\n" + "=" * 70)
            print(f"📊 RESUMEN:")
            print(f"   • Dataset ID: {settings.SECOP_DATASET_ID}")
            print(f"   • Última fecha disponible: {latest_date.strftime('%Y-%m-%d')}")
            print(f"   • Días de retraso: {days_behind}")
            print(f"   • Estado: {'🔴 DESACTUALIZADO' if days_behind > 0 else '✅ ACTUALIZADO'}")
            print(f"   • Licitaciones del {latest_date.strftime('%Y-%m-%d')}: {count_latest:,}")
            print(f"   • Total licitaciones en BD: {total:,}")
            print("=" * 70)
        else:
            print("\n❌ No se encontraron datos en la base de datos")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_secop_delay()

