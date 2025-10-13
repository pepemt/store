# 🎨 Paleta de Colores - La Tiendita de la Esquina

## 📋 Colores Principales

| Color | Código | Uso Recomendado | Descripción |
|-------|--------|-----------------|-------------|
| 🌸 **Primary** | `#C344AB` | Botones principales, enlaces, elementos destacados | Rosa/Magenta vibrante - Color principal de la marca |
| 💧 **Secondary** | `#85E3FF` | Botones secundarios, acentos, hover states | Azul cielo claro - Color complementario |
| 🌺 **Accent Pink** | `#FFD7F7` | Fondos suaves, tarjetas, elementos decorativos | Rosa pastel - Para elementos suaves |
| ☁️ **Accent Blue** | `#D9F7FF` | Fondos de secciones, bordes suaves | Azul muy claro - Para fondos delicados |
| 🏮 **Background** | `#F9FAFC` | Fondo principal de la aplicación | Gris muy claro - Base neutral |
| ⚪ **White** | `#FFFFFF` | Tarjetas, modales, contenido principal | Blanco puro - Contraste y limpieza |

## 🎯 Variables CSS Definidas

### Colores Base
```css
--color-primary: #C344AB;
--color-secondary: #85E3FF;
--color-accent-pink: #FFD7F7;
--color-accent-blue: #D9F7FF;
--color-background: #F9FAFC;
--color-white: #FFFFFF;
```

### Gradientes Predefinidos
```css
--gradient-primary: linear-gradient(135deg, #C344AB 0%, #85E3FF 100%);
--gradient-secondary: linear-gradient(135deg, #FFD7F7 0%, #D9F7FF 100%);
--gradient-hero: linear-gradient(135deg, #D9F7FF 0%, #FFD7F7 100%);
```

### Sombras con Colores de la Paleta
```css
--shadow-primary: 0 8px 32px rgba(195, 68, 171, 0.3);
--shadow-secondary: 0 8px 32px rgba(133, 227, 255, 0.3);
--shadow-soft: 0 4px 15px rgba(195, 68, 171, 0.1);
```

## 🛠️ Cómo Usar

### En CSS
```css
.mi-elemento {
  background: var(--color-primary);
  color: var(--text-white);
  box-shadow: var(--shadow-primary);
}

.mi-boton {
  background: var(--gradient-primary);
  border: 2px solid var(--color-primary);
}
```

### Clases de Utilidad
```html
<div class="bg-primary text-white shadow-primary">
  Elemento con fondo principal
</div>

<div class="gradient-secondary shadow-soft">
  Elemento con gradiente secundario
</div>
```

## 📱 Aplicación por Componentes

### Header
- Fondo: `var(--color-white)`
- Sombra: `var(--shadow-soft)`
- Enlaces: `var(--color-primary)`

### Botones
- **Primarios**: `var(--gradient-primary)` con `var(--shadow-primary)`
- **Secundarios**: `var(--color-white)` con borde `var(--color-primary)`

### Formularios
- Fondo inputs: `var(--color-white)`
- Borde focus: `var(--color-primary)`
- Sombra focus: `var(--input-shadow-focus)`

### Chat
- Usuario: `var(--gradient-primary)`
- Asistente: `var(--color-white)`
- Fondo ventana: `var(--color-white)`

### Carrusel
- Fondos rotativos usando todos los colores de la paleta
- Indicadores: `var(--carousel-dot)` y `var(--carousel-dot-active)`

## 🎨 Combinaciones Recomendadas

### Para CTAs (Call to Action)
```css
background: var(--gradient-primary);
color: var(--text-white);
box-shadow: var(--shadow-primary);
```

### Para Cards
```css
background: var(--color-white);
border: 1px solid var(--color-accent-blue);
box-shadow: var(--shadow-soft);
```

### Para Fondos de Sección
```css
background: var(--gradient-hero);
```

### Para Estados Hover
```css
.elemento:hover {
  background: var(--button-primary-hover);
  box-shadow: var(--shadow-medium);
}
```

## 🔧 Mantenimiento

Para cambiar la paleta de colores:
1. Edita los valores en `src/styles/colors.css`
2. Los cambios se aplicarán automáticamente en toda la app
3. Mantén la consistencia usando siempre las variables CSS

## 🌈 Accesibilidad

- Contraste suficiente entre texto y fondo
- Colores no son el único medio de comunicación
- Tema oscuro preparado para implementación futura

---

**Archivo de variables**: `src/styles/colors.css`
**Última actualización**: 3 de octubre de 2025