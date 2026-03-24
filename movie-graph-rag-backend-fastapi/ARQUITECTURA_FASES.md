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
| 5 | Métricas: ILD, precisión semántica, umbral cold start | ⏳ Pendiente |

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

### Fase 5 — Métricas de calidad

- **ILD (Intra-List Diversity):** mide qué tan diversas son las 5 películas recomendadas en una lista. Se calcula como la distancia promedio por pares en el espacio de géneros.
- **Precisión semántica:** porcentaje de recomendaciones con `compatibilityScore > 0.7`.
- **Umbral de cold start:** número de snapshots mínimos para salir del modo cold start (actualmente fijo en 3 — la Fase 5 lo hará adaptativo).
