# LicitIA Frontend - IBM Carbon Design System

## 🎨 Arquitectura UI

Este proyecto utiliza **IBM Carbon Design System** como base de diseño, proporcionando una experiencia consistente y accesible.

---

## 📦 Estructura del Proyecto

```
frontend/
├── src/
│   ├── components/
│   │   └── ui/              # Componentes base del UI Kit
│   │       ├── Button/
│   │       ├── Card/
│   │       └── Input/
│   ├── config/
│   │   └── i18n.ts         # Configuración de internacionalización
│   ├── layouts/
│   │   └── AppLayout/      # Layout principal con Carbon
│   ├── locales/
│   │   └── es-CO.json      # Traducciones en español colombiano
│   ├── styles/
│   │   ├── _carbon.scss    # Estilos base de Carbon
│   │   ├── _tokens.scss    # Tokens de diseño personalizados
│   │   └── index.scss      # Punto de entrada de estilos
│   ├── theme/
│   │   └── ThemeProvider.tsx  # Provider de temas (light/dark)
│   └── test/
│       └── setup.ts        # Configuración de pruebas
```

---

## 🎯 UI Kit - Componentes Base

### Button
```tsx
import { Button } from '@/components/ui'

<Button variant="primary" size="md" onClick={handleClick}>
  Click me
</Button>
```

**Variantes:** `primary` | `secondary` | `tertiary` | `danger` | `ghost`  
**Tamaños:** `sm` | `md` | `lg`

### Card
```tsx
import { Card } from '@/components/ui'

<Card padding="md" interactive onClick={handleClick}>
  Card content
</Card>
```

**Padding:** `none` | `sm` | `md` | `lg`  
**Interactive:** Hover effects cuando es clickeable

### Input
```tsx
import { Input } from '@/components/ui'

<Input
  label="Email"
  placeholder="tu@email.com"
  error={hasError}
  errorText="Email inválido"
  helperText="Ingresa tu email"
/>
```

---

## 🌍 Internacionalización (i18n)

### Configuración
- **Idioma:** Español Colombiano (`es-CO`)
- **Librería:** `react-i18next`
- **Archivo de traducciones:** `src/locales/es-CO.json`

### Uso
```tsx
import { useTranslation } from 'react-i18next'

function MyComponent() {
  const { t } = useTranslation()
  
  return <h1>{t('dashboard.title')}</h1>
}
```

### Agregar nuevas traducciones
1. Edita `src/locales/es-CO.json`
2. Usa la estructura anidada: `"section.key": "Traducción"`
3. Accede con `t('section.key')`

---

## 🎨 Sistema de Temas

### Temas Disponibles
- **Light** (default): Tema claro
- **Dark**: Tema oscuro (Carbon g100)

### Uso
```tsx
import { useTheme } from '@/theme/ThemeProvider'

function MyComponent() {
  const { theme, toggleTheme, setTheme } = useTheme()
  
  return (
    <button onClick={toggleTheme}>
      Cambiar a {theme === 'light' ? 'oscuro' : 'claro'}
    </button>
  )
}
```

### Persistencia
- El tema se guarda en `localStorage`
- Respeta la preferencia del sistema (`prefers-color-scheme`)
- Se aplica automáticamente al cargar

---

## 🧪 Testing

### Configuración
- **Framework:** Vitest
- **Testing Library:** @testing-library/react
- **Environment:** jsdom

### Ejecutar pruebas
```bash
npm run test          # Modo watch
npm run test:ui       # UI interactivo
npm run test:coverage # Con cobertura
```

### Ejemplo de test
```tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Button } from '@/components/ui'

describe('Button', () => {
  it('renders correctly', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByText('Click me')).toBeInTheDocument()
  })
})
```

---

## 🎨 Design Tokens

### Colores
Los colores se extienden desde Carbon Design System:
- `$licitia-primary`: #0f62fe (Carbon blue-60)
- `$licitia-secondary`: #8d3bff (Custom purple)
- `$licitia-success`: #24a148 (Carbon green-60)
- `$licitia-warning`: #f1c21b (Carbon yellow-40)
- `$licitia-error`: #da1e28 (Carbon red-60)

### Espaciado
Usa la escala de Carbon:
- `$licitia-spacing-xs`: 4px
- `$licitia-spacing-sm`: 8px
- `$licitia-spacing-md`: 16px
- `$licitia-spacing-lg`: 32px
- `$licitia-spacing-xl`: 48px

### Uso en SCSS
```scss
@use '@/styles/tokens' as *;

.my-component {
  padding: $licitia-spacing-md;
  color: $licitia-primary;
  border-radius: $licitia-radius-md;
}
```

---

## 📐 Layout

### AppLayout
Layout principal que incluye:
- Header con Carbon Header component
- Navegación con tabs
- Área de contenido principal
- Soporte para temas

```tsx
import { AppLayout } from '@/layouts/AppLayout'

function App() {
  return (
    <AppLayout>
      <YourContent />
    </AppLayout>
  )
}
```

---

## 🚀 Scripts Disponibles

```bash
npm run dev          # Desarrollo (Vite)
npm run build        # Build de producción
npm run preview      # Preview del build
npm run test         # Ejecutar tests
npm run test:ui      # Tests con UI
npm run test:coverage # Tests con cobertura
```

---

## 📚 Recursos

- [Carbon Design System](https://carbondesignsystem.com/)
- [Carbon React Components](https://react.carbondesignsystem.com/)
- [Carbon Design Tokens](https://carbondesignsystem.com/guidelines/color/usage/)
- [React i18next](https://react.i18next.com/)
- [Vitest](https://vitest.dev/)

---

## 🔄 Migración de Componentes Existentes

Para migrar componentes existentes a Carbon:

1. **Reemplaza componentes base:**
   ```tsx
   // Antes
   <button className="custom-button">Click</button>
   
   // Después
   <Button variant="primary">Click</Button>
   ```

2. **Usa Carbon components directamente:**
   ```tsx
   import { DataTable, Table, TableHead, TableRow, TableHeader, TableBody, TableCell } from '@carbon/react'
   ```

3. **Aplica tokens de diseño:**
   ```scss
   // Usa tokens en lugar de valores hardcodeados
   padding: $licitia-spacing-md; // En lugar de padding: 16px;
   ```

---

## ✅ Checklist de Implementación

- [x] Instalación de Carbon Design System
- [x] Configuración de tokens de diseño
- [x] Componentes base (Button, Card, Input)
- [x] Sistema de temas (light/dark)
- [x] Internacionalización (i18n es-CO)
- [x] Layout principal con Carbon
- [x] Configuración de pruebas (Vitest)
- [ ] Migración de componentes existentes
- [ ] Documentación de componentes personalizados

---

**Última actualización:** 2025-11-30

