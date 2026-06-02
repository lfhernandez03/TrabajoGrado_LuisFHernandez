# movie-graph-rag-frontend

Interfaz de usuario de **MOVIQ**, sistema de recomendación cinematográfica semántica basado en grafo de conocimiento. Construida con Next.js 16, TypeScript y Tailwind CSS v4, ofrece búsqueda conversacional, exploración del grafo de películas y recomendaciones personalizadas.

## Tecnologías

| Categoría | Tecnología |
|---|---|
| Framework | Next.js 16 (App Router) |
| Lenguaje | TypeScript 5 |
| Estilos | Tailwind CSS v4 |
| Componentes | Radix UI (Dialog, Avatar, DropdownMenu, etc.) |
| HTTP | Axios |
| Notificaciones | Sonner |
| Íconos | Lucide React |
| Temas | next-themes |

## Requisitos previos

- Node.js 18+
- Backend API corriendo (ver `movie-graph-rag-backend-fastapi`)

## Instalación

```bash
cd movie-graph-rag-frontend
npm install
```

## Variables de entorno

Crear un archivo `.env.local` en la raíz del proyecto:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_PREFIX=/api/v1
```

## Ejecución

```bash
# Desarrollo
npm run dev

# Producción
npm run build
npm start
```

La aplicación queda disponible en `http://localhost:3000`.

## Estructura del proyecto

```
app/                      # App Router de Next.js
├── (auth)/               # Rutas de autenticación (login, register)
├── chat/                 # Módulo de chat semántico
├── connections/          # Explorador del grafo de conexiones
├── favorites/            # Favoritos del usuario
├── profile/              # Perfil de usuario
├── search/               # Búsqueda con filtros
├── topology/             # Vista de perfil topológico
└── design-system/        # Referencia visual de componentes

components/
├── ui/                   # Átomos base (Button, Badge, Input, Card…)
├── atoms/                # Re-exports de átomos
├── molecules/            # Moléculas (ScoreBar, ContextChips, WhyCard…)
├── organisms/            # Organismos (Navbar, HeroSection, MovieCard, MovieGrid…)
├── home/                 # Componentes de la página de inicio
├── chat/                 # Burbujas y componentes del chat
├── recommendation/       # Cards de recomendación
└── shared/               # ProtectedRoute, Providers

services/                 # Clientes HTTP por dominio
hooks/                    # Custom React hooks
lib/                      # Utilidades, estilos del grafo, caché, SPARQL
```

## Vistas principales

### Home (`/`)
Hero con la recomendación personalizada del día y tres carruseles:
- **"Because you watched"** – vecindad de 2 saltos en el grafo de películas
- **"Like"** – vecindad basada en otro favorito
- **"Explore new genres"** – películas de clusters no explorados

En cold start (sin favoritos), los carruseles rotan por género según el día de la semana.

### Chat (`/chat`)
Interfaz de chat en tres columnas para consultas en lenguaje natural. El backend extrae contexto semántico (estado de ánimo, compañía, tiempo disponible, género), genera SPARQL y retorna películas con `compatibilityScore`. Se muestra la explicación narrativa generada por LLM.

### Search (`/search`)
Búsqueda con filtros de género, año, director y duración. Grid de 4 columnas con `MovieCard`.

### Connections (`/connections`)
Explorador visual del grafo de conexiones entre películas. Permite trazar caminos entre dos títulos con profundidad configurable.

### Favorites (`/favorites`)
Colección de películas marcadas por el usuario, con acceso rápido a detalles y búsqueda de similares.

### Profile (`/profile`)
Perfil del usuario con historial de recomendaciones y acceso al perfil topológico (clusters explorados y adyacentes).

## Diseño de componentes

El sistema sigue diseño atómico:

```
Átomos (ui/)          →  Button, Badge, Input, Card, Dialog…
Moléculas (molecules/) →  ScoreBar, SerendipityBadge, ContextChips, WhyCard
Organismos (organisms/)→  Navbar, HeroSection, MovieCard, MovieGrid,
                          RecommendationCarousel, FilterSidebar…
```

Los tokens de color están definidos como variables CSS en `globals.css`:

| Token | Uso |
|---|---|
| `--bg` | Fondo principal |
| `--surface` | Cards y paneles |
| `--accent` | Acción primaria (naranja) |
| `--accent2` | Acción secundaria |
| `--teal` | Indicadores semánticos |
| `--muted` | Texto secundario |

## Servicios HTTP

Cada dominio tiene su propio servicio en `services/`:

| Servicio | Descripción |
|---|---|
| `auth.service.ts` | Login, registro, perfil |
| `movies.service.ts` | Búsqueda, autocomplete, centralidad, vecindad, clusters |
| `chat.service.ts` | Recomendación semántica y actividad |
| `favorites.service.ts` | CRUD de favoritos |
| `history.service.ts` | Historial de recomendaciones |
| `graph.service.ts` | Explorador de conexiones |
| `topology.service.ts` | Perfil topológico del usuario |
| `clusters.service.ts` | Películas por cluster |

## Autenticación

Todas las rutas excepto `/login` y `/register` están protegidas por `ProtectedRoute`, que verifica el token JWT almacenado en `localStorage` y redirige al login si la sesión expiró.

## Build y lint

```bash
npm run build   # TypeScript + Next.js build
npm run lint    # ESLint
```
