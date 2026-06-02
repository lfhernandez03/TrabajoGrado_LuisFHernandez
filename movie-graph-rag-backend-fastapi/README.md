# movie-graph-rag-backend-fastapi

API REST para el sistema de recomendación cinematográfica semántica **MOVIQ**. Construida con FastAPI y arquitectura hexagonal, combina un grafo de conocimiento OWL/RDF almacenado en Apache Fuseki con MongoDB para datos de usuario, y modelos LLM (Gemini / Groq) para generar explicaciones en lenguaje natural.

## Tecnologías

| Capa | Tecnología |
|---|---|
| Framework | FastAPI 0.115+ |
| Base de datos | MongoDB (usuarios, historial) |
| Triple store | Apache Fuseki (SPARQL) |
| LLM | Google Gemini Flash / Groq |
| Grafo | NetworkX, python-louvain |
| Ontologías | rdflib 7+ |
| Auth | JWT (python-jose + passlib) |
| Python | 3.11+ |

## Arquitectura hexagonal

```
app/
├── domain/          # Entidades y puertos (contratos)
├── application/     # Casos de uso (orquestación)
├── adapters/        # Implementaciones concretas (MongoDB, Fuseki)
├── api/             # Routers, schemas HTTP, dependencies
│   └── v1/
└── core/            # Configuración, seguridad, logging, resiliencia
```

## Requisitos previos

- Python 3.11+
- MongoDB accesible (variable `MONGO_URI`)
- Apache Fuseki corriendo con dataset `Cine`
- (Opcional) clave de API de Gemini o Groq para explicaciones LLM

## Instalación

```bash
cd movie-graph-rag-backend-fastapi
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -e .[dev]
```

## Variables de entorno

Crear un archivo `.env` en la raíz del proyecto:

```env
# MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=moviq

# Fuseki / SPARQL
FUSEKI_URL=http://localhost:3030
FUSEKI_DATASET=Cine
FUSEKI_USER=admin
FUSEKI_PASSWORD=your_password
FUSEKI_TIMEOUT_SECONDS=10
FUSEKI_MAX_RETRIES=3

# JWT
SECRET_KEY=your_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=60

# LLM (opcional)
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-2.0-flash

# Administradores (correos separados por comas)
ADMIN_EMAILS=admin@example.com
```

## Ejecución

```bash
uvicorn app.main:app --reload --port 8000
```

Documentación interactiva disponible en `http://localhost:8000/docs`.

## Docker (Render)

```bash
docker build -f Dockerfile.render -t moviq-backend .
docker run -p 8000:8000 --env-file .env moviq-backend
```

## Endpoints principales

### Salud

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Salud general |
| GET | `/api/v1/health/db` | Conectividad MongoDB |
| GET | `/api/v1/health/gemini` | Conectividad LLM |

### Autenticación

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/auth/register` | Registro de usuario |
| POST | `/api/v1/auth/login` | Login (JSON) |
| POST | `/api/v1/auth/token` | Login OAuth2 (Swagger) |
| GET | `/api/v1/auth/me` | Perfil del usuario autenticado |

### Recomendación

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/recommendation` | Recomendación semántica por texto |
| GET | `/api/v1/recommendation` | Recomendación vía query param |
| POST | `/api/v1/recommendation/debug` | Recomendación + diagnóstico completo |
| GET | `/api/v1/recommendation/activity` | Recomendación basada en historial del usuario |

### Películas

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/movies/search` | Búsqueda con filtros |
| GET | `/api/v1/movies/autocomplete` | Autocompletado de títulos |
| GET | `/api/v1/movies/examples` | Películas de ejemplo |
| GET | `/api/v1/movies/connections` | Explorador de conexiones en el grafo |
| GET | `/api/v1/movies/centrality` | Películas por centralidad de grafo |
| GET | `/api/v1/movies/neighborhood` | Vecindad de una película en el grafo |
| GET | `/api/v1/movies/cluster` | Películas de un cluster temático |

### Usuario

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/users/me/favorites` | Favoritos del usuario |
| POST | `/api/v1/users/me/favorites` | Agregar a favoritos |
| DELETE | `/api/v1/users/me/favorites` | Eliminar de favoritos |
| GET | `/api/v1/users/me/topology` | Perfil topológico del usuario |

### Historial

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/history/me` | Historial de recomendaciones |
| POST | `/api/v1/history/me` | Registrar entrada de historial |
| GET | `/api/v1/history/{id}` | Entrada específica del historial |

### Administración (rol `admin`)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/admin/whoami` | Verificar rol admin |
| GET | `/api/v1/admin/metrics/recommendation` | Métricas de uso del sistema |

## Flujo de recomendación

```
POST /recommendation  →  Extracción de contexto (LLM)
                      →  Construcción RDF contextual
                      →  Generación SPARQL (ontology_query_builder)
                      →  Consulta Fuseki (estrategia progresiva)
                            strict → relaxed_runtime → relaxed_genre → broad
                      →  Scoring (compatibilityScore + serendipityScore)
                      →  Explicación narrativa (LLM)
                      →  Archivado de contexto en historial (Fuseki + MongoDB)
```

Si Fuseki no responde, el sistema hace fallback a señales de favoritos del usuario para mantener disponibilidad.

## Contexto semántico (Rol 1 y Rol 2)

El sistema mantiene dos niveles de contexto en Fuseki:

- **Rol 1 – Snapshot efímero**: Se inyecta por request en un grafo temporal (`http://session/{id}`) y se elimina tras archivar.
- **Rol 2 – Perfil histórico**: El snapshot se archiva en un grafo persistente por usuario (`http://users/{userId}/history`) y se usa para recomendaciones de actividad.

Para validar el ciclo completo:

```bash
python scripts/test_context_roles_traceability.py
```

## Tests

```bash
pytest -q
```

Los tests cubren estrategia de consulta, scoring adaptativo, endpoints de recomendación y scorer con prompt.

## Scripts auxiliares

| Script | Descripción |
|---|---|
| `scripts/compute_network_metrics.py` | Calcula métricas de red del grafo (centralidad, clusters) |
| `scripts/patch_imdb_ratings.py` | Actualiza ratings de IMDb en Fuseki |
| `scripts/translate_plot_summaries.py` | Traduce sinopsis de películas |
| `scripts/smoke_test_phase*.py` | Pruebas de humo por fase de desarrollo |
