# movie-graph-rag-backend-fastapi

Starter project para migrar `movie-graph-rag-backend` (NestJS) a FastAPI.

## Arranque rápido (Windows PowerShell)

```powershell
cd movie-graph-rag-backend-fastapi.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

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
- Opcional: `ADMIN_EMAILS` (lista separada por comas) para asignar rol `admin` al registrar
- Opcional: `FUSEKI_TIMEOUT_SECONDS` y `FUSEKI_MAX_RETRIES` para ajustar estabilidad/latencia de consultas SPARQL

## Recommendation v1.5

- `POST /api/v1/recommendation` ahora genera `rdfGenerated` contextual y ejecuta `sparqlQuery` real sobre Fuseki.
- El retrieval usa estrategia progresiva: `strict` (género+tiempo) → `relaxed_runtime` → `relaxed_genre` → `broad`.
- Si Fuseki no responde o no retorna resultados, hace fallback a señales de favoritos para mantener disponibilidad.
- Las escrituras de historial/métricas son resilientes: si fallan, la recomendación igual se retorna y el error queda en `debug.errors`.
- `POST /api/v1/recommendation/debug` devuelve la misma recomendación + diagnóstico (`source`, `fallbackUsed`, `errors`) y tiempos por etapa (`contextExtraction`, `rdfAndSparqlBuild`, `fusekiQuery`, `scoring`, `llmExplanation`, `historyWrite`, `total`).

## Pruebas de contexto semántico (Rol 1 + Rol 2)

Esta sección valida el ciclo completo de contexto en Fuseki:

- **Rol 1 (snapshot efímero por sesión):** inyectar snapshot temporal por request y luego limpiarlo.
- **Rol 2 (perfil histórico persistente):** archivar el snapshot en un grafo histórico por usuario y usarlo en actividad.

### Prerrequisitos

- API levantada en `http://127.0.0.1:8000`
- Fuseki levantado con dataset `Cine`
- Variables `.env` de Fuseki configuradas (`FUSEKI_URL`, `FUSEKI_DATASET`, `FUSEKI_USER`, `FUSEKI_PASSWORD`)

### 1) Generar snapshot (Rol 1) y archivarlo (Rol 2)

1. Registrar usuario (`POST /api/v1/auth/register`) y guardar `access_token`.
2. Ejecutar:
   - `POST /api/v1/recommendation/debug` con query contextual (por ejemplo: "Quiero algo relajado para ver en familia").
3. Verificar en respuesta debug:
   - `contextGraphInjected = true`

### 2) Verificar historial persistente del usuario (Rol 2)

Consultar en Fuseki (pestaña Query del dataset `Cine`):

```sparql
PREFIX context: <http://www.semanticweb.org/movierecommendation/ontologies/2025/context-ontology#>

SELECT ?snapshotID ?requestTimestamp ?moodDescription ?companionType ?desiredEnergyLevel
WHERE {
  GRAPH <http://users/USER_ID/history> {
    ?snapshot a context:ContextSnapshot ;
              context:snapshotID ?snapshotID .
    OPTIONAL { ?snapshot context:requestTimestamp ?requestTimestamp }
    OPTIONAL {
      ?snapshot context:feelsMood ?mood .
      ?mood context:moodDescription ?moodDescription .
      OPTIONAL { ?mood context:desiredEnergyLevel ?desiredEnergyLevel }
    }
    OPTIONAL {
      ?snapshot context:withCompanion ?social .
      ?social context:companionType ?companionType .
    }
  }
}
ORDER BY DESC(?requestTimestamp)
LIMIT 20
```

Reemplazar `USER_ID` por el id real de Mongo del usuario autenticado.

### 3) Verificar recomendación por actividad usando perfil semántico

Llamar `GET /api/v1/recommendation/activity` con el mismo token y revisar:

- `debugPayload.profileSource` (`fuseki_history` o `cold_start`)
- `debugPayload.dominantMood`
- `debugPayload.dominantCompanion`

### 4) Validar limpieza del grafo efímero de sesión (Rol 1)

```sparql
SELECT ?g
WHERE {
  GRAPH ?g { ?s ?p ?o }
  FILTER(STRSTARTS(STR(?g), "http://session/"))
}
LIMIT 20
```

No debería permanecer el snapshot de la request ya finalizada (se elimina tras intento de archivado).

### Script automatizado de trazabilidad (Rol 1 + Rol 2)

Se puede ejecutar un test end-to-end que:

- registra un usuario temporal,
- ejecuta recomendación debug,
- valida inyección y limpieza de sesión,
- valida archivado en historial por usuario,
- ejecuta recommendation activity y revisa `debugPayload`.

Comando:

```bash
python scripts/test_context_roles_traceability.py
```

El script imprime reporte `PASS/FAIL` por chequeo y retorna código `0` si todo pasa.

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
- `GET /api/v1/auth/me` (incluye `role`)
- `GET /api/v1/admin/whoami` (requiere rol `admin`)
- `GET /api/v1/admin/metrics/recommendation?recentLimit=20&summaryLimit=200` (requiere rol `admin`)
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
