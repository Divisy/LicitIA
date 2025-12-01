# Organización de Secciones: Perfil vs Experiencias

## 📋 ESTRUCTURA PROPUESTA

### **PERFIL (`/profile`)**
**Propósito:** Información y configuración de la cuenta de la empresa

**Contenido:**
1. **Información de la Empresa**
   - Nombre de la empresa
   - NIT/RUT (opcional)
   - Sector/Industria
   - Ubicación (ciudad, departamento)
   - Descripción breve

2. **Configuración de la Cuenta**
   - Email de contacto
   - Teléfono
   - Usuario administrador
   - Cambiar contraseña (si aplica)

3. **Preferencias de Notificaciones**
   - Frecuencia de alertas (inmediata, diaria, semanal)
   - Canales (email, push, SMS)
   - Tipos de notificaciones (nuevas licitaciones, matches altos, recordatorios)

4. **Configuración de Matching**
   - Umbral mínimo de match score (default: 55%)
   - Categorías preferidas
   - Rangos de monto preferidos
   - Departamentos/regiones de interés

5. **Estadísticas Generales** (resumen)
   - Total de experiencias cargadas
   - Total de matches encontrados
   - Última actualización

---

### **EXPERIENCIAS (`/experiences`)**
**Propósito:** Gestión completa de experiencias de la empresa

**Contenido:**
1. **Header con Estadísticas**
   - Número de experiencias cargadas
   - Número de licitaciones encontradas gracias a estas experiencias
   - Badge de éxito si tiene 5+ experiencias
   - CTA "Ver Matches" si hay matches disponibles

2. **Cargar Experiencias** (Sección Principal)
   - Tabs: Excel | Manual
   - Value proposition: "5+ experiencias = 3x más matches"
   - FileUploader para Excel
   - Formulario manual
   - Botón descargar plantilla
   - Feedback inmediato

3. **Lista de Experiencias Guardadas**
   - Tabla con todas las experiencias
   - Acciones: Editar | Eliminar | Ver matches relacionados
   - Filtros y búsqueda
   - Paginación

4. **Ayuda y Guías**
   - Accordion con:
     - Formato del Excel
     - ¿Por qué cargar experiencias?
     - Preguntas frecuentes

---

## 🎯 DÓNDE CARGAR EXPERIENCIAS

### **Ubicación Principal: `/experiences`**
- Es el lugar lógico y esperado
- Todo lo relacionado con experiencias en un solo lugar
- Mejor organización de información

### **Ubicación Secundaria: Onboarding**
- Paso 3 del onboarding (opcional, puede saltar)
- Para nuevos usuarios que quieren empezar rápido

### **Ubicación Terciaria: Banner en Dashboard**
- Si no tiene experiencias, mostrar banner destacado
- "Carga experiencias para ver matches personalizados"
- Click → Va a `/experiences`

---

## ✅ VENTAJAS DE ESTA ORGANIZACIÓN

1. **Separación de Responsabilidades**
   - Perfil = Configuración y datos de la empresa
   - Experiencias = Gestión de proyectos/contratos

2. **Mejor UX**
   - Usuario sabe dónde buscar cada cosa
   - Navegación más intuitiva
   - Menos confusión

3. **Escalabilidad**
   - Fácil agregar más features a cada sección
   - Perfil puede crecer con más configuraciones
   - Experiencias puede crecer con análisis, exportación, etc.

4. **Consistencia**
   - Sigue patrones comunes de SaaS
   - Similar a otros productos B2B

---

## 🔄 MIGRACIÓN NECESARIA

**Actual:**
- `/profile` tiene TODO (info empresa + cargar + listar experiencias)

**Nuevo:**
- `/profile` → Solo info empresa y configuración
- `/experiences` → Todo lo relacionado con experiencias (NUEVO)

**Cambios:**
1. Crear página `Experiences.tsx`
2. Mover componentes de carga y lista a `/experiences`
3. Simplificar `Profile.tsx` para solo info y configuración
4. Actualizar rutas en `App.tsx`
5. Actualizar navegación (ya existe en menú)

