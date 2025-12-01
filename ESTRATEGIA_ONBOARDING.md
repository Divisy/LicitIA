# Estrategia de Onboarding - LicitIA
## Enfoque Product Manager + UX/UI

---

## 🎯 Objetivos del Onboarding

### Objetivos Principales
1. **Time-to-Value Rápido**: El usuario debe ver valor en los primeros 5 minutos
2. **Reducir Fricción**: Minimizar pasos antes de ver resultados
3. **Educar sin Abrumar**: Mostrar funcionalidades clave sin saturar
4. **Generar Confianza**: Demostrar que el sistema encuentra oportunidades relevantes
5. **Retención Temprana**: Crear hábito de uso desde el primer día

### Métricas de Éxito
- **Tasa de completación**: >80% de usuarios completan onboarding
- **Time-to-first-match**: <3 minutos para ver primera licitación relevante
- **Día 1 engagement**: >60% de usuarios vuelven al día siguiente
- **Día 7 retention**: >40% de usuarios activos después de 1 semana

---

## 👥 Perfiles de Usuario

### Persona 1: Gerente de Oportunidades (Primera vez)
- **Contexto**: Nuevo en la plataforma, necesita entender rápidamente
- **Objetivo**: Encontrar licitaciones relevantes para su empresa
- **Dolor**: No sabe cómo funciona el matching, no tiene experiencias cargadas
- **Necesidad**: Guía paso a paso, ver resultados inmediatos

### Persona 2: Usuario Avanzado (Retornando)
- **Contexto**: Ya conoce el sistema, quiere eficiencia
- **Objetivo**: Acceso rápido a nuevas oportunidades
- **Dolor**: No quiere perder tiempo en pasos innecesarios
- **Necesidad**: Skip onboarding, acceso directo al dashboard

---

## 🚀 Estrategia: Onboarding Progresivo (Progressive Disclosure)

### Fase 1: Welcome Screen (Primera Impresión)
**Duración**: 30 segundos

**Elementos**:
- Logo + tagline claro: "Encuentra las licitaciones perfectas para tu empresa"
- Valor propuesto en 1 línea: "IA que identifica oportunidades de interventoría vial basadas en tu experiencia"
- CTA principal: "Comenzar" (grande, destacado)
- CTA secundario: "Ver demo" (opcional, para curiosos)

**UX Principles**:
- ✅ Una sola acción clara
- ✅ Sin distracciones
- ✅ Visual limpio y profesional

---

### Fase 2: Quick Setup (Configuración Mínima)
**Duración**: 2-3 minutos

**Flujo Optimizado**:

#### Paso 1: Nombre de la Empresa (30 seg)
- Input simple: "¿Cuál es el nombre de tu empresa?"
- Placeholder: "Ej: Constructora ABC"
- Validación: Solo verificar que no esté vacío
- **No pedir más datos** (email, teléfono, etc. se piden después)

#### Paso 2: Cargar Experiencias (2 min)
**Opciones**:
- **Opción A - Rápida**: "Cargar Excel" (recomendado)
  - Botón grande: "Subir archivo Excel"
  - Texto: "Formato: Descripción, Entidad, Monto, Fecha"
  - Link: "Descargar plantilla" (opcional)
  - Preview de las primeras 3 experiencias cargadas

- **Opción B - Manual**: "Agregar manualmente" (para usuarios sin Excel)
  - Formulario simple: 1 experiencia de ejemplo
  - Botón: "Agregar otra" (opcional, no obligatorio)
  - Texto: "Puedes agregar más después"

**UX Principles**:
- ✅ Progreso visible (1/3, 2/3, 3/3)
- ✅ Permitir "Saltar este paso" (opcional)
- ✅ Mostrar ejemplo visual de cómo se verá
- ✅ Feedback inmediato: "✓ 5 experiencias cargadas"

#### Paso 3: Ver Primeros Resultados (30 seg)
- **No esperar**: Mostrar resultados inmediatamente
- Usar datos de ejemplo si no hay experiencias
- Mensaje: "Basado en tu perfil, encontramos X licitaciones relevantes"
- CTA: "Ver licitaciones" → Lleva al dashboard

---

### Fase 3: Dashboard con Tooltips Contextuales
**Duración**: On-demand (el usuario decide cuándo)

**Elementos de Onboarding en Dashboard**:

#### Tooltip 1: Filtros (aparece automáticamente)
- **Trigger**: Al entrar al dashboard por primera vez
- **Contenido**: 
  - "Usa los filtros para encontrar licitaciones específicas"
  - "💡 Tip: Activa 'Solo coincidencias con experiencia' para ver solo las más relevantes"
- **Posición**: Sobre el panel de filtros
- **Acción**: "Entendido" (cierra) o "Mostrar más tips" (continúa)

#### Tooltip 2: Columna Match Score (on hover)
- **Trigger**: Al pasar mouse sobre columna "Match Experiencia"
- **Contenido**: 
  - "Este porcentaje indica qué tan bien coincide la licitación con tu experiencia"
  - ">60% = Alta coincidencia (recomendado)"
  - "40-60% = Coincidencia media"
- **Visual**: Badge de color (verde/amarillo/rojo) con explicación

#### Tooltip 3: Fecha Presentación Ofertas (on hover)
- **Trigger**: Al pasar mouse sobre columna "Fecha Presentación Ofertas"
- **Contenido**: 
  - "Fecha límite para presentar tu oferta"
  - "Las licitaciones se ordenan por fecha más lejana primero"
- **Visual**: Icono de calendario + texto

#### Tooltip 4: Acción Rápida (flotante, primera vez)
- **Trigger**: Después de 30 segundos en dashboard
- **Contenido**: 
  - "💡 ¿Sabías que puedes exportar las licitaciones a Excel?"
  - Botón: "Exportar ahora" o "Cerrar"
- **Posición**: Esquina inferior derecha (no intrusivo)

---

## 🎨 Componentes UI/UX Específicos

### 1. Progress Indicator
```
[████████░░] 80% completado
```
- Siempre visible durante onboarding
- Muestra pasos restantes
- Permite volver atrás

### 2. Empty States Educativos
**Cuando no hay experiencias**:
- Ilustración simple (icono de carpeta)
- Texto: "Carga tus experiencias para ver licitaciones personalizadas"
- CTA: "Cargar experiencias"
- Link: "Ver todas las licitaciones" (sin filtro)

**Cuando no hay matches**:
- Ilustración: Icono de búsqueda
- Texto: "No encontramos coincidencias con tu experiencia actual"
- Sugerencias:
  - "Intenta agregar más experiencias"
  - "Ajusta los filtros de búsqueda"
  - "Explora todas las licitaciones disponibles"

### 3. Success States
**Después de cargar experiencias**:
- Toast notification: "✓ 5 experiencias cargadas exitosamente"
- Animación sutil: Checkmark verde
- Auto-dismiss después de 3 segundos

**Después de primer match encontrado**:
- Highlight de la primera licitación con match alto
- Tooltip: "¡Esta licitación tiene 85% de coincidencia con tu experiencia!"

### 4. Skip Options
- **Siempre disponible**: "Saltar este paso" en cada fase
- **No forzar**: Permitir usar el sistema sin completar todo
- **Recordatorio suave**: "Puedes completar tu perfil después"

---

## 📱 Flujo Visual Completo

### Pantalla 1: Welcome
```
┌─────────────────────────────────────┐
│         [Logo LicitIA]              │
│                                     │
│  Encuentra las licitaciones         │
│  perfectas para tu empresa          │
│                                     │
│  IA que identifica oportunidades    │
│  de interventoría vial basadas      │
│  en tu experiencia                  │
│                                     │
│     [Comenzar]  [Ver Demo]         │
└─────────────────────────────────────┘
```

### Pantalla 2: Nombre Empresa
```
┌─────────────────────────────────────┐
│  [◄] Configura tu perfil    [1/3]   │
│                                     │
│  ¿Cuál es el nombre de tu empresa?  │
│                                     │
│  [___________________________]      │
│  Ej: Constructora ABC               │
│                                     │
│           [Continuar →]             │
└─────────────────────────────────────┘
```

### Pantalla 3: Cargar Experiencias
```
┌─────────────────────────────────────┐
│  [◄] Configura tu perfil    [2/3]   │
│                                     │
│  Carga tus experiencias anteriores  │
│  (Esto ayuda a encontrar mejores    │
│   coincidencias)                    │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  📄 Subir archivo Excel     │   │
│  │     Arrastra o haz click    │   │
│  └─────────────────────────────┘   │
│                                     │
│  O [Agregar manualmente]            │
│                                     │
│  [Saltar este paso]  [Continuar →] │
└─────────────────────────────────────┘
```

### Pantalla 4: Dashboard (Primera vez)
```
┌─────────────────────────────────────┐
│  [Tooltip flotante]                 │
│  💡 Usa los filtros para encontrar  │
│     licitaciones específicas        │
│  [Entendido]                        │
│                                     │
│  [Filtros...]                       │
│                                     │
│  Mostrando 50 de 52422 licitaciones │
│                                     │
│  [Tabla con datos...]                │
└─────────────────────────────────────┘
```

---

## 🎯 Estrategias Avanzadas

### 1. Onboarding Adaptativo
- **Detección de perfil**: Si el usuario carga muchas experiencias → Usuario avanzado
- **Ajustar contenido**: Menos explicaciones, más funcionalidades avanzadas
- **Skip inteligente**: Si detecta que sabe usar el sistema, ofrecer skip

### 2. Gamificación Sutil
- **Badges**: "Primera experiencia cargada", "Primer match encontrado"
- **Progreso visual**: Barra de completitud del perfil
- **Logros**: "Has visto 10 licitaciones", "Has exportado tu primer reporte"

### 3. Onboarding Contextual
- **Help contextual**: Botón "?" en cada sección
- **Video tours**: Opcionales, no obligatorios
- **FAQ inteligente**: Basado en acciones del usuario

### 4. Re-onboarding para Usuarios Inactivos
- **Email**: "Te extrañamos, aquí hay 5 nuevas licitaciones para ti"
- **In-app**: "¿Necesitas ayuda? Revisa las nuevas funcionalidades"
- **Tutoriales cortos**: Para nuevas features

---

## 🔧 Implementación Técnica

### Componentes Necesarios

1. **OnboardingWizard Component**
   - Maneja el flujo paso a paso
   - Persiste progreso en localStorage
   - Permite skip y resume

2. **Tooltip System**
   - Tooltips contextuales
   - Posicionamiento inteligente
   - Dismissible y no intrusivo

3. **Progress Tracker**
   - Barra de progreso
   - Indicadores de pasos
   - Navegación hacia atrás

4. **Empty States**
   - Componentes reutilizables
   - Mensajes contextuales
   - CTAs claros

5. **Analytics Integration**
   - Track eventos de onboarding
   - Medir completitud
   - Identificar puntos de fricción

---

## 📊 Métricas y Optimización

### KPIs a Medir
1. **Onboarding Completion Rate**
2. **Time to First Match**
3. **Experiences Uploaded (Día 1)**
4. **Dashboard Engagement (Primera sesión)**
5. **Feature Discovery Rate**

### A/B Testing Opportunities
- **Welcome screen**: Variaciones de copy
- **Upload flow**: Excel vs Manual vs Skip
- **Tooltip timing**: Inmediato vs Delay
- **Empty states**: Diferentes mensajes

---

## ✅ Checklist de Implementación

### Fase 1: MVP (Semana 1-2)
- [ ] Welcome screen básico
- [ ] Flujo de nombre de empresa
- [ ] Carga de experiencias (Excel)
- [ ] Dashboard con tooltip inicial
- [ ] Progress indicator

### Fase 2: Mejoras (Semana 3-4)
- [ ] Tooltips contextuales
- [ ] Empty states educativos
- [ ] Success animations
- [ ] Skip options
- [ ] Analytics integration

### Fase 3: Optimización (Semana 5+)
- [ ] Onboarding adaptativo
- [ ] Gamificación sutil
- [ ] A/B testing setup
- [ ] Re-onboarding para inactivos

---

## 🎓 Principios de Diseño Aplicados

1. **Progressive Disclosure**: Mostrar solo lo necesario en cada paso
2. **Time-to-Value**: Valor inmediato, no después de completar todo
3. **Opt-in, not Opt-out**: Permitir skip, no forzar
4. **Contextual Help**: Ayuda cuando se necesita, no antes
5. **Feedback Inmediato**: Confirmar acciones del usuario
6. **Error Prevention**: Validación proactiva, no reactiva
7. **Consistency**: Mismo lenguaje y patrones en todo el flujo

---

## 💡 Recomendaciones Finales

### DO's ✅
- Mantener el onboarding corto (<5 minutos)
- Mostrar valor inmediato (resultados antes de completar)
- Permitir exploración libre (no bloquear funcionalidades)
- Usar lenguaje simple y claro
- Proporcionar ejemplos visuales

### DON'Ts ❌
- No pedir demasiada información al inicio
- No forzar completar todos los pasos
- No usar jerga técnica
- No mostrar demasiadas opciones a la vez
- No asumir conocimiento previo

---

**Próximos Pasos**: 
1. Crear mockups de alta fidelidad
2. Prototipo interactivo en Figma
3. User testing con 5-10 usuarios
4. Iterar basado en feedback
5. Implementar versión MVP

