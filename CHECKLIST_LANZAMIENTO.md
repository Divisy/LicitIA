# Checklist de Lanzamiento - LicitIA

## ✅ Completado

### 1. Landing Page
- [x] Componente React creado (`frontend/src/pages/Landing.tsx`)
- [x] Estilos CSS creados (`frontend/src/pages/Landing.css`)
- [x] Ruta agregada a App.tsx (`/landing`)
- [x] Formulario de email capture funcional
- [x] Opción de "saltar" y ir directo al dashboard
- [x] Secciones: Hero, Benefits, How It Works, Pricing, CTA Final

### 2. Email Capture (Backend)
- [x] Modelo `Lead` creado (`backend/app/models/lead.py`)
- [x] Endpoint POST `/api/v1/leads` creado
- [x] Endpoint GET `/api/v1/leads` creado (admin)
- [x] Router agregado a `main.py`
- [x] Migración de base de datos creada (`aa8d575bebe5_add_leads_table.py`)

### 3. Email Capture (Frontend)
- [x] Función `captureLead` agregada a `api/client.ts`
- [x] Integración con formulario de landing page
- [x] Manejo de errores y éxito
- [x] Redirección automática al dashboard después de registro

### 4. Mensajes de Lanzamiento
- [x] Documento completo creado (`MENSAJES_LANZAMIENTO.md`)
- [x] Versiones para LinkedIn (3 variaciones)
- [x] Versiones para Email (lanzamiento, seguimiento, conversión)
- [x] Mensajes para WhatsApp/Telegram
- [x] Mensajes para grupos

## 🔄 Pendiente

### 1. Migración de Base de Datos
- [ ] Ejecutar migración: `cd backend && alembic upgrade head`
- [ ] Verificar que la tabla `leads` se creó correctamente

### 2. Verificación del Demo
- [ ] Verificar que el dashboard carga correctamente
- [ ] Verificar que el onboarding banner funciona
- [ ] Verificar que la landing page se muestra correctamente
- [ ] Probar el formulario de email capture
- [ ] Verificar que los leads se guardan en la base de datos

### 3. Configuración de URL
- [ ] Definir URL de producción (o usar localhost:3000 para pruebas)
- [ ] Actualizar `MENSAJES_LANZAMIENTO.md` con URL real
- [ ] Configurar dominio (opcional, para producción)

### 4. Personalización
- [ ] Reemplazar `[TU_URL]` en mensajes con URL real
- [ ] Reemplazar `[Tu nombre]` con nombre real
- [ ] Personalizar mensajes según audiencia

### 5. Testing
- [ ] Probar flujo completo: Landing → Registro → Dashboard
- [ ] Probar flujo alternativo: Landing → Skip → Dashboard
- [ ] Verificar que los emails se capturan correctamente
- [ ] Verificar que no hay errores en consola

## 🚀 Próximos Pasos

### Semana 1: Preparación
1. **Ejecutar migración de base de datos**
   ```bash
   cd backend
   alembic upgrade head
   ```

2. **Verificar que todo funciona**
   - Iniciar backend: `cd backend && python -m uvicorn app.main:app --reload`
   - Iniciar frontend: `cd frontend && npm run dev`
   - Visitar: `http://localhost:3000/landing`
   - Probar registro de email
   - Verificar dashboard

3. **Personalizar mensajes**
   - Reemplazar placeholders en `MENSAJES_LANZAMIENTO.md`
   - Preparar lista de contactos para email directo
   - Preparar posts para LinkedIn

### Semana 2: Lanzamiento
1. **Lanzamiento Soft**
   - Post en LinkedIn personal
   - Email a 10-20 contactos directos
   - Compartir en grupos relevantes

2. **Monitoreo**
   - Revisar sign-ups diarios
   - Responder a feedback
   - Ajustar según comportamiento

3. **Seguimiento**
   - Email Día 2 (si no ha usado)
   - Email Día 5 (si ha usado)
   - Email Día 7 (conversión)

## 📊 Métricas a Medir

### KPIs Diarios
- Sign-ups nuevos
- Usuarios activos (DAU)
- Conversiones a pago (después de semana 5)

### KPIs Semanales
- Tasa de retención D7
- Feature usage
- Feedback recibido

### KPIs Mensuales
- MRR (Monthly Recurring Revenue)
- CAC (Customer Acquisition Cost)
- LTV (Lifetime Value)
- Churn rate

## 🔗 URLs Importantes

- **Landing Page**: `http://localhost:3000/landing` (o tu dominio)
- **Dashboard**: `http://localhost:3000/` (o tu dominio)
- **API Backend**: `http://localhost:8000/api/v1`
- **API Docs**: `http://localhost:8000/docs`

## 📝 Notas

- La landing page está lista y funcional
- El email capture está integrado con el backend
- Los mensajes están preparados pero necesitan personalización
- La migración de base de datos necesita ejecutarse antes del lanzamiento

## 🎯 Objetivos del Experimento

- **Sign-ups**: >50 en primer mes
- **Activos D7**: >30% de usuarios vuelven después de 7 días
- **Conversión a pago**: >5% de sign-ups se convierten
- **Retención M1**: >60% de pagadores siguen después de 1 mes
- **NPS**: >40

---

**Última actualización**: [Fecha actual]
**Estado**: Listo para ejecutar migración y testing

