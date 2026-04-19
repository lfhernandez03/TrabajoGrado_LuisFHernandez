# Contexto para Claude Code — Mejora del Chat con Graph RAG Real

## Problema central

El chat actualmente usa el LLM (Groq) **solo como parser NLU** al inicio del pipeline y para generar la explicación final. No está "entrenado" con el contexto del usuario: si alguien escribe "Hola", el sistema extrae un `UserContext` vacío o con valores inventados y devuelve recomendaciones sin base real.

**Lo que debe pasar en cambio:**

1. El LLM debe recibir como contexto: favoritos del usuario, historial de búsquedas, perfil topológico y `accumulated_context` de la sesión conversacional actual.
2. Las relaciones de la ontología (comunidades Louvain, betweenness, PageRank, aristas director/género) deben explotarse **en el momento del query**, no solo como propiedades pre-asignadas — eso es lo que convierte el sistema en verdadero Graph RAG.
3. Cuando el query es ambiguo (ej. "Hola", "algo bueno", "no sé qué ver"), el sistema debe **inferir intención desde el perfil** en lugar de inventar contexto.

---

## Arquitectura actual (qué existe)

### Stack
- **Backend:** FastAPI + Python 3.12
- **Grafo de conocimiento:** Apache Jena Fuseki (SPARQL 1.1) — ontologías OWL 2 en Turtle
- **LLM:** Actualmente Groq (antes era Gemini 1.5 Flash vía `google-genai`) — solo NLU + explicación
- **BD:** MongoDB — usuarios, historial, favoritos
- **Frontend:** Next.js

### Pipeline actual del `/chat`

```
POST /api/v1/recommendation/chat
  ↓
ChatUseCase.execute(session_id, messages, user_id)
  ↓
1. LLM.extract_query_context(last_message)   ← solo ve el último mensaje, sin contexto de usuario
   → UserContext (mood, companion, genres, etc.)
  ↓
2. session_store.get_or_create(session_id)
   → ConversationSession con accumulated_context
  ↓
3. merge_contexts(accumulated, new_ctx)
  ↓
4. profile_service.get(user_id) → UserProfile  ← se obtiene pero NO se inyecta al LLM
  ↓
5. build_strategy(ctx, profile) → SPARQL attempts
  ↓
6. GraphExecutor.run_strategy() → películas desde Fuseki
  ↓
7. score_and_select(rows, ctx, profile) → [Movie × 5]
  ↓
8. LLM.generate_recommendation_explanation()  ← genera explicación sin ver favoritos reales
  ↓
9. archive_context(user_id, ctx) → Fuseki history
```

### Lo que existe y puede aprovecharse

**En Fuseki (ya calculado por `scripts/compute_network_metrics.py`):**
```turtle
<movieURI>
    movie:degreeCentrality        "0.0124"^^xsd:float ;
    movie:betweennessCentrality   "0.0531"^^xsd:float ;
    movie:pageRank                "0.00038"^^xsd:float ;
    movie:clusteringCoefficient   "0.2100"^^xsd:float ;
    movie:belongsToCluster        "14"^^xsd:string ;
    movie:clusterLabel            "Sci-Fi Épico Contemplativo"^^xsd:string .
```

**En MongoDB:**
- `user_favorites` — películas marcadas como favoritas con `addedAt`
- `query_history` — historial de búsquedas anteriores

**En ProfileService (`app/core/profile_service.py`):**
- `get(user_id) → UserProfile` con `genre_weights`, `dominant_mood`, `snapshot_count`, caché TTL 3 min
- `get_topological_profile(user_id) → TopologicalProfileResponse` con `explorationIndex`, `userType` (especialista/equilibrado/explorador), `dominantClusters`, `unexploredClusters`

**Modelo `UserProfile`:**
```python
@dataclass
class UserProfile:
    user_id: str
    genre_weights: dict[str, float]    # {"Comedy": 0.8, "Drama": 0.4, ...}
    dominant_mood: str | None
    dominant_companion: str | None
    dominant_time_of_day: str | None
    children_age_hint: str | None
    snapshot_count: int
    is_cold_start: bool
```

**Modelo `ConversationSession`:**
```python
@dataclass
class ConversationSession:
    session_id: str
    user_id: str
    turns: list[ConversationTurn]
    accumulated_context: UserContext | None
```

---

## Mejoras requeridas

### Mejora 1 — NLU consciente del perfil (query enriquecido)

**Archivo:** `app/adapters/llm/groq_recommendation_llm_adapter.py` (o el adapter LLM activo)

**Problema:** `extract_query_context()` y `extract_user_context()` solo reciben el texto del mensaje. No saben quién es el usuario.

**Solución:** Crear un nuevo método `extract_user_context_with_profile()` que construya un prompt enriquecido:

```python
def extract_user_context_with_profile(
    self,
    query: str,
    profile: UserProfile,
    favorites_sample: list[str],          # títulos de favoritos recientes (max 10)
    recent_queries: list[str],            # últimas 5 búsquedas
    topological_type: str | None,         # "especialista" | "equilibrado" | "explorador"
    dominant_clusters: list[str],         # etiquetas de clusters dominantes
    accumulated_context: UserContext | None,
    now: datetime | None = None,
) -> UserContext:
```

El prompt debe incluir una sección de contexto de usuario **antes** de la instrucción NLU:

```
CONTEXTO DEL USUARIO:
- Géneros favoritos: Comedy (0.8), Drama (0.5), Thriller (0.3)
- Estado de ánimo predominante: relaxed
- Perfil de exploración: especialista (se concentra en pocos géneros)
- Comunidades temáticas que frecuenta: "Comedia Contemporánea", "Drama Familiar"
- Favoritos recientes: "The Truman Show", "About Time", "500 Days of Summer"
- Búsquedas recientes: "algo romántico", "comedia ligera sin violencia"
- Contexto acumulado de esta sesión: mood=relaxed, genres=["Comedy"]

QUERY ACTUAL: "Hola"

INSTRUCCIÓN: Si el query es ambiguo o un saludo, usa el contexto del usuario para inferir
una intención razonable en lugar de devolver campos vacíos. Mapea a los valores del
vocabulario controlado.
```

**Regla crítica de manejo de queries ambiguos:**
- Si `confidence < 0.6` Y `profile.is_cold_start == False` → reutilizar `dominant_mood` y top géneros del perfil como fallback, con `confidence = 0.65`
- Si `confidence < 0.6` Y `profile.is_cold_start == True` → estrategia `broad` directamente, sin inventar mood

### Mejora 2 — Graph RAG real: relaciones ontológicas en el query

**Problema:** Las relaciones del grafo (comunidades, centralidad, aristas) están pre-calculadas como propiedades de películas, pero la selección de candidatos via SPARQL no explota las **relaciones estructurales** del grafo en tiempo de query.

**Qué significa Graph RAG real aquí:**

En lugar de filtrar por `bridge:compatibleMood`, también filtrar/priorizar usando la topología:

#### 2a — Estrategia por cluster del perfil del usuario

Nuevo intento en `build_strategy()` (`app/core/query_strategy.py`):

```python
# Estrategia "community_profile": películas de los clusters dominantes del usuario
# que también son compatibles con el mood actual
SPARQL:
SELECT ?movie ?title ?genreName ?rating ?compatibilityScore ...
WHERE {
  ?movie movie:belongsToCluster ?cluster .
  FILTER(?cluster IN ("14", "7", "3"))   # clusters del perfil del usuario
  ?movie bridge:compatibleMood ?moodEs .
  FILTER(?moodEs = "relajado")
  ...
}
ORDER BY DESC(?pageRank) DESC(?compatibilityScore)
```

Esta estrategia debe insertarse en el orden de intentos entre `ontology_mood_only` y `genre_filter`:

```
1. ontology_full
2. ontology_mood_companion
3. ontology_mood_only
4. community_profile          ← NUEVO: clusters del usuario + mood
5. community_adjacent         ← NUEVO: clusters adyacentes no explorados + mood
6. ontology_companion_only
7. genre_filter
8. broad
```

#### 2b — Estrategia de exploración (clusters adyacentes no visitados)

Cuando `userType == "especialista"` y `unexploredClusters` no está vacío, añadir candidatos de esos clusters con un boost de serendipity. Esta es la forma en que el grafo "recomienda salir de la burbuja".

#### 2c — Scoring con distancia en el grafo

En `scorer.py` (`app/core/scorer.py`), enriquecer `_compute_score()` con una componente de "relevancia topológica al perfil":

```python
# graph_affinity: qué tan cerca topológicamente está esta película del perfil del usuario
# = 1.0 si su cluster es un cluster dominante del usuario
# = 0.5 si es un cluster adyacente
# = 0.0 si no tiene relación topológica
graph_affinity = _compute_graph_affinity(movie, profile_clusters, adjacent_clusters)

# Nueva fórmula con datos semánticos + topología:
score = 0.35*rating + 0.25*semantic + 0.20*graph_affinity + 0.10*freshness + 0.10*novelty
```

### Mejora 3 — Explicación informada por el perfil real

**Archivo:** método `generate_recommendation_explanation()` en el adapter LLM

**Problema:** La explicación no sabe qué favoritos tiene el usuario ni por qué estas películas específicas son relevantes para él.

**Solución:** Pasar al método de explicación:
- Títulos de favoritos del usuario (muestra de 5)
- Clusters dominantes del usuario
- La estrategia SPARQL usada (`strategy_used`)
- Si se usó exploración de clusters adyacentes

Prompt diferenciado:
```
Si strategy_used == "community_profile": menciona que las recomendaciones son del espacio
  temático que el usuario ya ha explorado.
Si strategy_used == "community_adjacent": menciona que se está sugiriendo explorar nuevo
  territorio cinematográfico afín a sus gustos.
Si profile.is_cold_start: no mencionar historial, enfocarse en el contexto del momento.
```

### Mejora 4 — `ChatUseCase` orquesta el contexto completo

**Archivo:** `app/application/use_cases/recommendation/chat_use_case.py`

Cambios al método `execute()`:

```python
async def execute(self, session_id, messages, user_id):
    last_query = messages[-1].content

    # 1. Obtener perfil completo ANTES del NLU
    profile = await self.profile_service.get(user_id)

    # 2. Obtener muestra de favoritos y búsquedas recientes
    favorites_sample = await self._get_favorites_titles(user_id, limit=10)
    recent_queries = await self._get_recent_queries(user_id, limit=5)

    # 3. Obtener perfil topológico (clusters dominantes)
    topo = await self.profile_service.get_topological_profile(user_id)
    dominant_cluster_labels = [c.label for c in topo.dominantClusters[:3]]
    adjacent_cluster_ids = [c.clusterId for c in topo.unexploredClusters[:5]]

    # 4. NLU con contexto enriquecido
    session = self.session_store.get_or_create(session_id)
    new_ctx = self.llm_client.extract_user_context_with_profile(
        query=last_query,
        profile=profile,
        favorites_sample=favorites_sample,
        recent_queries=recent_queries,
        topological_type=topo.userType,
        dominant_clusters=dominant_cluster_labels,
        accumulated_context=session.accumulated_context,
    )

    # 5. Merge con contexto acumulado de la sesión
    merged_ctx = merge_contexts(session.accumulated_context, new_ctx)

    # 6. Build strategy con conocimiento de clusters del usuario
    attempts = build_strategy(
        merged_ctx,
        profile,
        dominant_cluster_ids=[c.clusterId for c in topo.dominantClusters[:3]],
        adjacent_cluster_ids=adjacent_cluster_ids,
    )

    # ... resto del pipeline sin cambios ...
```

**Nuevos métodos privados a añadir en `ChatUseCase`:**

```python
async def _get_favorites_titles(self, user_id: str, limit: int = 10) -> list[str]:
    """Lee favoritos desde MongoDB vía user_favorites_repository."""

async def _get_recent_queries(self, user_id: str, limit: int = 5) -> list[str]:
    """Lee últimas búsquedas desde query_history_repository."""
```

### Mejora 5 — `build_strategy` acepta clusters del perfil

**Archivo:** `app/core/query_strategy.py`

Firma actualizada:

```python
def build_strategy(
    ctx: UserContext,
    profile: UserProfile,
    dominant_cluster_ids: list[str] | None = None,   # NUEVO
    adjacent_cluster_ids: list[str] | None = None,   # NUEVO
) -> list[tuple[str, str]]:
```

Las estrategias `community_profile` y `community_adjacent` solo se añaden si los `cluster_ids` no están vacíos. Son no-ops si la Fase 6 no se ha ejecutado (graceful degradation: si la query no retorna resultados, el fallback progresivo la salta).

---

## Archivos a modificar (resumen)

| Archivo | Tipo de cambio |
|---|---|
| `app/adapters/llm/groq_recommendation_llm_adapter.py` | Nuevo método `extract_user_context_with_profile()`, prompt enriquecido en `generate_recommendation_explanation()` |
| `app/domain/ports/recommendation_llm_client.py` | Añadir `extract_user_context_with_profile()` al Protocol |
| `app/core/query_strategy.py` | Nuevas estrategias `community_profile` y `community_adjacent`, firma actualizada |
| `app/core/scorer.py` | Nueva componente `graph_affinity` en `_compute_score()` |
| `app/application/use_cases/recommendation/chat_use_case.py` | Orquestar perfil + favoritos + topología antes del NLU |
| `app/application/use_cases/recommendation/recommendation_use_case.py` | Mismo patrón que chat_use_case para el endpoint `/recommend` |

---

## Invariantes que NO deben romperse

- `time_of_day` siempre del reloj del servidor, **nunca** del LLM
- Todos los calls a Fuseki/Mongo/LLM en `try/except` con fallback seguro
- Si el LLM falla → keyword extraction fallback con `confidence=0.5`
- Si los clusters no están en Fuseki → la estrategia community se omite silenciosamente
- `UserContext.raw_query` siempre debe contener el texto original del usuario
- No añadir dependencias de pip nuevas sin necesidad estricta
- Dataclasses en `domain/`, Pydantic solo en `api/schemas/`

---

## Comportamiento esperado tras los cambios

| Escenario | Antes | Después |
|---|---|---|
| Usuario escribe "Hola" | Contexto vacío → recomendaciones aleatorias | Inferencia desde perfil → géneros dominantes del usuario, mood histórico |
| Usuario escribe "algo de terror" (usuario que solo ve comedias) | Devuelve terror directo | Devuelve terror pero con nota en la explicación de que es inusual para su perfil, ofrece alternativas del cluster adyacente |
| Usuario con perfil "especialista" | Sin diferenciación | Estrategia `community_profile` primero, resultados de sus clusters habituales |
| Usuario con perfil "explorador" | Sin diferenciación | Candidatos de `community_adjacent` mezclados para mantener diversidad |
| Explicación final | Genérica | Menciona favoritos concretos, comunidades temáticas, razón topológica de la selección |

---

## Notas de implementación

- El `ProfileService.get_topological_profile()` ya existe en `app/core/profile_service.py` — no hay que crearlo
- El repositorio de favoritos es `MongoUserFavoritesRepository` en `app/adapters/repositories/mongo_user_favorites_repository.py`
- El repositorio de historial es `MongoQueryHistoryRepository` en `app/adapters/repositories/mongo_query_history_repository.py`
- La DI está en `app/api/di/movies_di.py` — el `ChatUseCase` ya recibe `llm_client` y `profile_service`; hay que añadir los repositorios de favoritos e historial
- El LLM actual usa Groq pero la interfaz es la misma que el `GeminiAdapter` anterior — el Port `RecommendationLlmClientPort` es lo que importa, no el proveedor concreto
