# Requisitos para Enfoque Asíncrono (Background Processing)

## 🎯 ¿Qué es el Enfoque Asíncrono?

Procesar el matching de licitaciones en **background** (no bloquea la request HTTP). El usuario hace la request y recibe inmediatamente un "job ID", luego consulta el estado y ve resultados progresivamente.

---

## 📦 Infraestructura Necesaria

### **1. Sistema de Colas (Message Broker)**

**Opciones:**

#### **Opción A: Redis (Recomendada)** ⭐⭐⭐
- ✅ **Ligera** y rápida
- ✅ **Fácil de instalar** (solo Docker)
- ✅ **Ya usada** en muchos proyectos
- ✅ **Soporta** tanto colas como caché

**Instalación:**
```bash
# En docker-compose.yml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
```

#### **Opción B: RabbitMQ**
- ✅ Más robusta
- ⚠️ Más pesada
- ⚠️ Más compleja de configurar

#### **Opción C: PostgreSQL (Usando tu DB actual)**
- ✅ No requiere servicio adicional
- ⚠️ Menos eficiente para colas
- ⚠️ Puede saturar la DB

**Recomendación:** Redis ⭐

---

### **2. Worker Framework**

**Opciones:**

#### **Opción A: Celery** ⭐⭐⭐ (Más Popular)
- ✅ **Muy popular** en Python
- ✅ **Bien documentado**
- ✅ **Soporta** Redis, RabbitMQ, PostgreSQL
- ✅ **Features avanzadas** (retry, scheduling, etc.)

**Instalación:**
```bash
pip install celery[redis]
```

**Complejidad:** Media-Alta

#### **Opción B: RQ (Redis Queue)** ⭐⭐ (Más Simple)
- ✅ **Más simple** que Celery
- ✅ **Solo para Redis**
- ✅ **Fácil de usar**
- ⚠️ Menos features que Celery

**Instalación:**
```bash
pip install rq
```

**Complejidad:** Media

#### **Opción C: Thread Pool (Python nativo)**
- ✅ **No requiere** dependencias externas
- ✅ **Simple** de implementar
- ⚠️ **Limitado** a un solo proceso
- ⚠️ **No persiste** si el servidor se reinicia

**Complejidad:** Baja

**Recomendación:** RQ (si quieres simple) o Celery (si quieres robusto) ⭐

---

### **3. Base de Datos para Resultados**

**Opciones:**

#### **Opción A: Redis (Recomendada)** ⭐⭐⭐
- ✅ **Rápida** para consultas
- ✅ **Ya la tienes** para colas
- ✅ **TTL automático** (expira resultados viejos)

#### **Opción B: PostgreSQL (Tu DB actual)**
- ✅ **No requiere** servicio adicional
- ✅ **Persistente**
- ⚠️ Más lenta para consultas frecuentes

**Recomendación:** Redis ⭐

---

## 🏗️ Arquitectura Necesaria

### **Componentes:**

```
┌─────────────┐
│   Frontend  │
│  (React)    │
└──────┬──────┘
       │
       │ 1. POST /api/v1/tenders/match (async)
       │    → Retorna: { job_id: "abc123" }
       │
       ▼
┌─────────────┐
│   Backend   │
│  (FastAPI)  │
└──────┬──────┘
       │
       │ 2. Encola job en Redis
       │
       ▼
┌─────────────┐
│    Redis    │
│  (Cola +    │
│   Resultados)│
└──────┬──────┘
       │
       │ 3. Worker procesa job
       │
       ▼
┌─────────────┐
│   Worker    │
│ (Celery/RQ) │
│             │
│ - Matching  │
│ - Guarda    │
│   resultados│
└─────────────┘
```

---

## 📋 Cambios Necesarios en el Código

### **1. Backend (FastAPI)**

#### **Nuevas Dependencias:**
```python
# requirements.txt
celery[redis]==5.3.4  # o rq==1.15.1
redis==5.0.1
```

#### **Nuevo Endpoint:**
```python
# app/api/v1/tenders.py

@router.post("/tenders/match/async")
async def start_async_matching(
    filters: TenderFilters,
    background_tasks: BackgroundTasks
):
    """Inicia matching asíncrono, retorna job_id"""
    job_id = str(uuid.uuid4())
    
    # Encolar job
    task = process_matching_async.delay(job_id, filters)
    
    return {
        "job_id": job_id,
        "status": "processing",
        "status_url": f"/api/v1/tenders/match/status/{job_id}"
    }

@router.get("/tenders/match/status/{job_id}")
async def get_matching_status(job_id: str):
    """Consulta estado del matching"""
    # Consultar Redis para estado y resultados
    status = redis_client.get(f"match_status:{job_id}")
    results = redis_client.get(f"match_results:{job_id}")
    
    return {
        "job_id": job_id,
        "status": status,  # "processing", "completed", "failed"
        "progress": {...},  # Licitaciones procesadas, matches encontrados
        "results": results if status == "completed" else None
    }
```

---

### **2. Worker (Celery o RQ)**

#### **Con Celery:**
```python
# app/workers/celery_app.py
from celery import Celery

celery_app = Celery(
    'licitia',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0'
)

@celery_app.task
def process_matching_async(job_id: str, filters: dict):
    """Procesa matching en background"""
    # Tu lógica de matching aquí
    # Guarda resultados en Redis
    redis_client.set(f"match_results:{job_id}", results)
    redis_client.set(f"match_status:{job_id}", "completed")
```

#### **Con RQ:**
```python
# app/workers/rq_worker.py
from rq import Queue
from redis import Redis

redis_conn = Redis(host='redis', port=6379)
q = Queue('matching', connection=redis_conn)

def process_matching_async(job_id: str, filters: dict):
    """Procesa matching en background"""
    # Tu lógica de matching aquí
    # Guarda resultados en Redis
    redis_client.set(f"match_results:{job_id}", results)
    redis_client.set(f"match_status:{job_id}", "completed")
```

---

### **3. Docker Compose**

#### **Agregar Redis:**
```yaml
# docker/docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    container_name: licitia_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  worker:
    build:
      context: ../backend
      dockerfile: Dockerfile
    container_name: licitia_worker
    depends_on:
      - redis
      - postgres
    env_file:
      - ../.env
    command: celery -A app.workers.celery_app worker --loglevel=info
    # o para RQ: rq worker matching --url redis://redis:6379
```

---

### **4. Frontend (React)**

#### **Nuevo Flujo:**
```typescript
// 1. Iniciar matching asíncrono
const response = await fetch('/api/v1/tenders/match/async', {
  method: 'POST',
  body: JSON.stringify(filters)
});
const { job_id } = await response.json();

// 2. Polling para estado
const checkStatus = async () => {
  const status = await fetch(`/api/v1/tenders/match/status/${job_id}`);
  const data = await status.json();
  
  if (data.status === 'completed') {
    setTenders(data.results);
  } else if (data.status === 'processing') {
    setProgress(data.progress); // Mostrar progreso
    setTimeout(checkStatus, 2000); // Revisar cada 2 segundos
  }
};

checkStatus();
```

---

## 💰 Costos y Recursos

### **Recursos Adicionales:**
- **Redis:** ~50-100 MB RAM
- **Worker:** ~200-500 MB RAM (depende de carga)
- **Total adicional:** ~250-600 MB RAM

### **Costo:**
- **Desarrollo:** 1-2 días
- **Mantenimiento:** Medio (monitorear workers, Redis)
- **Infraestructura:** Mínimo (solo Redis si no lo tienes)

---

## ⚙️ Configuración Completa

### **1. Instalar Dependencias:**
```bash
# Backend
pip install celery[redis] redis
# o
pip install rq redis
```

### **2. Agregar Redis a Docker:**
```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
```

### **3. Configurar Variables de Entorno:**
```env
# .env
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

### **4. Crear Worker:**
```python
# app/workers/__init__.py
# app/workers/celery_app.py
# app/workers/tasks.py
```

### **5. Iniciar Worker:**
```bash
# En Docker
celery -A app.workers.celery_app worker --loglevel=info

# O con RQ
rq worker matching --url redis://redis:6379
```

---

## 📊 Comparación: Celery vs RQ

| Aspecto | Celery | RQ |
|---------|--------|-----|
| **Complejidad** | Media-Alta | Media |
| **Features** | Muchas | Básicas |
| **Documentación** | Excelente | Buena |
| **Comunidad** | Muy grande | Mediana |
| **Recomendación** | Si necesitas features avanzadas | Si quieres simplicidad |

---

## 🎯 Recomendación Final

### **Para tu caso (LicitIA):**

**Usar RQ (Redis Queue)** porque:
- ✅ **Más simple** que Celery
- ✅ **Suficiente** para tu caso de uso
- ✅ **Fácil de mantener**
- ✅ **Menos configuración**

**O usar Celery** si:
- Necesitas features avanzadas (retry, scheduling, etc.)
- Planeas escalar a múltiples workers
- Necesitas monitoreo avanzado

---

## 📝 Checklist de Implementación

- [ ] Instalar Redis (Docker)
- [ ] Instalar Celery o RQ
- [ ] Configurar variables de entorno
- [ ] Crear worker tasks
- [ ] Agregar endpoints async en FastAPI
- [ ] Actualizar frontend para polling
- [ ] Probar con 400 licitaciones
- [ ] Monitorear performance

---

## ⏱️ Tiempo Estimado

- **Setup básico:** 4-6 horas
- **Implementación completa:** 1-2 días
- **Testing y ajustes:** 4-8 horas
- **Total:** 2-3 días

---

**¿Quieres que implemente el enfoque asíncrono con RQ (más simple) o Celery (más robusto)?**



