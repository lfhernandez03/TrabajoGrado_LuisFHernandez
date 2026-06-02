# Manual Técnico — CineSemantico

**Sistema de Recomendación Semántica de Películas basado en Grafos de Conocimiento y GraphRAG**

> Trabajo de Grado · Universidad del Valle · Escuela de Ingeniería de Sistemas y Computación
> Autor: Luis F. Hernández · 2026

---

## Tabla de Contenidos

1. [Descripción Técnica del Sistema](#1-descripción-técnica-del-sistema)
2. [Stack Tecnológico](#2-stack-tecnológico)
3. [Prerrequisitos](#3-prerrequisitos)
4. [Estructura del Proyecto](#4-estructura-del-proyecto)
5. [Configuración de Variables de Entorno](#5-configuración-de-variables-de-entorno)
6. [Instalación y Ejecución del Backend](#6-instalación-y-ejecución-del-backend)
7. [Instalación y Ejecución del Frontend](#7-instalación-y-ejecución-del-frontend)
8. [Arquitectura del Sistema](#8-arquitectura-del-sistema)
9. [Ontologías y Modelo de Conocimiento](#9-ontologías-y-modelo-de-conocimiento)
10. [Pipeline de Recomendación](#10-pipeline-de-recomendación)
11. [Scripts de Utilidad](#11-scripts-de-utilidad)
12. [Referencia de Endpoints](#12-referencia-de-endpoints)

---

## 1. Descripción Técnica del Sistema

CineSemantico es un sistema de recomendación de películas que integra tres capas de tecnología:

- **Grafo de conocimiento RDF/OWL** modelado en tres ontologías complementarias (dominio cinematográfico, contexto del usuario y puente de compatibilidad), almacenadas en Apache Jena Fuseki.
- **GraphRAG** (*Graph Retrieval-Augmented Generation*): los LLMs traducen la consulta en lenguaje natural a SPARQL y ejecutan la recuperación sobre el triple store.
- **Análisis de redes complejas** (NetworkX + algoritmo Louvain) para calcular comunidades, centralidades y perfiles topológicos de usuarios.

---

## 2. Stack Tecnológico

### Backend

| Componente | Tecnología | Versión |
|---|---|---|
| Framework web | FastAPI | ≥ 0.115 |
| Servidor ASGI | Uvicorn | ≥ 0.30 |
| Lenguaje | Python | 3.11+ |
| Base de datos documental | MongoDB (PyMongo) | ≥ 4.8 |
| Triple store RDF | Apache Jena Fuseki | 4.x |
| LLM principal | Google Gemini Flash 2.5 | `gemini-2.5-flash` |
| LLM auxiliar | Llama 3.3 70B via Groq | `llama-3.3-70b-versatile` |
| Análisis de redes | NetworkX + python-louvain | ≥ 3.0 / ≥ 0.16 |
| Validación de datos | Pydantic v2 | ≥ 2.8 |
| Autenticación | JWT (python-jose + bcrypt) | HS256 / 24 h |

### Frontend

| Componente | Tecnología | Versión |
|---|---|---|
| Framework | Next.js | 16.1.4 |
| Librería UI | React | 19.2.3 |
| Estilos | Tailwind CSS | 4.x |
| Componentes accesibles | Radix UI | 1.x / 2.x |
| Cliente HTTP | Axios | ≥ 1.13 |
| Notificaciones | Sonner | ≥ 2.0 |
| Iconos | Lucide React | ≥ 0.563 |
| Lenguaje | TypeScript | 5.x |

---

## 3. Prerrequisitos

### Software requerido

| Herramienta | Versión mínima | Verificación |
|---|---|---|
| Python | 3.11 | `python --version` |
| Node.js | 18.x | `node --version` |
| npm | 9.x | `npm --version` |
| MongoDB | 6.x | Servicio activo en `localhost:27017` |
| Apache Jena Fuseki | 4.x | Servicio activo en `localhost:3030` |
| Git | — | `git --version` |

### Claves API externas (gratuitas)

| Servicio | Variable de entorno | Obtención |
|---|---|---|
| Google AI Studio | `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com) → *Get API key* |
| Groq Cloud | `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) → *API Keys* |

> Ambos servicios ofrecen nivel gratuito suficiente para desarrollo y evaluación. Las claves son requeridas para que el pipeline de recomendación funcione; sin ellas la API arranca pero devuelve error en los endpoints de recomendación.

---

## 4. Estructura del Proyecto

```
TrabajoGrado_LuisFHernandez/
├── movie-graph-rag-backend-fastapi/    ← API REST (Python/FastAPI)
│   ├── app/
│   │   ├── api/v1/endpoints/           ← Routers HTTP
│   │   ├── core/                       ← Configuración, seguridad
│   │   ├── domain/                     ← Entidades y puertos (interfaces)
│   │   ├── application/use_cases/      ← Casos de uso (lógica de negocio)
│   │   └── adapters/repositories/      ← Implementaciones concretas (MongoDB, Fuseki)
│   ├── scripts/                        ← Scripts de utilidad y pruebas
│   ├── pyproject.toml                  ← Dependencias y metadatos del proyecto
│   └── .env                            ← Variables de entorno (NO versionar)
│
├── movie-graph-rag-frontend/           ← Interfaz web (Next.js)
│   ├── app/                            ← Páginas y layouts (App Router)
│   │   ├── (auth)/                     ← Login y registro
│   │   ├── chat/                       ← Chat de recomendación
│   │   ├── search/                     ← Búsqueda avanzada
│   │   ├── favorites/                  ← Favoritos del usuario
│   │   ├── profile/                    ← Perfil topológico
│   │   ├── connections/                ← Explorador de conexiones
│   │   └── topology/                   ← Dashboard del grafo
│   ├── components/                     ← Componentes reutilizables
│   │   ├── ui/                         ← Átomos base (Button, Badge, Input)
│   │   ├── molecules/                  ← Componentes compuestos
│   │   └── organisms/                  ← Bloques de página
│   ├── lib/                            ← Utilidades, cliente HTTP, tipos
│   ├── package.json
│   └── .env.local                      ← Variables de entorno del frontend
│
└── movie-graph-rag-ontologies/         ← Ontologías OWL y pipeline de datos
    ├── movie-ontology/                 ← Ontología del dominio cinematográfico
    ├── context-ontology/               ← Ontología de contexto del usuario
    └── bridge-ontology/                ← Ontología de compatibilidad
```

---

## 5. Configuración de Variables de Entorno

### Backend — archivo `.env`

Cree el archivo `.env` en la raíz de `movie-graph-rag-backend-fastapi/`. A continuación se detallan todas las variables reconocidas por el sistema:

```ini
# ── Aplicación ────────────────────────────────────────────────────────────────
APP_ENV=development          # "development" | "production"
APP_PORT=8000                # Puerto en que escucha Uvicorn

# ── MongoDB ───────────────────────────────────────────────────────────────────
MONGO_URI=mongodb://localhost:27017/movie-graph-rag
# Si MongoDB requiere autenticación:
# MONGO_URI=mongodb://usuario:contraseña@localhost:27017/movie-graph-rag?authSource=admin

# ── Apache Jena Fuseki ────────────────────────────────────────────────────────
FUSEKI_URL=http://localhost:3030
FUSEKI_DATASET=Cine          # Nombre del dataset dentro de Fuseki
FUSEKI_USER=admin            # Dejar vacío si Fuseki no requiere autenticación
FUSEKI_PASSWORD=admin
FUSEKI_TIMEOUT_SECONDS=8     # Tiempo máximo de espera por consulta SPARQL
FUSEKI_MAX_RETRIES=3         # Reintentos ante fallo de Fuseki

# ── Seguridad JWT ─────────────────────────────────────────────────────────────
# REQUERIDO. El sistema no arranca si esta variable está vacía.
JWT_SECRET=cambie_esto_por_una_cadena_larga_y_aleatoria

# ── LLMs (REQUERIDO para recomendaciones) ────────────────────────────────────
GEMINI_API_KEY=su_clave_de_google_ai_studio
GEMINI_MODEL=gemini-2.5-flash

GROQ_API_KEY=su_clave_de_groq_cloud
GROQ_MODEL=llama-3.3-70b-versatile

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS=http://localhost:3000

# ── Administración ────────────────────────────────────────────────────────────
# Emails separados por coma. Al registrarse con uno de estos emails
# el usuario recibe automáticamente el rol "admin".
ADMIN_EMAILS=su_email@ejemplo.com
```

> **Validaciones al arranque**: el sistema lanza `ValueError` y se detiene si `JWT_SECRET` está vacío, si `APP_ENV=production` con `APP_DEBUG=True`, o si se define `FUSEKI_USER` sin `FUSEKI_PASSWORD`.

### Frontend — archivo `.env.local`

Cree el archivo `.env.local` en la raíz de `movie-graph-rag-frontend/`:

```ini
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_PREFIX=/api/v1
```

---

## 6. Instalación y Ejecución del Backend

### Crear el entorno virtual e instalar dependencias

```bash
cd movie-graph-rag-backend-fastapi

python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate

pip install -e ".[dev]"
```

El flag `-e` instala el paquete en modo editable (cambios en el código se reflejan sin reinstalar). El extra `[dev]` incluye herramientas de prueba y linting (`pytest`, `ruff`, `mypy`).

### Iniciar el servidor

```bash
uvicorn app.main:app --reload --port 8000
```

| Flag | Descripción |
|---|---|
| `--reload` | Recarga automática al detectar cambios en el código (solo desarrollo) |
| `--port 8000` | Puerto de escucha (ajustar si hay conflicto) |

La API quedará disponible en:

- **Base URL**: `http://localhost:8000`
- **Documentación interactiva (Swagger)**: `http://localhost:8000/docs`
- **Documentación alternativa (ReDoc)**: `http://localhost:8000/redoc`
- **Health check**: `http://localhost:8000/health`

### Verificar conexiones al arrancar

El sistema expone tres endpoints de diagnóstico:

```
GET /api/v1/health          → Estado general de la API
GET /api/v1/health/db       → Conectividad con MongoDB
GET /api/v1/health/gemini   → Conectividad con Gemini API
```

### Ejecutar pruebas

```bash
# Todas las pruebas
pytest

# Con salida detallada
pytest -v

# Prueba de trazabilidad de contexto (Rol 1 + Rol 2, requiere API activa)
python scripts/test_context_roles_traceability.py
```

---

## 7. Instalación y Ejecución del Frontend

```bash
cd movie-graph-rag-frontend

npm install

npm run dev
```

La interfaz estará disponible en `http://localhost:3000`.

### Scripts disponibles

| Comando | Descripción |
|---|---|
| `npm run dev` | Servidor de desarrollo con hot-reload |
| `npm run build` | Compilación optimizada para producción |
| `npm run start` | Servir el build de producción |
| `npm run lint` | Revisión de estilo con ESLint |

---

## 8. Arquitectura del Sistema

El backend sigue una **arquitectura hexagonal** (Ports & Adapters) organizada en cuatro capas concéntricas:

```
┌─────────────────────────────────────────────────────────┐
│  API (FastAPI routers + Pydantic schemas)                │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Application (casos de uso)                       │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  Domain (entidades + puertos/interfaces)    │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
│  Adapters (MongoDB, Fuseki, Gemini, Groq)                │
└─────────────────────────────────────────────────────────┘
```

| Capa | Directorio | Responsabilidad |
|---|---|---|
| **Domain** | `app/domain/` | Entidades puras (`Movie`, `User`, `ContextSnapshot`) y contratos de repositorio (interfaces Python). Sin dependencias externas. |
| **Application** | `app/application/use_cases/` | Orquesta la lógica de negocio. Llama a los puertos definidos en Domain. Independiente de frameworks. |
| **Adapters** | `app/adapters/repositories/` | Implementaciones concretas de los puertos: `MongoUserRepository`, `FusekiGraphRepository`, `GeminiLLMAdapter`, etc. |
| **API** | `app/api/v1/` | Routers FastAPI. Valida HTTP, llama a casos de uso, serializa respuestas con Pydantic. |
| **Core** | `app/core/` | Configuración global (`settings`), seguridad JWT, middleware de trazabilidad (`X-Trace-ID`). |

---

## 9. Ontologías y Modelo de Conocimiento

El sistema utiliza **tres ontologías OWL 2 DL** que se consultan de forma cruzada mediante SPARQL:

### Ontología de Películas (`movie-ontology`)

Modela el dominio cinematográfico completo.

**Clases principales:**
- `Movie` → `FeatureFilm`, `Documentary`, `ShortFilm`, `AnimatedFilm`
- `Person` → `Director`, `Actor`, `Producer`, `Screenwriter`, `Cinematographer`, `Composer`
- `Genre` → `MainGenre`, `Subgenre`
- `NarrativeElement` → `Theme`, `Tone`, `PlotStructure`
- `Certification` → `G`, `PG`, `PG13`, `R`, `NC17`

**Propiedades clave:** `hasTitle`, `runtime`, `releaseDate`, `hasMainGenre`, `hasDirector`, `hasActor`, `hasAverageRating`, `hasTone`, `hasTheme`, `hasPlotSummary`

### Ontología de Contexto (`context-ontology`)

Modela el estado del usuario en el momento de cada interacción.

**Clases principales:**
- `ContextSnapshot` — nodo raíz con `snapshotID` único y `requestTimestamp`
- `EmotionalContext` — `moodDescription`, `desiredEnergyLevel`, intensidad
- `SocialContext` — `companionType` (alone / friends / family / partner), `hasChildren`, `groupSize`
- `RequirementContext` — `availableTimeMinutes`, géneros excluidos, restricciones

**Roles del snapshot:**
- **Rol 1 (efímero)**: se inyecta en Fuseki por la duración del request y se elimina al finalizar.
- **Rol 2 (persistente)**: se archiva en un grafo por usuario (`http://users/{id}/history`) para enriquecer recomendaciones futuras.

### Ontología Puente (`bridge-ontology`)

Conecta películas con snapshots de contexto mediante scores de compatibilidad.

| Propiedad | Rango | Descripción |
|---|---|---|
| `compatibilityScore` | [0, 1] | Score general de compatibilidad |
| `moodMatchScore` | [0, 1] | Coincidencia de estado de ánimo |
| `socialMatchScore` | [0, 1] | Adecuación para el tipo de compañía |
| `energyMatchScore` | [0, 1] | Coincidencia de nivel de energía |
| `timeMatchScore` | [0, 1] | Adecuación de duración vs tiempo disponible |

---

## 10. Pipeline de Recomendación

El endpoint `POST /api/v1/recommendation` ejecuta un pipeline de cinco etapas:

```
Query del usuario
      │
      ▼
┌─────────────────────────────────────────┐
│ 1. EXTRACCIÓN DE CONTEXTO (Gemini LLM)  │
│    Entrada: texto libre del usuario     │
│    Salida:  ContextSnapshot estructurado│
│    Tiempo:  ~2–4 s                      │
└─────────────────┬───────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│ 2. GENERACIÓN RDF + SPARQL (Gemini LLM) │
│    Inyecta snapshot efímero en Fuseki   │
│    Construye SPARQL cross-ontology      │
│    Estrategia progresiva:               │
│      strict → relaxed_runtime           │
│             → relaxed_genre → broad     │
│    Tiempo:  ~1–3 s                      │
└─────────────────┬───────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│ 3. EJECUCIÓN EN FUSEKI (HTTP SPARQL)    │
│    Retorna hasta 20 candidatos          │
│    Fallback a favoritos si Fuseki falla │
│    Tiempo:  ~0.5–2 s                    │
└─────────────────┬───────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│ 4. SCORING MULTI-CRITERIO               │
│    mood:       40 %                     │
│    social:     30 %                     │
│    logística:  20 % (tiempo, edad)      │
│    calidad:    10 % (rating)            │
│    Retorna top-5 ordenados              │
│    Tiempo:  < 0.1 s                     │
└─────────────────┬───────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│ 5. EXPLICACIÓN NARRATIVA (Gemini LLM)   │
│    Genera texto en lenguaje natural     │
│    Justifica cada recomendación         │
│    Tiempo:  ~1–3 s                      │
└─────────────────┬───────────────────────┘
                  ▼
      Respuesta al usuario (5 películas + explicación)
```

### Diagnóstico del pipeline

El endpoint `POST /api/v1/recommendation/debug` retorna la misma recomendación más un payload de diagnóstico:

```json
{
  "debugPayload": {
    "source": "fuseki_history | fallback",
    "fallbackUsed": false,
    "rdfGenerated": "...",
    "sparqlExecuted": "...",
    "errors": [],
    "timingsMs": {
      "contextExtraction": 2341,
      "rdfAndSparqlBuild": 1205,
      "fusekiQuery": 843,
      "scoring": 12,
      "llmExplanation": 1987,
      "historyWrite": 45,
      "total": 6433
    }
  }
}
```

---

## 11. Scripts de Utilidad

Los scripts se encuentran en `movie-graph-rag-backend-fastapi/scripts/`. Todos requieren el entorno virtual activo y la API corriendo en `http://localhost:8000`.

| Script | Descripción |
|---|---|
| `test_context_roles_traceability.py` | Prueba end-to-end del ciclo completo de contexto (Rol 1 + Rol 2). Registra usuario temporal, ejecuta recomendación, valida inyección/limpieza del snapshot efímero y archivado histórico. Retorna código `0` si todo pasa. |
| `compute_network_metrics.py` | Calcula métricas de redes complejas sobre el grafo de películas: centralidades (degree, betweenness, PageRank), comunidades Louvain, coeficiente de clustering, modularidad. Los resultados se persisten en MongoDB. |
| `patch_imdb_ratings.py` | Actualiza los ratings de películas en Fuseki con datos actualizados de IMDB. |
| `translate_plot_summaries.py` | Traduce sinopsis de películas al español usando la API de traducción configurada. |
| `smoke_test_phase*.py` | Pruebas de humo por fase de implementación (fases 4 a 11). Verifican que los endpoints de cada fase responden correctamente. |

---

## 12. Referencia de Endpoints

### Autenticación

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Registrar nuevo usuario | No |
| `POST` | `/api/v1/auth/login` | Login → retorna `access_token` JWT | No |
| `POST` | `/api/v1/auth/token` | Login vía OAuth2 form (Swagger) | No |
| `GET` | `/api/v1/auth/me` | Perfil del usuario autenticado | Sí |

### Recomendación

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| `POST` | `/api/v1/recommendation` | Recomendación por consulta en texto natural | Sí |
| `GET` | `/api/v1/recommendation?query=...` | Recomendación vía query param | Sí |
| `POST` | `/api/v1/recommendation/debug` | Ídem con diagnóstico completo del pipeline | Sí |
| `GET` | `/api/v1/recommendation/activity` | Recomendación basada en contexto temporal y perfil | Sí |

### Películas

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| `GET` | `/api/v1/movies/examples?limit=3` | Películas de ejemplo para cold-start | No |
| `GET` | `/api/v1/movies/autocomplete?q=...&limit=8` | Autocompletado de título | No |
| `GET` | `/api/v1/movies/search` | Búsqueda con filtros (título, director, género, año) | No |
| `GET` | `/api/v1/movies/connections` | Camino más corto entre dos películas en el grafo | Sí |
| `GET` | `/api/v1/movies/{title}/cluster` | Películas en la misma comunidad | Sí |

### Usuarios y Favoritos

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| `GET` | `/api/v1/users/me/favorites` | Listar favoritos del usuario | Sí |
| `POST` | `/api/v1/users/me/favorites` | Agregar película a favoritos | Sí |
| `DELETE` | `/api/v1/users/me/favorites` | Eliminar película de favoritos | Sí |
| `GET` | `/api/v1/users/me/topology` | Perfil topológico del usuario | Sí |

### Historial

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| `POST` | `/api/v1/history/me` | Registrar consulta en el historial | Sí |
| `GET` | `/api/v1/history/me?limit=10` | Historial del usuario actual | Sí |
| `GET` | `/api/v1/history/{id}` | Detalle de una consulta histórica | Sí |

### Grafo y Topología

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| `GET` | `/api/v1/graph` | Estadísticas globales del grafo | Sí |
| `GET` | `/api/v1/clusters` | Listado de comunidades detectadas | Sí |

### Administración

| Método | Ruta | Descripción | Auth (rol) |
|---|---|---|---|
| `GET` | `/api/v1/admin/whoami` | Verificar identidad de administrador | Admin |
| `GET` | `/api/v1/admin/metrics/recommendation` | Métricas del sistema de recomendación | Admin |

### Health

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Estado general |
| `GET` | `/api/v1/health` | Estado de la API |
| `GET` | `/api/v1/health/db` | Conectividad MongoDB |
| `GET` | `/api/v1/health/gemini` | Conectividad Gemini API |

---

*Versión del manual: 1.0 · Mayo 2026*
*Sistema: MOVIQ v1.0 · Trabajo de Grado · Universidad del Valle*
