# 🎬 Plan de Implementación del Frontend — CineGraph

> **Estado**: Aprobado ✅ | **Timeline**: 9-10 semanas | **Última actualización**: 2026-04-02

## 📊 Resumen Ejecutivo

- **Frontend**: 50-60% completado (autenticación, chat, búsqueda, favoritos)
- **Backend**: 11 fases completadas, 25+ endpoints operacionales
- **Gap**: Design system, componentes visuales, refinamiento UX
- **Objetivo**: Completar frontend siguiendo arquitectura correcta, aprovechando lo existente

---

## 🔄 Las 9 Fases

### FASE 0: Configuración Base ⚙️
**Semana 1** | 2-3 días | Dependencias: Ninguna

Establecer design tokens en Tailwind:
- Colores (accent, teal, surface, etc.)
- Tipografía (Bebas Neue, DM Sans)
- Animaciones (pulse-dot, fade-in, slide-up, fill-bar)

**Archivos**: `tailwind.config.ts`, `globals.css`, `lib/utils.ts`

✓ Verificación: `npm run build` sin errores

---

### FASE 1: Componentes Atómicos 🧩
**Semana 1-2** | 5-7 días | Dependencias: Fase 0

Crear 5 componentes reutilizables:

1. **ScoreBar** — Barra de compatibilidad (0-1) con animación
2. **SerendipityBadge** — Badge para películas `serendipityScore > 0.6`
3. **ContextChips** — Chips removibles de mood, companion, energy, runtime
4. **WhyCard** — Card con explicación narrativa del backend
5. **Refactor UI** — Button, Input, Badge con variantes correctas

**Archivos**:
```
components/atoms/
  ├── ScoreBar.tsx
  ├── SerendipityBadge.tsx
  ├── ContextChips.tsx
  ├── WhyCard.tsx
  └── index.ts
```

✓ Verificación: Componentes tipados, animaciones funcionales

---

### FASE 2: Organismos Principales 🏢
**Semana 2-3** | 8-10 días | Dependencias: Fase 1

Construir 3 componentes complejos:

1. **HeroSection** — 2 columnas con búsqueda + RecCard
   - Columna iz: Badge + H1 + SearchPrompt + quick-chips
   - Columna der: Poster + meta + ScoreBar + WhyCard
   - Datos: `GET /api/v1/movies/connections/centrality?limit=1`

2. **MovieCard** — Refactorizar existente
   - Poster + score bar + badge + info + rating
   - SerendipityBadge cuando proceda
   - Hover animations

3. **ChatModule** — Refactorizar con multi-turno
   - Sidebar (historial) | Chat (mensajes) | Panel (contexto)
   - `session_id` en sessionStorage
   - `POST /api/v1/recommendation/chat` multi-turno

**Archivos**: Organismos refactorizados

✓ Verificación: Datos reales del backend, responsive

---

### FASE 3: Carouseles y Grids 🎠
**Semana 3-4** | 5-7 días | Dependencias: Fase 2

Carruseles de homepage y grid de búsqueda:

| Carrusel | Endpoint |
|----------|----------|
| "Porque viste [X]" | `GET /api/v1/movies/connections/neighborhood?title=X` |
| "Basado en favoritos" | `GET /api/v1/movies/connections/centrality?genre=Y` |
| "Explora algo diferente" | `GET /api/v1/movies/connections/centrality` (filtrar serendipity DESC) |

MovieGrid:
- Búsqueda con filtros (género, director, año, runtime)
- Grid responsive
- `GET /api/v1/movies/search`

✓ Verificación: Carruseles y grid cargan datos, responden a filtros

---

### FASE 4: Páginas Principales 📄
**Semana 4-5** | 8-10 días | Dependencias: Fase 2, 3

Integrar componentes en 5 páginas:

1. **HomePage** — HeroSection + 3 carouseles + footer
2. **ChatPage** — ChatModule con sesiones
3. **ExplorePage** — FilterSidebar + MovieGrid
4. **FavoritesPage** — Grid + CRUD de favoritos
5. **ConnectionsPage** — Explorador de caminos entre películas

✓ Verificación: 5 páginas navegan sin errores, mobile responsive

---

### FASE 5: Componentes Avanzados 🚀
**Semana 5-6** | 7-9 días | Dependencias: Fases 2-4, ⚠️ **Backend Fase 6**

#### ⚠️ BLOQUEADOR
**Ejecutar antes de esta fase**:
```bash
cd movie-graph-rag-backend-fastapi
python scripts/compute_network_metrics.py
# Esperar 10-30 min
```

Esto genera:
- Centrality metrics (degree, betweenness, pagerank)
- Community assignments (Louvain)
- Graph topology

Componentes a crear:

1. **TopologicalProfile** — Muestra clasificación del usuario (especialista/equilibrado/explorador)
2. **ClusterSection** — Comunidades de película + películas adyacentes
3. **GraphMinimap** — Mini-grafo interactivo de vecindad

✓ Verificación: Componentes renderizan datos topológicos sin errores

---

### FASE 6: Páginas Avanzadas 📍
**Semana 6-7** | 5-7 días | Dependencias: Fase 5, Backend Fase 6

3 nuevas páginas:

1. **ProfilePage** — Perfil topológico + recomendaciones personalizadas
2. **TopologyPage** — Todas las comunidades interactivas + sugerencias
3. **MovieDetailPage** — Poster + meta + ClusterSection + GraphMinimap + recomendaciones

✓ Verificación: Páginas con datos reales del backend

---

### FASE 7: Refinamiento UX ✨
**Semana 7-8** | 5-7 días | Dependencias: Todas las fases

Pulir experiencia de usuario:

- [ ] Skeletons en lugar de spinners
- [ ] Toast notifications en acciones
- [ ] Transiciones suaves (`animate-slide-up`)
- [ ] Manejo de errores con mensajes amigables
- [ ] Accesibilidad (aria labels, focus states, keyboard nav)

✓ Verificación: Lighthouse ≥ 90, sin console errors

---

### FASE 8: Testing & Optimización 🧪
**Semana 8-9** | 5-7 días | Dependencias: Todas las fases

- [ ] Tests unitarios (componentes atómicos)
- [ ] Tests integración (flujos: chat, búsqueda, favoritos)
- [ ] E2E tests (Playwright)
- [ ] Performance optimizations (code splitting, lazy loading)
- [ ] Bundle analysis

✓ Verificación: `npm run test` pasa ✓, coverage ≥ 70%, `npm run build` sin warnings

---

### FASE 9: Deployment & Docs 🚢
**Semana 9-10** | 3-5 días | Dependencias: Fase 8

- [ ] Docker setup (Dockerfile + docker-compose.yml)
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] README + setup local docs
- [ ] Environment variables (.env.example)

✓ Verificación: Deploy exitoso a staging/producción

---

## 🎯 Hitos Clave

| Hito | Fin de Semana | Entrega |
|------|---|---|
| 1 | Semana 2 | Componentes base + HeroSection funcional |
| 2 | Semana 4 | Homepage + Chat + Explore completos |
| 3 | Semana 6 | ProfilePage + TopologyPage con datos reales |
| 4 | Semana 8 | Suite de tests, Lighthouse ≥90, sin errores |
| 5 | Semana 10 | En producción |

---

## ⚠️ Bloqueadores Críticos

### Backend Fase 6 Script
**Fases 5-6 requieren**: `python scripts/compute_network_metrics.py` ejecutado en backend

Esto genera datos de:
- Topología global de grafo
- Community assignments (Louvain)
- Centrality metrics
- Serendipity scores

**Timeline**: +10-30 min en backend

### Endpoints Operacionales Ahora
✅ `POST /recommendation` (single-turn)
✅ `POST /recommendation/chat` (multi-turno)
✅ `GET /movies/search`
✅ `GET /movies/connections/*`
✅ Favoritos CRUD
⚠️ `/graph/topology` (requiere Fase 6)
⚠️ `/users/me/topology` (requiere Fase 6)
⚠️ `serendipityScore` (requiere Fase 6)

---

## 📁 Archivos a Crear/Modificar

### Nuevos (15+)
```
components/atoms/{ScoreBar,SerendipityBadge,ContextChips,WhyCard}.tsx
components/organisms/{TopologicalProfile,ClusterSection,GraphMinimap}.tsx
hooks/{useMovieDetail,useExplore,useChatSession,useUserProfile}.ts
lib/{constants.ts,validators.ts}
app/{profile,topology,movie-detail}/page.tsx
__tests__/{components,e2e,integration}/*.test.ts
Dockerfile, docker-compose.yml, .env.example
```

### Modificados (10+)
```
tailwind.config.ts (design tokens)
globals.css (CSS variables)
lib/utils.ts
components/organisms/{HeroSection,MovieCard,ChatModule,MovieGrid}.tsx
app/{page,chat,search}.tsx
```

---

## 🧪 Testing Strategy

```bash
# Unitarios
npm run test -- components/atoms

# Integración
npm run test -- components/organisms app/

# E2E
npm run test:e2e -- search.spec.ts
npm run test:e2e -- chat.spec.ts
npm run test:e2e -- favorites.spec.ts

# Build & Performance
npm run build
npm run analyze
```

---

## 📊 Riesgos & Mitigación

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-----------|--------|-----------|
| Backend Fase 6 script no ejecuta | Media | Alto | Ejecutar ANTES de Sem 5, tener fallback mock |
| Scope creep (nuevas features) | Alta | Media | Sprint planning riguroso |
| Performance con grafo grande | Media | Medio | Mobile-first, lazy loading, caching |
| Cambios API backend | Baja | Alto | Versionado `/api/v1`, validación tipos |

---

## 🔧 Setup Local

```bash
# 1. Frontend
git clone <repo>
cd movie-graph-rag-frontend
npm install
cp .env.example .env
npm run dev  # http://localhost:3000

# 2. Backend (terminal separada)
cd ../movie-graph-rag-backend-fastapi
source .venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000

# 3. (Antes de Fase 5) Backend Fase 6
python scripts/compute_network_metrics.py  # ~10-30 min
```

---

## ✅ Checklist de Inicio

- [ ] Leer completamente FRONTEND_CONTEXT.md
- [ ] Revisar estado actual del código
- [ ] Ejecutar `npm run build` localmente
- [ ] Confirmar conectividad con backend (`GET /api/v1/health`)
- [ ] Ejecutar backend Fase 6 script (antes de Fase 5)
- [ ] Crear rama feature (`git checkout -b feature/implementation-phase-0`)
- [ ] Comenzar Fase 0

---

## 📚 Referencias

- **Plan detallado**: `C:\Users\luish\.claude\plans\lovely-floating-mango.md`
- **Frontend Context**: `FRONTEND_CONTEXT.md`
- **Backend Docs**: Backend README + ARQUITECTURA_FASES.md
- **Servicios existentes**: `services/*.service.ts`

---

## 👤 Owner & Timeline

- **Frontend Developer**: Luis Fernando Hernández Solís
- **Backend Developer**: Luis Fernando Hernández Solís
- **Asesor**: Universidad del Valle
- **Ideal Timeline**: Feb-Abril 2026
- **Duraci total**: 9-10 semanas (2-2.5 meses)

---

**✨ Listo para comenzar Fase 0**
