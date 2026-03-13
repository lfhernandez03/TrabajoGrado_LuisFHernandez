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
- `adapters`: implementaciones concretas (repo in-memory inicial)
- `api`: controllers/routers + schemas HTTP

## Requisitos

- Python 3.11+

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

## Endpoints iniciales

- `GET /health`
- `GET /api/v1/health`

## Siguiente fase de migración

1. Migrar `users` + `favorites`
2. Migrar `auth` JWT
3. Migrar `history`
4. Migrar `graph` y `recommendation`
5. Migrar `llm` y prompts
