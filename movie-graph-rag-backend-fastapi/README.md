# movie-graph-rag-backend-fastapi

Starter project para migrar `movie-graph-rag-backend` (NestJS) a FastAPI.

## Objetivo inicial

- Levantar una API FastAPI mínima y estable
- Definir estructura tipo hexagonal para migración incremental
- Preparar base para módulos: auth, users, history, recommendation, llm, graph

## Estructura

```txt
app/
  api/
    v1/
      endpoints/
    schemas/
    dependencies.py
  core/
  domain/
    entities/
    ports/
  application/
    use_cases/
  adapters/
    repositories/
tests/
```

## Arquitectura Hexagonal aplicada

- `domain`: entidades y contratos (puertos)
- `application`: casos de uso (orquesta reglas)
- `adapters`: implementaciones concretas (repositorio MongoDB)
- `api`: controllers/routers + schemas HTTP

## Requisitos

- Python 3.11+
- MongoDB accesible por `MONGO_URI`
- Opcional: `GROQ_API_KEY` (y `GROQ_MODEL`) para generar explicaciones narrativas con LLM

## Recommendation v1.5

- `POST /api/v1/recommendation` ahora genera `rdfGenerated` contextual y ejecuta `sparqlQuery` real sobre Fuseki.
- Si Fuseki no responde o no retorna resultados, hace fallback a señales de favoritos para mantener disponibilidad.
- `POST /api/v1/recommendation/debug` devuelve la misma recomendación + diagnóstico (`source`, `fallbackUsed`, `errors`) y tiempos por etapa (`contextExtraction`, `rdfAndSparqlBuild`, `fusekiQuery`, `scoring`, `llmExplanation`, `historyWrite`, `total`).

## Instalación

```bash
cd movie-graph-rag-backend-fastapi
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -e .[dev]
```

## Ejecución

```bash
uvicorn app.main:app --reload --port 8000
```

La API abre conexión a MongoDB al iniciar y la cierra al apagar.

## Endpoints iniciales

- `GET /health`
- `GET /api/v1/health`
- `GET /api/v1/health/db`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/token` (OAuth2 form login para Swagger Authorize)
- `GET /api/v1/auth/me`
- `GET /api/v1/users/me/favorites`
- `POST /api/v1/users/me/favorites`
- `DELETE /api/v1/users/me/favorites`
- `POST /api/v1/history/me`
- `GET /api/v1/history/me?limit=10`
- `GET /api/v1/history/{id}`
- `GET /api/v1/recommendation?query=...`
- `POST /api/v1/recommendation`
- `POST /api/v1/recommendation/debug`
- `GET /api/v1/movies/examples?limit=3`
- `GET /api/v1/movies/autocomplete?q=...&limit=8`
- `GET /api/v1/movies/search?...`
- `GET /api/v1/movies/connections?from=...&to=...&maxDepth=3`

## Siguiente fase de migración

1. Migrar `users` + `favorites`
2. Migrar `auth` JWT
3. Migrar `history`
4. Migrar `graph` y `recommendation`
5. Migrar `llm` y prompts
