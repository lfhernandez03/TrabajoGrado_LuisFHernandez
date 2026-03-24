# Contexto del proyecto: Sistema de recomendación de películas con GraphRAG

## Qué es este proyecto

Sistema de recomendación de películas basado en ontologías OWL y GraphRAG, desarrollado
como trabajo de grado en la Universidad del Valle (Escuela de Ingeniería de Sistemas y
Computación). Combina razonamiento ontológico sobre un grafo de conocimiento (Apache Jena
Fuseki) con un LLM (Google Gemini 1.5 Flash) para recomendaciones contextualizadas.

El sistema está siendo reconstruido con arquitectura limpia. NO es un refactor incremental
del código anterior — es una reconstrucción deliberada con separación clara de capas.

---

## Stack tecnológico

- **Backend**: FastAPI + Python 3.12
- **Base de conocimiento**: Apache Jena Fuseki (SPARQL 1.1)
- **LLM**: Google Gemini 1.5 Flash vía SDK `google-genai`
- **Base de datos**: MongoDB (usuarios, historial, favoritos, métricas)
- **Ontologías**: OWL 2 en formato Turtle (.ttl)

---

## Arquitectura de carpetas actual

```
app/
  domain/
    entities/
      recommendation_models.py   ← UserContext, UserProfile, Movie,
                                    RecommendationResult, ConversationTurn,
                                    ConversationSession (COMPLETADO)
      auth_user.py
      favorite_movie.py
      query_context.py           ← LEGACY: QueryContext, se está migrando
      query_history.py
      recommendation_metric.py
    ports/
      graph_port.py              ← GraphPort, ProfilePort (COMPLETADO)
      recommendation_llm_client.py
      auth_user_repository.py
      query_history_repository.py
      recommendation_metrics_repository.py
      user_favorites_repository.py
    errors/
      auth.py
    events/
      base.py
      history_events.py
      recommendation_events.py
      user_events.py
  adapters/
    llm/
      gemini_recommendation_llm_adapter.py  ← GeminiRecommendationLlmAdapter
    repositories/
      mongo_auth_user_repository.py
      mongo_movie_catalog_repository.py
      mongo_query_history_repository.py
      mongo_recommendation_metrics_repository.py
      mongo_user_favorites_repository.py
  api/
    di/
      auth_di.py
      common_di.py
      di_container.py
      movies_di.py
      recommendation_di.py
    schemas/
      recommendation.py
      auth.py
      favorites.py
      history.py
      movies.py
    v1/
      endpoints/
        admin.py
        auth.py
        health.py
        history.py
        movies.py
        recommendation.py
        users.py
      router.py
    dependencies.py
  application/
    events/
      event_bus.py
      event_handlers.py
    use_cases/
      auth/
        auth_user.py
      history/
        query_history.py
      movies/
        movies.py
      recommendation/
        models.py
        recommendation_metrics.py
        recommendation_use_case.py  ← ARCHIVO PRINCIPAL (450 líneas, funciona pero se va a limpiar)
      users/
  core/
    config.py
    database.py
    fuseki_client.py              ← execute_select_query, execute_update_query,
                                    copy_graph_to_user_history, get_user_context_history,
                                    user_history_graph_exists
    ontology_query_builder.py     ← build_cross_ontology_sparql, inject/delete_context_snapshot,
                                    translate_mood/companion/energy
    recommendation_llm.py         ← LEGACY: módulo antiguo, en proceso de reemplazo
    security.py
  infrastructure/
    logging/
      structured_logger.py
    resilience/
      circuit_breaker.py
  main.py
```

---

## Ontologías cargadas en Fuseki

Tres archivos TTL completamente cargados:

### movie-ontology (movies_data.ttl)

```
Namespace: movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>
Data namespace: moviedata: <http://www.semanticweb.org/movierecommendation/data/movie/>

Propiedades relevantes por película:
  ?movie rdf:type movie:FeatureFilm
  ?movie movie:hasTitle "string"
  ?movie movie:hasMainGenre genre:Comedy   ← URI, no literal
  genre:Comedy movie:genreName "Comedy"    ← literal en el nodo de género
  ?movie movie:hasAverageRating "float"^^xsd:float
  ?movie movie:runtime integer
  ?movie schema1:image "url"               ← schema1: es http://schema.org/, NO movie:
  ?movie movie:releaseDate "date"^^xsd:date
  ?movie movie:hasDirector person:Name
  ?movie movie:hasCertification moviedata:certification_PG

Géneros disponibles (literales exactos):
  "Action", "Adventure", "Animation", "Children", "Comedy", "Crime",
  "Documentary", "Drama", "Fantasy", "Film-Noir", "Horror", "IMAX",
  "Musical", "Mystery", "Romance", "Sci-Fi", "Thriller", "War", "Western"
```

### bridge-ontology (bridge_data_v2.ttl — NUEVA VERSIÓN)

```
Namespace: bridge: <http://www.semanticweb.org/movierecommendation/ontologies/2025/bridge-ontology#>

Propiedades por película (predicados INDIVIDUALES, no pipe-concatenados):
  ?movie bridge:compatibleMood "relajado"          ← múltiples triples por película
  ?movie bridge:compatibleCompanion "familia"       ← múltiples triples
  ?movie bridge:compatibleEnergyLevel "medio"       ← múltiples triples
  ?movie bridge:compatibleTimeOfDay "evening"       ← NUEVO: múltiples triples
  ?movie bridge:isKidFriendly true/false^^xsd:boolean
  ?movie bridge:compatibilityScore "0.83"^^xsd:float
  ?movie bridge:moodMatchScore "0.9"^^xsd:float
  ?movie bridge:socialMatchScore "0.9"^^xsd:float
  ?movie bridge:energyMatchScore "0.9"^^xsd:float
  ?movie bridge:timeMatchScore "0.75"^^xsd:float    ← NUEVO

Valores válidos (español exacto):
  mood: "feliz", "relajado", "estresado", "triste", "ansioso", "emocionado",
        "aburrido", "curioso", "romantico", "nostalgico", "aventurero", "nervioso",
        "concentrado", "alegre"
  companion: "solo", "pareja", "familia", "familia con niños", "amigos"
  energy: "bajo", "medio", "alto"
  timeOfDay: "morning", "afternoon", "evening", "night"

Kid-friendly: basado en certificación MPAA (G=siempre, PG+Animation/Children=sí,
              PG-13/R/NC-17=no, sin certificación=fallback a géneros)
```

### context-ontology (contexto dinámico por sesión)

```
Namespace: context: <http://www.semanticweb.org/movierecommendation/ontologies/2025/context-ontology#>
Data namespace: contextdata: <http://www.semanticweb.org/movierecommendation/data/context/>

Estructura de un ContextSnapshot:
  contextdata:Session_{id} a context:ContextSnapshot ;
      context:snapshotID "id"^^xsd:string ;
      context:requestTimestamp "datetime"^^xsd:dateTime ;
      context:userIntent "query"^^xsd:string ;
      context:hourOfDay 20^^xsd:integer ;
      context:dayOfWeek "Wednesday"^^xsd:string ;
      context:feelsMood contextdata:Mood_{id} ;
      context:withCompanion contextdata:Social_{id} ;
      context:hasRequirement contextdata:Req_{id} .

  contextdata:Mood_{id} a context:EmotionalContext ;
      context:moodDescription "relajado"^^xsd:string ;
      context:desiredEnergyLevel "bajo"^^xsd:string .

  contextdata:Social_{id} a context:SocialContext ;
      context:companionType "amigos"^^xsd:string ;
      context:hasChildren false^^xsd:boolean .

  contextdata:Req_{id} a context:RequirementContext ;
      context:availableTime 90^^xsd:integer .

Los snapshots se inyectan dinámicamente en named graphs por sesión:
  GRAPH <http://session/{snapshot_id}> { ... }
  Y se limpian al terminar el request con DROP SILENT GRAPH.

El historial del usuario se archiva permanentemente en:
  GRAPH <http://users/{user_id}/history> { ... }
```

---

## Modelos de dominio (domain/entities/recommendation_models.py)

```python
@dataclass
class UserContext:
    mood: str | None = None              # "relaxed", "happy", etc. (inglés, del NLU)
    companion: str | None = None         # "friends", "family", etc.
    has_children: bool = False
    energy: str | None = None            # "low", "medium", "high"
    genres: list[str] = field(...)       # ["Comedy", "Drama"]
    runtime_max: int | None = None       # minutos
    exclusions: list[str] = field(...)
    confidence: float = 0.5              # 0.9 si LLM, 0.5 si keyword fallback
    raw_query: str = ""
    time_of_day: str | None = None       # "morning/afternoon/evening/night" — del reloj
    children_age_hint: str | None = None # "young"/<12, "teen"/12-17, "adult"/18+
    session_id: str | None = None        # para flujo conversacional

@dataclass
class UserProfile:
    user_id: str
    genre_weights: dict[str, float] = field(...)   # con decay temporal
    dominant_mood: str | None = None
    dominant_companion: str | None = None
    snapshot_count: int = 0              # snapshots en Fuseki history
    is_cold_start: bool = True
    dominant_time_of_day: str | None = None
    children_age_hint: str | None = None

    @classmethod
    def cold_start(cls, user_id: str) -> UserProfile: ...

@dataclass
class Movie:
    uri: str
    title: str
    genre: str | None = None
    runtime: int | None = None
    rating: float | None = None
    poster_url: str | None = None
    release_year: str | None = None
    compatibility_score: float = 0.0
    semantic_scores: dict[str, float] = field(...)  # moodMatch, socialMatch, etc.
    kid_friendly: bool | None = None

    @classmethod
    def from_fuseki_row(cls, row: dict) -> Movie: ...
    def to_response_dict(self) -> dict: ...

@dataclass
class RecommendationResult:
    movies: list[Movie]
    strategy_used: str         # "ontology_full", "ontology_mood_only", "broad", etc.
    sparql_executed: str
    context: UserContext
    explanation: str = ""
    execution_ms: int = 0
    debug: dict = field(...)

@dataclass
class ConversationTurn:
    role: str                  # "user" o "assistant"
    content: str
    context: UserContext | None = None
    timestamp: datetime = field(...)

@dataclass
class ConversationSession:
    session_id: str
    user_id: str
    turns: list[ConversationTurn] = field(...)
    accumulated_context: UserContext | None = None
    created_at: datetime = field(...)
    last_updated: datetime = field(...)

    def add_turn(self, turn: ConversationTurn) -> None: ...

    @property
    def user_turns(self) -> list[ConversationTurn]: ...

    @property
    def last_user_query(self) -> str | None: ...
```

---

## Ports definidos (domain/ports/)

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

## Mapeos NLU → español (para SPARQL)

```python
MOOD_ES_MAP = {
    "happy": "feliz", "relaxed": "relajado", "stressed": "estresado",
    "sad": "triste", "anxious": "ansioso", "excited": "emocionado",
    "bored": "aburrido", "curious": "curioso", "romantic": "romantico",
    "nostalgic": "nostalgico", "adventurous": "aventurero",
    "nervous": "nervioso", "neutral": None,
}

COMPANION_ES_MAP = {
    "alone": "solo", "partner": "pareja", "family": "familia",
    "friends": "amigos", "family_with_kids": "familia con niños",
}
# Regla especial: si companion="family" y has_children=True → "familia con niños"

ENERGY_ES_MAP = {
    "low": "bajo", "medium": "medio", "high": "alto",
    "relaxed": "bajo", "excited": "alto",
}

TIME_OF_DAY_MAP = {  # inferido desde hora del servidor, nunca del LLM
    range(6, 12): "morning",
    range(12, 18): "afternoon",
    range(18, 23): "evening",
    # 23-5: "night"
}
```

---

## Pipeline de recomendación (cómo funciona)

```
Query del usuario
    ↓
GeminiRecommendationLlmAdapter.extract_query_context()
    → produce UserContext (mood, companion, genres, runtime_max, etc.)
    → fallback a keyword parser si Gemini falla
    ↓
build_strategy(ctx, profile) → list[(name, sparql)]
    Orden de intentos:
    1. "ontology_full"        bridge:compatibleMood + companion + energy + isKidFriendly
    2. "ontology_mood_companion"  mood + companion, sin energy
    3. "ontology_mood_only"   solo mood
    4. "ontology_companion_only"  solo companion
    5. "genre_filter"         FILTER(?genreName IN (...))  ← fallback clásico
    6. "broad"                sin filtros, ordenado por rating
    ↓
GraphExecutor.run_strategy(attempts, min_results=5)
    → ejecuta en orden hasta tener >= 5 resultados
    → retorna (rows, strategy_used)
    ↓
Scorer.score_and_select(candidates, ctx, profile, n=5)
    → Movie.from_fuseki_row(row) por cada candidato
    → score = 0.40*rating + 0.30*semantic_overall + 0.15*freshness + 0.15*novelty
    → MMR selection para diversidad (lambda=0.7)
    ↓
GeminiRecommendationLlmAdapter.generate_recommendation_explanation()
    → prompt diferenciado por query_type: "general", "mood_driven", "social",
      "cold_start", "activity"
    ↓
RecommendationResult(movies, strategy_used, context, explanation)
    ↓
Archivar UserContext en Fuseki named graph permanente del usuario
Limpiar named graph temporal de sesión
```

---

## Children age hint — lógica de filtrado

El campo `children_age_hint` en `UserContext` controla cómo se aplica `isKidFriendly`:

- `"young"` (< 12 años): filtro DURO — `?movie bridge:isKidFriendly true .`
- `None` (ambiguo): señal SOFT — sube score pero no excluye películas
- `"teen"` (12-17): sin filtro de kidFriendly, pero evita NC-17
- `"adult"` (18+): sin restricción de contenido

El NLU extrae esto del texto:
- "mis hijos pequeños" → young
- "mis hijos" (sin más contexto) → None
- "mis hijos adolescentes" → teen
- "mis hijos universitarios" → adult

---

## Flujo conversacional (Fase 2.5)

El frontend envía el historial completo de mensajes al backend:

```json
POST /api/v1/recommendation/chat
{
  "session_id": "sess_abc123",
  "messages": [
    {"role": "user", "content": "algo de terror"},
    {"role": "assistant", "content": "Te recomiendo..."},
    {"role": "user", "content": "pero que no sea muy larga"}
  ],
  "user_id": "user_xyz"
}
```

El backend:
1. Extrae `UserContext` del último mensaje del usuario
2. Hace `merge_contexts(accumulated_context, new_context)` acumulando el historial
3. Usa el contexto acumulado para la estrategia SPARQL

Reglas de merge:
- Campos no-None del nuevo sobrescriben al anterior
- Campos None en el nuevo preservan el valor anterior
- `exclusions` se acumulan (unión)
- `time_of_day` siempre del turno actual (reloj)
- `confidence` aumenta con cada turn (max 0.95)

---

## Estado actual del plan de fases

| Fase | Descripción | Estado |
|------|-------------|--------|
| 1 | Modelos de dominio (`UserContext`, `UserProfile`, `Movie`, `RecommendationResult`, `ConversationTurn`, `ConversationSession`) | ✅ Completo |
| 1.5 | Datos — `bridge_data_v2.ttl` con predicados individuales + `compatibleTimeOfDay` + `isKidFriendly` por certificación | 🔄 Bridge generado, pendiente de recargar en Fuseki |
| 2 | Core components: `query_strategy.py`, `scorer.py`, `profile_service.py`, `connection_explorer.py`, actualizar `fuseki_client.py` | ⏳ Pendiente |
| 2.5 | Flujo conversacional: `conversation_context.py`, endpoint `/chat`, merge de contextos | ⏳ Pendiente |
| 3 | `RecommendationUseCase` limpio usando los nuevos componentes (< 100 líneas) | ⏳ Pendiente |
| 4 | Endpoints explorador de conexiones entre películas | ⏳ Pendiente |
| 5 | Métricas: ILD, precisión semántica, cold start threshold | ⏳ Pendiente |

---

## Archivos que ya existen y funcionan (no tocar)

- `app/core/fuseki_client.py` — execute_select_query, execute_update_query, copy_graph_to_user_history, get_user_context_history, user_history_graph_exists
- `app/core/ontology_query_builder.py` — build_cross_ontology_sparql, inject/delete_context_snapshot, translate_*
- `app/adapters/llm/gemini_recommendation_llm_adapter.py` — GeminiRecommendationLlmAdapter (extract_query_context, generate_recommendation_explanation)
- `app/adapters/repositories/` — todos los repositorios MongoDB
- `app/api/v1/endpoints/` — todos los endpoints existentes
- `app/application/use_cases/recommendation/recommendation_use_case.py` — funciona, se limpiará en Fase 3

---

## Lo que se está construyendo en Fase 2

Cuatro archivos nuevos en `app/core/`:

### query_strategy.py
```python
def build_strategy(ctx: UserContext, profile: UserProfile) -> list[tuple[str, str]]:
    """Returns ordered (name, sparql) list to try until min_results reached."""
    # Cold start → centralidad de red
    # Si hay mood + companion → ontology_full primero
    # Fallback progresivo hasta broad
```

### scorer.py
```python
def score_and_select(
    candidates: list[dict],
    ctx: UserContext,
    profile: UserProfile,
    n: int = 5,
) -> list[Movie]:
    """Score candidates and select top-n with MMR diversity."""

def _compute_score(movie: Movie, ctx: UserContext, profile: UserProfile, rank: int) -> float:
    # semantic = movie.semantic_scores.get("overallCompatibility")
    # rating = _norm_rating(movie.rating)
    # fresh = _freshness(movie.release_year)
    # novel = _novelty(movie, profile)
    # if semantic: return 0.40*rating + 0.30*semantic + 0.15*fresh + 0.15*novel
    # else: return rating + bonuses
```

### profile_service.py
```python
class ProfileService:
    def get(self, user_id: str) -> UserProfile:
        # Cache TTL 3 min
        # Construir desde favorites + history con decay temporal
        # Leer dominant_mood/companion desde Fuseki history si existe

    def archive_context(self, user_id: str, ctx: UserContext) -> None:
        # Escribir snapshot a GRAPH <http://users/{user_id}/history>
        # Limpiar cache del usuario
```

### connection_explorer.py
```python
class ConnectionExplorer:
    def find_path(self, title_a: str, title_b: str) -> ConnectionPath:
        """BFS — camino más corto entre dos películas en el grafo."""
        # Salto 1: ¿comparten director?
        # Salto 2: ¿comparten género + actor?
        # Salto 3: ¿comparten tema/tono?

    def get_neighborhood(self, title: str, depth: int = 2) -> NetworkGraph:
        """Películas conectadas a N saltos."""

    def get_centrality_ranking(self, genre: str | None = None) -> list[Movie]:
        """Películas más centrales (ya existe en cold start, exponer como endpoint)."""
```

---

## Variables de entorno (.env)

```
GEMINI_API_KEY=AIzaSyDnL5Y-LVjzIeOqtd_IraqA3KORyP0DcDI
GEMINI_MODEL=gemini-2.5-flash
FUSEKI_URL=http://localhost:3030
FUSEKI_DATASET=Cine
FUSEKI_USER=Admin
FUSEKI_PASSWORD=Admin
MONGO_URI=mongodb+srv://luishernandezsolis_db_user:V59XBERr4aTPfigR@cluster0.pjqxsja.mongodb.net/movie-graph-rag?retryWrites=true&w=majority&ssl=true
JWT_SECRET=qA0aGfGs6UGIp1pq9LpZkGDS7vJlVQ2pHS732egMkZ7
```

---

## Convenciones de código

- Python 3.12, `from __future__ import annotations`
- Dataclasses para modelos de dominio (no Pydantic en domain/)
- Pydantic solo en api/schemas/ y para modelos de BD
- Todos los métodos que llaman a Fuseki u otros servicios externos: `try/except Exception` con fallback seguro, nunca propagan excepciones al pipeline de recomendación
- Type hints completos en todos los métodos públicos
- Sin logging excesivo — solo errores y eventos importantes
- Sin dependencias nuevas de pip a menos que sean estrictamente necesarias
