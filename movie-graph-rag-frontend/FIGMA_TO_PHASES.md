# 🎬 Figma Designs → Implementation Phases Mapping

> Referencia visual para mapear los diseños de Figma a las fases de implementación del frontend

---

## 📋 Resumen de Vistas

| Vista | Imagen | Fase Principal | Componentes Clave |
|-------|--------|---------------|--------------------|
| HomePage | `image.png` | Fase 2-4 | HeroSection, RecCard, Carouseles |
| MovieDetail | `image-1.png` | Fase 5-6 | ClusterSection, GraphMinimap, ScoreBar |
| Chat | `image-2.png` | Fase 2, 4 | ChatModule, ContextChips, MovieCard inline |
| UserProfile | `image-3.png` | Fase 5-6 | TopologicalProfile, ClusterStats |
| Explore | `image-4.png` | Fase 3-4 | MovieGrid, FilterSidebar, MovieCard |

---

## 🏠 1. HomePage (image.png)

### Componentes Visibles
```
┌─────────────────────────────────────────┐
│ Navbar (CINERAPH logo, menu, auth)      │ ← Fase 4 basic structure
├─────────────────────────────────────────┤
│ HeroSection (izq: H1 + SearchPrompt)    │ ← Fase 2 (ScoreBar, WhyCard, ContextChips)
│ RecCard (der: Poster + ScoreBar + Meta) │
├─────────────────────────────────────────┤
│ Carousel 1: "Porque viste..."           │ ← Fase 3 (RecommendationCarousel)
│ 6 MovieCards con score bars             │
├─────────────────────────────────────────┤
│ Carousel 2: "Basado en tus favoritos"   │
│ 6 MovieCards                            │
├─────────────────────────────────────────┤
│ Carousel 3: "Explora algo diferente"    │
│ 6 MovieCards con SerendipityBadge       │
├─────────────────────────────────────────┤
│ "Recomendaciones temáticas"             │ ← Fase 7 (refinamiento)
│ Quick chips: "Estresado", "Familia", etc│
├─────────────────────────────────────────┤
│ Footer                                  │ ← Fase 4
└─────────────────────────────────────────┘
```

### Fases que lo Construyen
- **Fase 0**: Colores teal/accent en Tailwind, animaciones base
- **Fase 1**: ScoreBar, SerendipityBadge, ContextChips, WhyCard
- **Fase 2**: HeroSection, MovieCard, Navbar
- **Fase 3**: RecommendationCarousel (3 instancias)
- **Fase 4**: HomePage template, integración de componentes
- **Fase 7**: Animaciones slide-up, transiciones suaves

### Endpoints Usados
```typescript
GET /api/v1/movies/connections/centrality?limit=1     // RecCard película destacada
GET /api/v1/movies/connections/neighborhood?title=X   // Carousel "Porque viste X"
GET /api/v1/movies/connections/centrality?genre=Y     // Carousel "Basado en favoritos"
GET /api/v1/movies/connections/centrality             // Carousel "Explora diferente" (filtrar por serendipityScore)
```

---

## 🎞️ 2. MovieDetail (image-1.png)

### Componentes Visibles
```
┌─────────────────────────────────────────┐
│ Navbar + Back button                    │ ← Fase 4
├──────────────────────┬──────────────────┤
│ Col Izq:             │ Col Der:         │
│ - Poster             │ - Title          │ ← Fase 2 (MovieCard refactored)
│ - Genre · Director   │ - Meta           │
│ - Runtime · Rating   │ - ScoreBar       │
├──────────────────────┼──────────────────┤
│ "¿Por qué esto?"     │ Context Panel    │ ← Fase 2 (WhyCard)
│ WhyCard explanation  │ Mood/Energy/etc  │ ← Fase 5 (ClusterSection inicio)
├──────────────────────┼──────────────────┤
│ "En su comunidad"    │ "Distribuído en" │
│ ClusterSection:      │ Genre bars       │ ← Fase 5 (ClusterSection)
│ - Intra-cluster pics │ Community bars   │
│ - Adjacent clusters  │                  │
├──────────────────────┴──────────────────┤
│ GraphMinimap (mini-grafo interactivo)   │ ← Fase 5 (GraphMinimap)
├─────────────────────────────────────────┤
│ "Recomendadas para ti"                  │ ← Fase 3 (MovieCarousel)
│ 4 MovieCards                            │
├─────────────────────────────────────────┤
│ Footer                                  │ ← Fase 4
└─────────────────────────────────────────┘
```

### Fases que lo Construyen
- **Fase 1**: ScoreBar, badges, basic UI
- **Fase 2**: MovieCard hero refactored, WhyCard
- **Fase 3**: Related movies carousel
- **Phase 5**: ⚠️ **BLOCKER** — ClusterSection, GraphMinimap (requiere backend Phase 6)
- **Fase 6**: MovieDetailPage template integración completa
- **Fase 7**: Animaciones, transiciones suaves

### Endpoints Usados
```typescript
GET /api/v1/movies/{title}                // Detalles película
GET /api/v1/movies/{title}/cluster        // ⚠️ ClusterSection (Fase 5 blocker)
GET /api/v1/movies/connections/neighborhood?title={title}&depth=2  // GraphMinimap
GET /api/v1/movies/connections/centrality?genre={genreName}        // Recommendations
```

---

## 💬 3. Chat (image-2.png)

### Componentes Visibles
```
┌──────────────────────────────────────────┐
│ Navbar + "New Chat" button               │ ← Fase 4
├───────────┬──────────────────┬───────────┤
│ Sidebar:  │ Chat Messages:   │ Panel Der│
│           │                  │ (Desktop│
│ Sessions  │ - Sistema: dark  │ only)   │
│ - New     │   bubbles        │         │
│ - History │ - Usuario: orange│ Context:│
│ - Recent  │   bubbles        │ - Mood  │
│           │ - MovieCards (≤5)│ - Energy│
│ Quick     │   inline         │ - Genre │
│ Prompts   │                  │ - Stats │
│           │ ContextChips     │         │
│           │ (removibles)     │ Strategy│
│           │                  │ Metrics │
│           │ Input + Send     │         │
└───────────┴──────────────────┴─────────┘
```

### Fases que lo Construyen
- **Fase 1**: ContextChips, ScoreBar, badges
- **Fase 2**: ChatModule (architecture multi-turno)
- **Fase 4**: ChatPage template, session management layout
- **Fase 7**: Animaciones de burbujas, transiciones
- **Fase 8**: Testing flujo chat multi-turno

### Endpoints Usados
```typescript
POST /api/v1/recommendation/chat          // Multi-turn chat (session_id, messages)
GET /api/v1/users/me                      // Avatar + username en panel der
// sessionStorage: session_id (UUID v4)
```

---

## 👤 4. UserProfile (image-3.png)

### Componentes Visibles
```
┌─────────────────────────────────────────┐
│ Navbar + User settings button           │ ← Fase 4
├─────────────────────────────────────────┤
│ Header:                                 │ ← Fase 6
│ Avatar (LH iniciales)                   │
│ Nombre: "Luis Hernández Solís"          │
│ Stats: 47 favoritos, 12 comunidades, 4 👥
├─────────────────────────────────────────┤
│ TopologicalProfile:                     │ ← Fase 5 (⚠️ BLOCKER)
│ - explorationIndex: 0.65 (score bar)    │
│ - "Equilibrado" classification badge    │
│ - Dominant clusters (top 5 with bars)   │
│ - Unexplored adjacent clusters          │
│ - Trend: "Especializando ↘"             │
├─────────────────────────────────────────┤
│ "Distribución por géneros"              │
│ Horizontal bar charts (Comedy, Drama...)│
├─────────────────────────────────────────┤
│ "Explora otros espacios"                │
│ Cards de comunidades recomendadas       │
├─────────────────────────────────────────┤
│ "MisFavoritos más relevantes"           │
│ 4 MovieCards                            │
├─────────────────────────────────────────┤
│ "Historial de recomendaciones"          │ ← Fase 8 (history service)
│ Timeline de searches/chats               │
└─────────────────────────────────────────┘
```

### Fases que lo Construyen
- **Fase 1**: Badges, score bars, basic UI
- **Fase 2**: MovieCard, basic layout
- **Fase 5**: ⚠️ **TopologicalProfile, ClusterStats** (requiere backend Phase 6)
- **Fase 6**: ProfilePage template integración
- **Fase 7**: Animaciones, visualización datos
- **Fase 8**: Testing de perfil + topología

### Endpoints Usados
```typescript
GET /api/v1/users/me                      // Nombre, avatar, stats
GET /api/v1/users/me/topology             // ⚠️ TopologicalProfile (Fase 5 blocker)
GET /api/v1/users/me/favorites            // Mi Favoritos
GET /api/v1/graph/topology                // ⚠️ Distribución géneros (Fase 5)
```

---

## 🔍 5. Explore (image-4.png)

### Componentes Visibles
```
┌──────────────────────────────────────────┐
│ Navbar + Search bar                      │ ← Fase 4
├──────────┬───────────────────────────────┤
│ Sidebar: │ Main Grid:                    │
│ Filters  │ 4-columna grid (responsive)   │ ← Fase 3 (MovieGrid)
│          │                               │
│ Género   │ MovieCard × N:                │
│ - Comedy │ - Poster                      │
│ - Drama  │ - Score bar                   │
│ - Sci-Fi │ - Compat %                    │
│ - Acción │ - Fav button                  │
│          │ - Meta: género · año          │
│ Director │ - Rating                      │
│ - [input]│                               │
│          │ Hover: scale + CTA            │
│ Year     │                               │
│ - desde  │ Infinite scroll / Pagination  │
│ - hasta  │                               │
│          │                               │
│ Runtime  │                               │
│ - slider │                               │
│          │                               │
│ Rating   │                               │
│ - 5 stars│                               │
│          │                               │
│ Sort     │                               │
│ - Rating │                               │
│ - Year   │                               │
│ - Recentl│                               │
│          │                               │
│ Pagination bottom                        │
└──────────┴───────────────────────────────┘
```

### Fases que lo Construyen
- **Fase 1**: Input, Button, ScoreBar, Badge
- **Fase 2**: MovieCard refactored
- **Fase 3**: FilterSidebar, MovieGrid con búsqueda
- **Fase 4**: ExplorePage template, navigation
- **Fase 7**: Animaciones grid, slide-up
- **Fase 8**: Testing filters + búsqueda

### Endpoints Usados
```typescript
GET /api/v1/movies/search?q=&genre=&director=&yearFrom=&yearTo=&limit=30
GET /api/v1/movies/autocomplete?q=  // Para director/actor input
```

---

## 🎯 Mapeo Fase → Vista

| Fase | Contribuye a | Componentes | Estados |
|------|--------------|-------------|---------|
| **0** | Todas | Design tokens (Tailwind) | ✓ Configuración |
| **1** | Todas | Átomos base (Button, Input, ScoreBar, etc) | ✓ UI foundation |
| **2** | HomePage, Chat, MovieDetail | HeroSection, ChatModule, MovieCard, Navbar | ✓ Organismos |
| **3** | HomePage, Explore | RecommendationCarousel, MovieGrid, FilterSidebar | ✓ Features |
| **4** | Todas (templates) | HomePage, ChatPage, ExplorePage, FavoritesPage | ✓ Pages |
| **5** | MovieDetail, UserProfile | ⚠️ TopologicalProfile, ClusterSection, GraphMinimap | ⏳ BLOCKER |
| **6** | MovieDetail, UserProfile | ⚠️ MovieDetailPage, ProfilePage, TopologyPage | ⏳ BLOCKER |
| **7** | Todas | Skeletons, toasts, animaciones, a11y | ✓ Polish |
| **8** | Todas | Tests, optimizaciones, performance | ✓ Quality |
| **9** | All | Docker, CI/CD, deployment | ✓ Production |

---

## ⚠️ Blockers

### Fase 5 & 6 — Backend Phase 6 Script
**Imágenes afectadas**: MovieDetail, UserProfile

**Requisito**: Ejecutar en backend ANTES de Fase 5
```bash
cd movie-graph-rag-backend-fastapi
python scripts/compute_network_metrics.py
# ⏳ 10-30 minutos
```

**Sin este script**:
- ❌ No se pueden mostrar comunidades (ClusterSection)
- ❌ No se puede mostrar grafo de vecindad (GraphMinimap)
- ❌ No se puede mostrar topología del usuario (TopologicalProfile)
- ❌ No se puede calcular serendipity scores (SerendipityBadge)

---

## ✅ Roadmap Híper-Visual

```
SEMANA 1-2                      SEMANA 3-4
┌──────────────────┐            ┌──────────────────┐
│ Fase 0: Tokens   │            │ Fase 3: Grids    │
│ Fase 1: Átomos   │            │ Carouseles       │
└──┬───────────────┘            └──┬───────────────┘
   │                                │
   └─→ FASE 2: ORGANISMOS           │
       HeroSection ✓                │
       MovieCard ✓         ────→ Visuales en HomePage/Explore
       ChatModule ✓
       │
       └─→ FASE 4: PAGES
           HomePage OK ✓
           ChatPage OK ✓
           ExplorePage OK ✓

SEMANA 5-6                      SEMANA 7-8
⚠️ BACKEND BLOCKER             ┌──────────────────┐
python compute_network...      │ Fase 7: UX ✨    │
│                              │ Fase 8: Tests 🧪 │
└─→ FASE 5: ADVANCED           └──┬───────────────┘
    TopologicalProfile ✓          │
    ClusterSection ✓      ────→ MovieDetail ✓
    GraphMinimap ✓               UserProfile ✓
    │
    └─→ FASE 6: PAGES
        MovieDetailPage ✓
        ProfilePage ✓
        TopologyPage ✓
```

---

## 🚀 Inicio Recomendado

1. **AHORA**: Fase 0 (Tailwind tokens, ~1 día)
2. **Día 2-5**: Fase 1 (Átomos, ~4 días) → Los átomos sirven en TODAS las vistas
3. **Día 6-12**: Fase 2 (Organismos principales, ~7 días) → HeroSection, MovieCard, ChatModule
4. **Antes de Semana 5**: Backend script → `python scripts/compute_network_metrics.py`
5. **Día 13+**: Fase 3-4 en paralelo, luego Fase 5-6

---

## 📌 Notas Finales

- **móvil-first**: Todos los diseños incluyen breakpoints responsivos
- **Dark mode**: Ya configurado en next-themes, diseños ya son oscuros
- **Animaciones**: phase-reveal, slide-up, pulse-dot usadas en varias vistas
- **Accesibilidad**: Keyboard nav, ARIA labels en todos los componentes interactivos
- **Performance**: Lazy loading imágenes, skeleton loaders en transiciones

