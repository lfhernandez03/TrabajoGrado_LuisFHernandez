# Arquitectura del sistema — Registro de fases de implementación

Sistema de recomendación de películas basado en ontologías OWL y GraphRAG.
Trabajo de grado — Universidad del Valle, Escuela de Ingeniería de Sistemas y Computación.

---

## Tabla de estado

| Fase | Descripción | Estado |
|------|-------------|--------|
| 1 | Modelos de dominio | ✅ Completo |
| 1.5 | Bridge data v2 | 🔄 Generado — pendiente de recargar en Fuseki |
| 2 | Core components: estrategia, scorer, perfil, explorador | ✅ Completo |
| 2.5 | Flujo conversacional y endpoint `/chat` | ✅ Completo |
| 3 | `RecommendationUseCase` limpio con nuevos componentes | ✅ Completo |
| 4 | Endpoints del explorador de conexiones | ✅ Completo |
| 5 | Métricas: ILD, precisión semántica, umbral cold start | ✅ Completo |
| 6 | Pipeline NetworkX offline: centralidades + comunidades en Fuseki | ✅ Completo — requiere ejecutar `scripts/compute_network_metrics.py` contra Fuseki |
| 7 | Graph Diversity Score basado en distancia BFS | ✅ Completo |
| 8 | Dashboard topológico: endpoint REST + frontend Next.js | ✅ Completo — 21/21 smoke tests PASS |
| 9 | Recomendacion por comunidad: GET /movies/{title}/cluster + GET /clusters | ✅ Completo — 30/30 smoke tests PASS |

---

## Fase 1 — Modelos de dominio

**Archivos:** `app/domain/entities/recommendation_models.py`, `app/domain/ports/graph_port.py`

### Qué se construyó

Los tipos de datos centrales del sistema de dominio. Son `@dataclass` de Python (no Pydantic) porque viven en la capa de dominio y no deben depender de ningún framework.

### Modelos principales

#### `UserContext`
Representa lo que el usuario quiere en una consulta concreta.

```python
@dataclass
class UserContext:
    mood: str | None           # "relaxed", "happy", "sad"… (inglés, viene del LLM)
    companion: str | None      # "alone", "friends", "family", "partner"
    has_children: bool         # True si hay niños en la compañía
    energy: str | None         # "low", "medium", "high"
    genres: list[str]          # ["Comedy", "Drama"]
    runtime_max: int | None    # minutos máximos de duración
    exclusions: list[str]      # géneros o títulos a excluir
    confidence: float          # 0.9 si vino del LLM, 0.5 si fue keyword fallback
    time_of_day: str | None    # "morning/afternoon/evening/night" — del reloj del servidor, NUNCA del LLM
    children_age_hint: str | None  # "young" (<12), "teen" (12-17), "adult" (18+)
    session_id: str | None     # identificador de sesión conversacional
    raw_query: str             # texto original del usuario
```

> **Decisión de diseño:** `time_of_day` se inyecta desde el reloj del servidor en el momento del request, nunca se le pide al LLM que lo infiera. Esto garantiza consistencia temporal y elimina alucinaciones de horario.

#### `UserProfile`
Perfil persistente del usuario, construido desde el historial y los favoritos con *decay* temporal.

```python
@dataclass
class UserProfile:
    user_id: str
    genre_weights: dict[str, float]    # {"Comedy": 0.8, "Drama": 0.4, ...}
    dominant_mood: str | None          # mood más frecuente en el historial
    dominant_companion: str | None     # compañía más frecuente
    dominant_time_of_day: str | None   # horario predominante
    children_age_hint: str | None      # edad de hijos, se conserva entre sesiones
    snapshot_count: int                # cuántos snapshots hay en Fuseki
    is_cold_start: bool                # True si snapshot_count < 3

    @classmethod
    def cold_start(cls, user_id: str) -> UserProfile: ...
```

#### `Movie`
Candidato de película con los metadatos del grafo y los scores del bridge.

```python
@dataclass
class Movie:
    uri: str                          # URI en Fuseki
    title: str
    genre: str | None
    runtime: int | None
    rating: float | None
    poster_url: str | None
    release_year: str | None
    compatibility_score: float        # bridge:compatibilityScore
    mood_match_score: float | None    # bridge:moodMatchScore
    social_match_score: float | None  # bridge:socialMatchScore
    energy_match_score: float | None  # bridge:energyMatchScore
    time_match_score: float | None    # bridge:timeMatchScore
    semantic_scores: dict[str, float] # dict consolidado para el LLM
    kid_friendly: bool | None

    @classmethod
    def from_fuseki_row(cls, row: dict) -> Movie: ...
    def to_response_dict(self) -> dict: ...
```

#### `ConversationSession` y `ConversationTurn`
Modelos para el flujo conversacional multi-turno.

```python
@dataclass
class ConversationTurn:
    role: str              # "user" o "assistant"
    content: str
    context: UserContext | None   # solo en turnos de usuario
    timestamp: datetime

@dataclass
class ConversationSession:
    session_id: str
    user_id: str
    turns: list[ConversationTurn]
    accumulated_context: UserContext | None   # contexto acumulado entre turnos
    created_at: datetime
    last_updated: datetime
```

### Ports definidos

```python
class GraphPort(Protocol):
    def execute_select(self, sparql: str) -> list[dict]: ...
    def execute_update(self, sparql: str) -> bool: ...
    def run_strategy(self, attempts: list[tuple[str,str]], min_results: int = 5) -> tuple[list[dict], str]: ...

class ProfilePort(Protocol):
    def get(self, user_id: str) -> UserProfile: ...
    def archive_context(self, user_id: str, context: UserContext) -> None: ...
    def invalidate_cache(self, user_id: str) -> None: ...
```

---

## Fase 1.5 — Bridge data v2

**Archivos:** `bridge_data_v2.ttl` (generado, fuera del backend)

### Qué se construyó

Una nueva versión del archivo TTL de la bridge-ontology que reemplaza el esquema antiguo (valores pipe-concatenados) con predicados individuales por película.

### Cambios respecto al bridge v1

| Aspecto | Bridge v1 | Bridge v2 |
|---------|-----------|-----------|
| Estructura | Un triple con valor concatenado `"feliz\|relajado"` | Un triple por valor: `bridge:compatibleMood "feliz"`, `bridge:compatibleMood "relajado"` |
| Filtrado SPARQL | Requería `CONTAINS()` o `SPLIT()` | Coincidencia exacta con patrón de triple |
| TimeOfDay | No existía | `bridge:compatibleTimeOfDay "morning"/"evening"` |
| KidFriendly | Score numérico solamente | `bridge:isKidFriendly true/false^^xsd:boolean` basado en certificación MPAA |

### Valores válidos en bridge v2

```
mood:      "feliz", "relajado", "estresado", "triste", "ansioso", "emocionado",
           "aburrido", "curioso", "romantico", "nostalgico", "aventurero",
           "nervioso", "concentrado", "alegre"

companion: "solo", "pareja", "familia", "familia con niños", "amigos"

energy:    "bajo", "medio", "alto"

timeOfDay: "morning", "afternoon", "evening", "night"
```

> **Pendiente:** Recargar `bridge_data_v2.ttl` en el dataset de Apache Jena Fuseki antes de probar las queries de la Fase 2.

---

## Fase 2 — Core components

**Archivos nuevos en `app/core/`:**
- `query_strategy.py`
- `scorer.py`
- `profile_service.py`
- `connection_explorer.py`

### 2.1 — `query_strategy.py`

**Función principal:** `build_strategy(ctx: UserContext, profile: UserProfile) -> list[tuple[str, str]]`

#### Qué hace

Traduce el `UserContext` (valores en inglés del LLM) a queries SPARQL con valores en español (del bridge-ontology) y devuelve una lista ordenada de intentos. El ejecutor los prueba en orden hasta obtener ≥ 5 resultados.

#### Cadena de intentos

```
1. ontology_full
   bridge:compatibleMood + bridge:compatibleCompanion + bridge:compatibleEnergyLevel
   + bridge:isKidFriendly true (solo si children_age_hint = "young")
   + FILTER runtime_max
   → 30 candidatos

2. ontology_mood_companion
   mood + companion, sin energy, sin runtime_max
   → 40 candidatos

3. ontology_mood_only
   solo mood + energy (si existe) + kid filter
   → 40 candidatos

4. ontology_companion_only
   solo companion, sin mood, sin energy
   → 40 candidatos

5. genre_filter
   FILTER(?genreName IN ("Comedy", "Drama", ...))
   → 40 candidatos

6. centrality_ranking   ← solo para cold start con señal de género
   ORDER BY rating DESC, filtrado por género
   → 50 candidatos

7. broad                ← último recurso absoluto
   Sin filtros, ORDER BY compatibilityScore DESC, rating DESC
   → 50 candidatos
```

#### Lógica cold start

Si `profile.is_cold_start = True` **y** no hay mood ni companion ni géneros en el contexto, se salta toda la cadena ontológica y va directo a:
```
centrality_ranking → broad
```

Esto evita que usuarios nuevos reciban cero resultados al hacer una consulta muy vaga.

#### Mapeos de traducción

Los valores del LLM (inglés) se traducen al español del bridge antes de generar los filtros SPARQL:

```python
MOOD_ES_MAP    = {"happy": "feliz", "relaxed": "relajado", "sad": "triste", ...}
COMPANION_ES_MAP = {"alone": "solo", "family": "familia", "friends": "amigos", ...}
ENERGY_ES_MAP  = {"low": "bajo", "medium": "medio", "high": "alto", ...}
```

Regla especial: `companion="family"` + `has_children=True` → `"familia con niños"`.

---

### 2.2 — `scorer.py`

**Función principal:** `score_and_select(candidates, ctx, profile, n=5) -> list[Movie]`

#### Qué hace

1. Convierte cada row de Fuseki a un objeto `Movie` vía `Movie.from_fuseki_row()`
2. Calcula un score compuesto para cada candidato
3. Aplica MMR (Maximal Marginal Relevance) para seleccionar los top-n con diversidad

#### Fórmula de score

**Con datos semánticos** (la película tiene `bridge:compatibilityScore`):
```
score = 0.40 × rating + 0.30 × semantic + 0.15 × freshness + 0.15 × novelty
```

**Sin datos semánticos** (estrategias `genre_filter` o `broad`):
```
score = 0.70 × rating + 0.15 × freshness + 0.15 × novelty
```

#### Componentes del score

| Componente | Cálculo | Justificación |
|------------|---------|---------------|
| `rating` | `min(rating / 10.0, 1.0)` | Calidad objetiva de la película |
| `semantic` | `bridge:compatibilityScore` (0–1) | Compatibilidad ontológica con el contexto del usuario |
| `freshness` | `(año - 1990) / (año_actual - 1990)`, clamped 0–1 | Preferencia leve por películas más recientes |
| `novelty` | `1 - profile.genre_weights.get(genre, 0)` | Penaliza géneros que el usuario ya conoce mucho, favorece variedad |

#### MMR — Maximal Marginal Relevance

Evita que las 5 recomendaciones sean todas del mismo género. En cada iteración elige la candidata que maximiza:

```
MMR(cand) = λ × score(cand) - (1 - λ) × max_sim(cand, ya_seleccionadas)
```

Con `λ = 0.7`: 70% relevancia, 30% diversidad. La similitud entre dos películas es 0.7 si comparten género, menor si tienen compatibility scores similares pero géneros distintos.

---

### 2.3 — `profile_service.py`

**Clase:** `ProfileService` (implementa `ProfilePort`)

#### `get(user_id) -> UserProfile`

1. Revisa el caché en memoria (TTL 3 minutos por usuario)
2. Si no está en caché o expiró, llama a `get_user_context_history(user_id, limit=50)` en Fuseki
3. Construye el perfil contando mood/companion/energy con `Counter`
4. `snapshot_count < 3` → `is_cold_start = True`
5. Guarda en caché y retorna

#### `archive_context(user_id, ctx) -> None`

Escribe el `UserContext` actual como triple context-ontology **directamente** en el grafo permanente del usuario en Fuseki, sin pasar por el grafo temporal de sesión:

```sparql
INSERT DATA {
  GRAPH <http://users/{user_id}/history> {
    contextdata:Session_{id}  a context:ContextSnapshot ;
        context:snapshotID     "..."^^xsd:string ;
        context:requestTimestamp "..."^^xsd:dateTime ;
        context:hourOfDay       20^^xsd:integer .
    contextdata:Mood_{id}  a context:EmotionalContext ;
        context:moodDescription "relajado"^^xsd:string ;
        context:desiredEnergyLevel "bajo"^^xsd:string .
    contextdata:Social_{id}  a context:SocialContext ;
        context:companionType "amigos"^^xsd:string ;
        context:hasChildren false^^xsd:boolean .
  }
}
```

Después de archivar, siempre llama a `invalidate_cache(user_id)` para que la próxima llamada a `get()` reconstruya el perfil con el nuevo snapshot incluido.

> **Nota:** El caché es en proceso (dict en memoria). Un reinicio del servidor lo borra. Esto es aceptable para el prototipo; en producción se reemplazaría con Redis.

---

### 2.4 — `connection_explorer.py`

**Clase:** `ConnectionExplorer`

#### `find_path(title_a, title_b) -> ConnectionPath`

BFS de hasta 3 saltos entre dos películas. En cada nodo expande por:
1. **Director compartido** (relación más fuerte — misma autoría)
2. **Género compartido** (relación estructural — misma categoría)
3. **Mood profile** (relación semántica — mismo perfil emocional en bridge)

Devuelve un `ConnectionPath` con la lista de `ConnectionHop` que describen cómo están conectadas:

```json
{
  "source": "Inception",
  "target": "The Prestige",
  "hops": [
    {"from": "Inception", "to": "The Prestige", "relation": "same_director"}
  ],
  "found": true,
  "length": 1
}
```

#### `get_neighborhood(title, depth=2) -> NetworkGraph`

Expande desde una película hasta `depth` saltos por director y género. Retorna un `NetworkGraph` con nodos y aristas listo para renderizar como grafo en el frontend. Limitado a 60 nodos para no saturar la respuesta.

#### `get_centrality_ranking(genre, limit) -> list[dict]`

Devuelve películas ordenadas por `rating DESC, compatibilityScore DESC`. Cuando `genre` está especificado, filtra por ese género. Es el mismo formato de rows que consume `Movie.from_fuseki_row()`, así que es compatible con el Scorer.

Esta función también es la que usa `query_strategy.py` internamente para las estrategias `centrality_ranking` de cold start.

---

## Fase 2.5 — Flujo conversacional

**Archivos nuevos/modificados:**
- `app/core/conversation_context.py` *(nuevo)*
- `app/application/use_cases/recommendation/chat_use_case.py` *(nuevo)*
- `app/api/schemas/recommendation.py` *(modificado — ChatRequest/ChatResponse)*
- `app/api/v1/endpoints/recommendation.py` *(modificado — endpoint `/chat`)*
- `app/api/di/movies_di.py` *(modificado — ChatUseCase DI)*

### 2.5.1 — `conversation_context.py`

Módulo de lógica pura para el manejo de contexto conversacional. Sin dependencias de framework.

#### `merge_contexts(accumulated, new) -> UserContext`

Fusiona el contexto acumulado de la sesión con el contexto extraído del nuevo turno del usuario.

| Campo | Regla |
|-------|-------|
| `mood`, `companion`, `energy`, `runtime_max`, `children_age_hint` | El nuevo sobreescribe si no es `None`; si es `None`, se conserva el anterior |
| `genres` | El nuevo reemplaza si no está vacío; si está vacío, se conserva el anterior |
| `exclusions` | **Se acumulan** (unión ordenada, sin duplicados) |
| `time_of_day` | **Siempre del turno actual** (reloj del servidor) |
| `has_children` | `True` si cualquiera de los dos turnos lo marcó como `True` |
| `confidence` | Sube `+0.05` por turno, máximo `0.95` |
| `session_id` | Se conserva el de `accumulated` si existe |
| `raw_query` | Siempre del turno nuevo |

**Ejemplo de acumulación en 3 turnos:**

```
Turno 1: "algo de terror"
  → mood=None, genres=["Horror"], runtime_max=None

Turno 2: "que no sea muy larga"
  → mood=None, genres=[], runtime_max=90
  → merged: genres=["Horror"], runtime_max=90   ← se acumula

Turno 3: "estoy nervioso"
  → mood="anxious", genres=[], runtime_max=None
  → merged: mood="anxious", genres=["Horror"], runtime_max=90   ← todo acumulado
```

#### `query_context_to_user_context(qctx, session_id, now) -> UserContext`

Puente entre el modelo legacy `QueryContext` (que devuelve el `GeminiAdapter` actual) y el nuevo `UserContext` del dominio. Esta función es temporal: en la Fase 3, el adaptador Gemini se actualizará para devolver `UserContext` directamente.

El puente:
- Mapea `social_context.companionType` → `companion`
- Mapea `social_context.hasChildren` → `has_children`
- Inyecta `time_of_day` desde el reloj del servidor
- Aplica detección de `children_age_hint` por keywords ("pequeños" → "young", "adolescentes" → "teen")

#### `SessionStore`

Diccionario en memoria de `session_id → ConversationSession` con TTL de **2 horas** de inactividad. Se evictan sesiones expiradas automáticamente en cada `get_or_create`. Singleton de módulo (`session_store`) compartido entre todos los requests.

---

### 2.5.2 — `chat_use_case.py`

**Clase:** `ChatUseCase`

Es el primer use case que usa los cuatro componentes de la Fase 2 de forma integrada.

#### Dependencias del constructor

```python
ChatUseCase(
    llm_client: RecommendationLlmClientPort,   # GeminiAdapter
    profile_service: ProfileService,           # Fase 2
)
```

#### Flujo del método `execute(session_id, messages, user_id)`

```
1. Extraer último mensaje de usuario
         ↓
2. LLM.extract_query_context(last_query)
   → QueryContext (modelo legacy)
         ↓
3. query_context_to_user_context()
   → UserContext (con time_of_day del servidor)
         ↓
4. session_store.get_or_create(session_id)
   → ConversationSession con accumulated_context
         ↓
5. merge_contexts(accumulated, new) → merged_ctx
         ↓
6. profile_service.get(user_id) → UserProfile
         ↓
7. build_strategy(merged_ctx, profile) → [(name, sparql), ...]
         ↓
8. _run_strategy(attempts)
   → prueba en orden hasta len(rows) >= 5
   → (rows, strategy_used)
         ↓
9. score_and_select(rows, merged_ctx, profile, n=5)
   → [Movie × 5] con MMR
         ↓
10. LLM.generate_recommendation_explanation(
       query_type = "mood_driven" | "social" | "cold_start" | "general"
    ) → explanation
         ↓
11. session.accumulated_context = merged_ctx  ← persiste para próximo turno
    session.add_turn(usuario)
    session.add_turn(asistente)
    session_store.update(session)
         ↓
12. profile_service.archive_context(user_id, merged_ctx)
    → INSERT en Fuseki history graph
         ↓
13. ChatResult(movies, explanation, strategy_used, context, execution_ms)
```

---

### 2.5.3 — Endpoint `/chat`

```
POST /api/v1/recommendation/chat
Authorization: Bearer {jwt}
Content-Type: application/json
```

**Request:**
```json
{
  "session_id": "sess_abc123",
  "messages": [
    {"role": "user",      "content": "algo de terror"},
    {"role": "assistant", "content": "Te recomiendo The Shining..."},
    {"role": "user",      "content": "que no sea muy larga"}
  ]
}
```

> El `user_id` no va en el body — se extrae del JWT (campo `sub`). El frontend gestiona el `session_id` localmente (puede ser un UUID generado al abrir la pantalla de chat).

**Response:**
```json
{
  "session_id": "sess_abc123",
  "movies": [
    {
      "title": "Get Out",
      "posterUrl": "https://...",
      "runtime": 104,
      "genreName": "Horror",
      "releaseDate": "2017",
      "averageRating": 7.7,
      "compatibilityScore": 0.87,
      "moodMatchScore": 0.9,
      "socialMatchScore": null,
      "energyMatchScore": 0.75,
      "timeMatchScore": 0.8,
      "kidFriendly": false
    }
  ],
  "explanation": "Basándome en tu estado ansioso y preferencia por el terror...",
  "strategy_used": "ontology_mood_only",
  "context_extracted": {
    "mood": "anxious",
    "companion": null,
    "genres": ["Horror"],
    "runtime_max": 90,
    "exclusions": [],
    "confidence": 0.95,
    "time_of_day": "evening"
  },
  "execution_ms": 1240,
  "turn_count": 2
}
```

---

## Fase 3 — Limpieza de `RecommendationUseCase`

**Archivos modificados:**
- `app/application/use_cases/recommendation/recommendation_use_case.py` *(reescrito)*
- `app/domain/ports/recommendation_llm_client.py` *(nuevo método)*
- `app/adapters/llm/gemini_recommendation_llm_adapter.py` *(nuevo método)*
- `app/core/conversation_context.py` *(bugs corregidos)*
- `app/api/schemas/recommendation.py` *(esquema actualizado)*
- `app/application/use_cases/recommendation/__init__.py` *(exportaciones limpias)*
- `app/api/di/movies_di.py` *(DI actualizado)*

### Qué se hizo

#### Bugs corregidos en Phase 2/2.5

1. **Import no usado** en `conversation_context.py`: `from dataclasses import replace` eliminado.
2. **Raw query en bridge**: `query_context_to_user_context` recibía `qctx.intent` ("family", "horror") para detectar `children_age_hint` en lugar del texto real del usuario. Se agregó el parámetro `raw_query: str` y se corrigió la llamada en `ChatUseCase`.
3. **`_infer_children_age_hint`** renombrada a `infer_children_age_hint` (pública) para poder usarla desde el adaptador Gemini.
4. **`_attach_raw_query`** eliminada de `chat_use_case.py` — ahora `raw_query` se pasa directamente a la función de conversión.

#### Nuevo método `extract_user_context` en el LLM port y el adaptador

```python
# RecommendationLlmClientPort
def extract_user_context(
    self,
    query: str,
    now: datetime | None = None,
    session_id: str | None = None,
) -> UserContext: ...
```

El `GeminiAdapter` implementa este método llamando a Gemini con el mismo NLU prompt y construyendo `UserContext` directamente (sin pasar por `QueryContext`). Injección de `time_of_day` desde `now`, detección de `children_age_hint` desde el texto crudo, y fallback a keyword extraction con `confidence=0.5`.

#### `RecommendationUseCase` — de 450 líneas a ~100

El pipeline del nuevo use case:

```
llm.extract_user_context(query)        → UserContext
profile_service.get(user_id)           → UserProfile
build_strategy(ctx, profile)           → [(name, sparql), ...]
_run_strategy(attempts)                → (rows, strategy_used)
score_and_select(rows, ctx, profile)   → [Movie × 5]
llm.generate_recommendation_explanation() → explanation
profile_service.archive_context(...)   → escribe en Fuseki
```

Eliminados del use case anterior:
- Toda la lógica de scoring inline (ahora en `scorer.py`)
- Toda la generación de SPARQL inline (ahora en `query_strategy.py`)
- La inyección/limpieza del snapshot RDF (ya no se usa en el flujo single-turn)
- El MMR inline (ahora en `scorer.py`)
- Las dependencias a `UserFavoritesUseCase` y `QueryHistoryUseCase`

El use case ahora recibe `(llm_client, profile_service)` en lugar de `(favorites_use_case, history_use_case, llm_client)`.

#### Esquema de respuesta actualizado

`RecommendedMovieResponse` ahora devuelve los campos ricos del `Movie` domain model en lugar del esquema simplificado anterior:

| Antes | Ahora |
|-------|-------|
| `movieUri`, `title`, `score`, `genres: list`, `rating`, `year`, `runtime`, `posterUrl` | `title`, `posterUrl`, `runtime`, `genreName`, `releaseDate`, `averageRating`, `compatibilityScore`, `moodMatchScore`, `socialMatchScore`, `energyMatchScore`, `timeMatchScore`, `kidFriendly` |

`ChatMovieResponse` es ahora un alias de `RecommendedMovieResponse` — ambos endpoints devuelven exactamente la misma estructura de película.

---

## Fase 4 — Endpoints del explorador de conexiones

**Archivos nuevos/modificados:**
- `app/api/schemas/connections.py` *(nuevo)*
- `app/api/v1/endpoints/connections.py` *(nuevo)*
- `app/api/v1/router.py` *(modificado — router registrado)*

### Tres endpoints REST

```
GET /api/v1/movies/connections/path?source=Inception&target=The+Prestige
GET /api/v1/movies/connections/neighborhood?title=Inception&depth=2
GET /api/v1/movies/connections/centrality?genre=Drama&limit=20
```

Todos requieren JWT (`Authorization: Bearer {token}`). El prefijo `/movies/connections` está definido en el router del módulo de endpoints.

---

### 4.1 — `GET /path`

Encuentra el camino más corto entre dos películas en el grafo de conocimiento, usando el BFS del `ConnectionExplorer`.

**Parámetros:**

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `source`  | string | Sí | Título de la película origen |
| `target`  | string | Sí | Título de la película destino |

**Respuesta (`ConnectionPathResponse`):**
```json
{
  "source": "Inception",
  "target": "The Prestige",
  "found": true,
  "hops": [
    { "from_title": "Inception", "to_title": "The Prestige", "relation": "same_director" }
  ],
  "length": 1
}
```

Valores posibles de `relation`: `"same_director"`, `"same_genre"`, `"same_mood_profile"`.
Si no existe camino en ≤ 3 saltos: `"found": false`, `"hops": []`.

---

### 4.2 — `GET /neighborhood`

Devuelve el grafo de vecindad alrededor de una película hasta N saltos. Los nodos representan películas; las aristas indican el tipo de relación.

**Parámetros:**

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `title`   | string | — | Título de la película central |
| `depth`   | int (1–3) | `2` | Profundidad de expansión |

**Respuesta (`NetworkGraphResponse`):**
```json
{
  "center_title": "Inception",
  "nodes": [
    { "uri": "http://ont/m1", "title": "Inception", "genre": "Sci-Fi", "rating": 8.8, "poster_url": null },
    { "uri": "http://ont/m2", "title": "Interstellar", "genre": "Sci-Fi", "rating": 8.6, "poster_url": "..." }
  ],
  "edges": [
    { "source_uri": "http://ont/m1", "target_uri": "http://ont/m2", "relation": "same_genre" }
  ],
  "node_count": 2,
  "edge_count": 1
}
```

Limitado a 60 nodos para mantener respuestas manejables.

---

### 4.3 — `GET /centrality`

Devuelve las películas más centrales del grafo (mayor rating + compatibilityScore), opcionalmente filtradas por género. Útil para pantallas de inicio y cold start.

**Parámetros:**

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `genre`   | string | `null` | Filtrar por género (opcional) |
| `limit`   | int (1–100) | `20` | Número máximo de películas |

**Respuesta (`CentralityResponse`):**
```json
{
  "genre": "Drama",
  "movies": [
    {
      "title": "The Shawshank Redemption",
      "posterUrl": "https://...",
      "runtime": 142,
      "genreName": "Drama",
      "releaseDate": "1994",
      "averageRating": 9.3,
      "compatibilityScore": 0.95,
      "moodMatchScore": 0.88,
      "socialMatchScore": 0.72,
      "energyMatchScore": 0.60,
      "timeMatchScore": 0.80,
      "kidFriendly": false
    }
  ],
  "total": 1
}
```

Cada película en `movies` es idéntica al esquema `RecommendedMovieResponse` para consistencia entre endpoints.

---

### 4.4 — Inyección de dependencias

`ConnectionExplorer` es stateless (sin estado interno, sin dependencias del constructor), por lo que se crea una sola instancia por proceso usando `@lru_cache(maxsize=1)`:

```python
@lru_cache(maxsize=1)
def _explorer_singleton() -> ConnectionExplorer:
    return ConnectionExplorer()

def get_connection_explorer() -> ConnectionExplorer:
    return _explorer_singleton()
```

No se agregó al DI global (`movies_di.py`) porque el explorador no necesita pasar por el contenedor de dependencias del use case. FastAPI lo inyecta directamente en cada endpoint vía `Depends(get_connection_explorer)`.

---

### Smoke test — Phase 4

**Script:** `scripts/smoke_test_phase4.py`

25 checks en 7 secciones, sin requerir Fuseki ni Gemini activos:

| Sección | Checks |
|---------|--------|
| Imports (módulo, schemas, endpoint, prefijo de router) | 4 |
| Dataclasses (`ConnectionHop`, `ConnectionPath.length`, `NetworkGraph`, `_esc`) | 4 |
| Pydantic schemas (serialización, campos opcionales, conteos) | 5 |
| `ConnectionExplorer` con Fuseki mockeado | 7 |
| Helper `_movie_to_response` | 2 |
| `Movie.from_fuseki_row` con datos de centralidad | 2 |
| Registro de rutas en `api_router` | 1 |

Resultado: **25/25 PASS**.

---

## Fase 5 — Métricas de calidad

**Archivos nuevos/modificados:**
- `app/core/metrics.py` *(nuevo)*
- `app/application/use_cases/recommendation/recommendation_use_case.py` *(integración)*
- `app/application/use_cases/recommendation/chat_use_case.py` *(integración)*
- `app/api/schemas/recommendation.py` *(nuevo schema `RecommendationMetricsResponse`)*
- `app/api/v1/endpoints/recommendation.py` *(expone métricas en `/chat`)*

### 5.1 — `app/core/metrics.py`

Módulo de lógica pura (sin dependencias de framework). Expone:

```python
@dataclass
class ListMetrics:
    ild: float                 # Intra-List Diversity (0–1)
    semantic_precision: float  # fracción de películas con compatibilityScore > umbral
    cold_start_threshold: int  # umbral adaptativo de snapshots
    semantic_threshold: float  # umbral usado (almacenado para transparencia)
    movie_count: int           # películas en la lista

def compute_ild(movies: list[Movie]) -> float: ...
def compute_semantic_precision(movies: list[Movie], threshold: float = 0.7) -> float: ...
def compute_cold_start_threshold(profile: UserProfile) -> int: ...
def compute_metrics(movies, profile, semantic_threshold=0.7) -> ListMetrics: ...
```

### 5.2 — ILD (Intra-List Diversity)

Distancia promedio por pares entre las películas de la lista, usando distancia de género binaria:

```
dist(a, b) = 0  si mismo género
             1  si géneros distintos (o uno de ellos es None)

ILD = sum(dist(a, b) for all pairs) / C(n, 2)
```

| Caso extremo | ILD |
|---|---|
| Todas del mismo género | 0.0 |
| Todas de géneros distintos | 1.0 |
| Lista vacía o de un elemento | 0.0 |

### 5.3 — Precisión semántica

```
precision = len([m for m in movies if m.compatibility_score > 0.7]) / len(movies)
```

La comparación es **estrictamente mayor** (`>`), por lo que un score exactamente en el umbral no se cuenta.

### 5.4 — Umbral de cold start adaptativo

Reemplaza el valor fijo de 3. Basado en la diversidad de géneros del perfil del usuario:

| Géneros distintos en `profile.genre_weights` | Diversidad (`min(n,5)/5`) | Umbral |
|---|---|---|
| 0 | 0.0 | 5 |
| 1–2 | 0.2–0.4 | 3 |
| 3+ | 0.6–1.0 | 2 |

**Rationale:** un usuario que ya demostró preferencias por 3 géneros distintos tiene un perfil suficientemente informativo con sólo 2 snapshots. Un usuario sin historial de géneros requiere 5 snapshots para salir del modo cold start.

### 5.5 — Integración en el pipeline

`compute_metrics(movies, profile)` se llama inmediatamente después de `score_and_select()` en ambos use cases. El resultado se incluye en:
- El payload de API (`"metrics"` en la respuesta JSON)
- El debug payload (para `/debug` y logs internos)

**Schema de respuesta:**
```json
{
  "metrics": {
    "ild": 0.8,
    "semanticPrecision": 0.6,
    "coldStartThreshold": 3,
    "movieCount": 5
  }
}
```

### Smoke test — Phase 5

**Script:** `scripts/smoke_test_phase5.py`

42 checks en 8 secciones, sin requerir Fuseki ni Gemini:

| Sección | Checks |
|---|---|
| Imports y campos en schemas/dataclasses | 4 |
| `ListMetrics` dataclass | 3 |
| `compute_ild` (casos límite y valores esperados) | 6 |
| `compute_semantic_precision` (umbral estricto, custom threshold) | 6 |
| `compute_cold_start_threshold` (5 perfiles distintos) | 5 |
| `compute_metrics` integración | 8 |
| Pydantic schema serialización | 5 |
| `_Result.to_api_dict()` con métricas | 5 |

---

## Fase 6 — Pipeline NetworkX offline

**Archivo nuevo:** `scripts/compute_network_metrics.py`
**Smoke test:** `scripts/smoke_test_phase6.py`
**pyproject.toml:** agregadas dependencias `networkx>=3.0`, `python-louvain>=0.16`

### Por qué

SPARQL no puede calcular betweenness centrality, coeficiente de clustering ni detectar comunidades Leiden/Louvain. Es necesario exportar el grafo a NetworkX, calcular las métricas offline y persistirlas como tripletas RDF en Fuseki para que el backend las consulte en tiempo de request.

### Qué construyó

Script ejecutable autónomo (sin imports de `app.*`) que:
1. Obtiene todos los movies con sus directores y géneros via SPARQL
2. Construye grafo película-película ponderado en NetworkX:
   - Aristas de director (weight=2) — máximo 30 películas por director
   - Aristas de género (weight=1) — máximo 100 películas por género (sample si >500)
3. Calcula con NetworkX: `degree_centrality`, `betweenness_centrality` (k=300, aproximado), `pagerank`, `clustering`
4. Detecta comunidades con `community_louvain.best_partition` (Louvain) y calcula modularidad
5. Genera etiquetas de cluster en español usando Gemini (`google-genai`)
6. Limpia tripletas viejas con DELETE WHERE y escribe nuevas en batches de 500

### Nuevas tripletas escritas en Fuseki

```turtle
PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>

<moviedata:uri>
    movie:degreeCentrality        "0.0124"^^xsd:float ;
    movie:betweennessCentrality   "0.0531"^^xsd:float ;
    movie:pageRank                "0.00038"^^xsd:float ;
    movie:clusteringCoefficient   "0.2100"^^xsd:float ;
    movie:belongsToCluster        "14"^^xsd:string ;
    movie:clusterLabel            "Sci-Fi Épico Contemplativo"^^xsd:string .
```

### Cómo ejecutar

```bash
# Desde la raíz del proyecto backend
cd movie-graph-rag-backend-fastapi
pip install networkx python-louvain  # si no están instalados
python scripts/compute_network_metrics.py
# Verificar resultado:
python scripts/smoke_test_phase6.py
```

> **Nota:** betweenness con k=300 puede tardar 10-30 minutos en el grafo completo (~9700 nodos). El resto del pipeline es rápido.

### Decisiones de diseño

- **Sin imports de app.*** — el script tiene sus propias funciones HTTP para Fuseki (stdlib `urllib`), evitando dependencias del runtime de FastAPI
- **Batches de 500 tripletas** — evita timeouts de Fuseki con INSERT DATA masivos
- **Graceful fallbacks** — cada paso (betweenness, community detection, Gemini labels) está envuelto en try/except; un fallo parcial no aborta el script completo
- **Delete antes de insert** — garantiza idempotencia (se puede re-ejecutar sin duplicar tripletas)

### Smoke test — Phase 6

**Script:** `scripts/smoke_test_phase6.py`

Requiere Fuseki activo y que `compute_network_metrics.py` haya corrido exitosamente.

| Sección | Checks |
|---|---|
| Conectividad a Fuseki | 1 (abort si falla) |
| `degreeCentrality` — ≥500 movies, valores en [0,1] | 2 |
| `belongsToCluster` — ≥5 clusters distintos | 1 |
| `clusterLabel` — ≥5 labels distintos y no vacíos | 2 |
| `pageRank` — ≥500 movies, valores > 0.0 | 2 |
| `clusteringCoefficient` + `betweennessCentrality` | 2 |

---

## Fase 7 — Graph Diversity Score

**Archivos modificados:**
- `app/core/metrics.py`
- `app/api/schemas/recommendation.py`
- `app/application/use_cases/recommendation/chat_use_case.py`
- `app/application/use_cases/recommendation/recommendation_use_case.py`

**Archivo nuevo:** `scripts/smoke_test_phase7.py`

### Por qué

El ILD existente (Fase 5) usa distancia binaria por género: 0 si mismo género, 1 si distinto. Esto no captura la riqueza semántica del grafo — una película de Drama oscura está más cerca de un Thriller que de una Comedia, pero ILD las trata igual.

`graphDiversityScore` usa la distancia BFS real (hops) entre pares de películas recomendadas. El `ConnectionExplorer.find_path()` ya existía (Fase 4); esta fase lo conecta con las métricas de la lista de recomendaciones.

### Qué construyó

#### `compute_graph_diversity(movies, explorer) -> float`

```python
def compute_graph_diversity(movies: list[Movie], explorer: ConnectionExplorer) -> float:
    """Distancia BFS promedio entre todos los pares del top-K, normalizada a [0, 1]."""
    # Si < 2 películas → sin pares → retorna 1.0
    # Para cada par (i, j):
    #   - clave de caché: (min(title_a, title_b), max(title_a, title_b))
    #   - llama explorer.find_path(title_a, title_b)
    #   - si path.found: hops = path.length; else: hops = _MAX_HOPS (= 3)
    #   - normaliza: hops / _MAX_HOPS
    # Retorna promedio de distancias normalizadas
```

**Cache:** `_PATH_CACHE: dict[tuple[str, str], int]` a nivel de módulo — persiste entre requests en el mismo proceso.

#### Nuevos campos

`ListMetrics.graph_diversity_score: float = 0.0`
`RecommendationMetricsResponse.graphDiversityScore: float = 0.0`

#### Integración en use cases

Ambos `ChatUseCase.execute()` y `RecommendationUseCase._run()` crean un `ConnectionExplorer()` local y lo pasan a `compute_metrics(movies, profile, explorer=explorer)`.

`_Result.to_api_dict()` incluye `"graphDiversityScore": self.metrics.graph_diversity_score`.

#### Decisiones de diseño

- **TYPE_CHECKING guard** para importar `ConnectionExplorer` en `metrics.py` — evita import circular en tiempo de ejecución
- **`explorer=None` como default** — `compute_metrics` sin explorer retorna `graph_diversity_score=0.0`, preservando 100% de compatibilidad con código existente
- **Fallback a _MAX_HOPS cuando find_path no encuentra camino** — trata películas sin conexión en 3 hops como "máxima diversidad", evitando penalizar listas diversas

### Smoke test — Phase 7

**Script:** `scripts/smoke_test_phase7.py`

16 checks en 7 secciones, sin requerir Fuseki ni Gemini:

| Sección | Checks |
|---|---|
| Imports | 2 |
| `graphDiversityScore` en schema | 2 |
| Lista de 1 película → 1.0 | 1 |
| Path no encontrado → trata como distancia máxima | 1 |
| `ListMetrics.graph_diversity_score` | 2 |
| `compute_metrics(explorer=None)` → 0.0, ILD correcto | 3 |
| Serialización Pydantic correcta | 5 |

**Resultado:** 16/16 PASS ✅

Resultado: **42/42 PASS**.

---

## Fase 8 — Dashboard Topológico

**Archivos nuevos:**
- `app/api/schemas/graph.py`
- `app/api/v1/endpoints/graph.py`
- `movie-graph-rag-frontend/services/graph.service.ts`
- `movie-graph-rag-frontend/app/topology/page.tsx`
- `scripts/smoke_test_phase8.py`

**Archivos modificados:** `app/api/v1/router.py`

**Dependencia:** Fase 6 completada ✅ (métricas cargadas en Fuseki)

### Qué se construyó

Un endpoint REST y una página frontend que exponen las métricas topológicas globales calculadas offline por el pipeline de Fase 6.

**Backend — `GET /graph/topology`:**
- Devuelve `GraphTopologyResponse` con cuatro secciones: `graphSummary`, `topByDegree`, `topByBetweenness`, `topByPageRank`, `clusterSummary`.
- Resultado cacheado en memoria con `@lru_cache(maxsize=1)`: la topología no cambia entre ejecuciones del pipeline, por lo que una sola llamada a Fuseki es suficiente.
- El campo `isSmallWorld` se deduce dinámicamente: `clusteringCoefficient > 0.3` y `communityCount >= 5`.

**Frontend — `/topology`:**
- Dashboard con tarjetas de resumen (películas, aristas, grado promedio, clustering, comunidades, modularidad).
- Tres rankings de centralidad (degree / betweenness / PageRank) con barras horizontales construidas en Tailwind puro — sin dependencia de ninguna librería de gráficas.
- Tabla de comunidades Louvain con barra de proporción relativa.
- Banner condicional "Small-world detectado" cuando se cumple la propiedad.

### Por qué se construyó así

- **Sin librería de gráficas:** `package.json` no incluía Recharts ni D3; instalar dependencias externas requiere aprobación y no aporta valor diferencial aquí. Las barras CSS-width son suficientes para mostrar rankings ordinales.
- **Cache en endpoint:** Las métricas topológicas son estáticas entre ejecuciones del pipeline. Cachear evita N consultas SPARQL por cada visita a la página.
- **`fetch_limit = limit * 10` en `_fetch_top`:** El JOIN OPTIONAL de género puede producir múltiples filas por película; sobrecargar la consulta y deduplicar garantiza exactamente N entradas únicas.
- **Patrón singleton idéntico a `connections.py`:** Coherencia con el resto de endpoints de la API.

### Cómo funciona

```
GET /api/v1/graph/topology
  → _cached_topology()              # lru_cache(maxsize=1)
    → _fetch_summary()              # AVG + COUNT sobre tripletas Phase 6
    → _fetch_top("degreeCentrality", 10)
    → _fetch_top("betweennessCentrality", 10)
    → _fetch_top("pageRank", 10)
    → _fetch_clusters()             # GROUP BY clusterId
    → GraphTopologyResponse(...)
```

Frontend: `useEffect → getGraphTopology() → setState(data)` → renderiza tarjetas + barras + tabla.

### Prueba de humo

| Check | Resultado |
|-------|-----------|
| Schemas importan y serializan | 5 |
| Endpoint importa, prefijo correcto, callable | 3 |
| degreeCentrality ≥500 películas en Fuseki | 1 |
| top-10 por degree retorna 10 filas | 1 |
| Valores en [0, 1] | 1 |
| betweennessCentrality ≥500 películas | 1 |
| pageRank ≥500 películas | 1 |
| ≥5 clusters distintos | 1 |
| clusterLabel no vacío | 1 |
| `_build_topology()` retorna tipo correcto | 1 |
| totalMovies ≥500 | 1 |
| communityCount ≥5 | 1 |
| topByDegree tiene 10 entradas | 1 |
| clusterSummary no vacío | 1 |
| modularity en [0, 1] | 1 |

**Resultado:** 21/21 PASS ✅

---

## Fase 9 — Recomendacion por Comunidad

**Archivos nuevos:**
- `app/api/schemas/clusters.py`
- `app/api/v1/endpoints/clusters.py`
- `services/clusters.service.ts` (frontend — solo tipos y cliente HTTP)
- `scripts/smoke_test_phase9.py`

**Archivos modificados:** `app/api/v1/router.py`

**Dependencia:** Fase 6 completada (tripletas `movie:belongsToCluster` y `movie:clusterLabel` en Fuseki)

### Que se construyo

Dos endpoints REST que exponen la estructura de comunidades Louvain calculada en Fase 6:

**`GET /movies/{title}/cluster`** — `MovieClusterResponse`:
- Encuentra la comunidad (cluster) a la que pertenece la pelicula.
- Devuelve hasta 10 peliculas del mismo cluster ordenadas por rating (**intra-cluster**).
- Devuelve hasta 3 clusters adyacentes con peliculas puente (**inter-cluster**), identificados como los clusters que comparten mas generos dominantes con el cluster fuente.

**`GET /clusters`** — `ClusterListResponse`:
- Lista todas las comunidades ordenadas por tamano.
- Incluye etiqueta generada por LLM, numero de peliculas y hasta 3 ejemplos representativos.
- Resultado cacheado con `@lru_cache(maxsize=1)` — la lista de clusters no cambia entre ejecuciones del pipeline.

### Por que se construyo asi

- **Intra vs. inter-cluster:** Ambos tipos de recomendacion son diferenciales frente a sistemas convencionales — ningun modelo de collaborative filtering puede hacer recomendacion semantica por comunidades topologicas.
- **`_cached_cluster_list()` con lru_cache:** La lista de clusters requiere dos queries SPARQL (tallas + ejemplos). Se cachea en memoria para que la pagina de clusters no ejecute queries en cada visita.
- **Busqueda de adyacentes por generos compartidos:** El enfoque basado en `VALUES ?sharedGenre` en SPARQL es preciso y eficiente; Fuseki optimiza el join con indice de propiedades. La alternativa (PageRank sobre clusters) requeriria datos que no estan en Fuseki.
- **Deduplicacion en Python:** Los OPTIONAL en SPARQL pueden producir multiples filas por pelicula (una por genero). Se deduplicacion por titulo antes de devolver la lista.

### Como funciona

```
GET /movies/{title}/cluster
  1. SPARQL: find ?clusterId + ?clusterLabel for ?title
  2. SPARQL: COUNT(DISTINCT ?m) WHERE belongsToCluster = clusterId
  3. SPARQL: top genres in cluster (GROUP BY genreName)
  4. SPARQL: top 50 intra-cluster movies ORDER BY rating → deduplicate → take 10
  5. SPARQL: adjacent clusters sharing dominant genres (GROUP BY otherClusterId)
  6. for each adjacent cluster: SPARQL top 3 bridge movies → AdjacentCluster

GET /clusters
  → _cached_cluster_list()          # lru_cache(maxsize=1)
    1. SPARQL: GROUP BY clusterId → sizes + labels
    2. SPARQL: all movies ORDER BY clusterId DESC(rating) LIMIT 3000
       → group in Python, take first 3 per cluster → exampleMovies
```

### Prueba de humo

| Seccion | Checks | Resultado |
|---------|--------|-----------|
| Schemas importan y serializan | 6 | OK |
| Endpoints importan, rutas presentes | 6 | OK |
| GET /clusters: >=5 clusters, ordenados, con ejemplos | 7 | OK |
| GET /movies/{title}/cluster: intraCluster, adyacentes, bridge | 11 | OK |

**Resultado:** 30/30 PASS
