# Diagramas Técnicos — Trabajo de Grado

---

## 1. Arquitectura General del Sistema

```mermaid
graph TB
    subgraph CLIENTE["Cliente — Next.js / React"]
        UI_HOME["Home"]
        UI_CHAT["Chat"]
        UI_SEARCH["Busqueda"]
        UI_TOPO["Topologia"]
    end

    subgraph BACKEND["Backend — FastAPI"]
        API["API REST /api/v1/"]
        UC_REC["Caso de Uso:<br/>Recomendacion"]
        UC_CHAT["Caso de Uso:<br/>Chat"]
        SCORER["Scorer"]
        BUILDER["OntologyQueryBuilder"]
    end

    subgraph LLM["LLM — Groq Cloud"]
        LLAMA["Llama 3.3 70B"]
    end

    subgraph STORES["Almacenamiento"]
        FUSEKI["Apache Jena Fuseki<br/>SPARQL 1.1 / TDB2"]
        MONGO["MongoDB<br/>usuarios, historial, favoritos"]
    end

    subgraph ONTOLOGIAS["Ontologias OWL 2 DL"]
        ONT_MOV["movie-ontology"]
        ONT_CTX["context-ontology"]
        ONT_BRI["bridge-ontology"]
    end

    CLIENTE -- "HTTP / JSON" --> API
    API --> UC_REC
    API --> UC_CHAT
    UC_REC --> LLAMA
    UC_REC --> BUILDER
    UC_REC --> SCORER
    BUILDER -- "SPARQL cross-ontology" --> FUSEKI
    FUSEKI --- ONT_MOV
    FUSEKI --- ONT_CTX
    FUSEKI --- ONT_BRI
    UC_REC --> MONGO
    UC_CHAT --> MONGO
```

---

## 2. Pipeline de Recomendacion (5 Pasos)

```mermaid
flowchart TD
    START(["Consulta del usuario"])

    subgraph P1["Paso 1 — Extracción de Contexto"]
        P1_LLM["LLM extrae QueryContext<br/>mood, companion, genres,<br/>hasChildren, availableTime"]
    end

    subgraph P2["Paso 2 — Generación SPARQL"]
        P2_BUILD["OntologyQueryBuilder<br/>traduce contexto a clases OWL"]
        P2_LLM["LLM genera consulta<br/>cross-ontology (3 prefijos)"]
        P2_BUILD --> P2_LLM
    end

    subgraph P3["Paso 3 — Ejecución en Fuseki"]
        P3_HTTP["HTTP POST a Fuseki<br/>/movies/query"]
        P3_RESP["JSON Bindings<br/>20 candidatos"]
        P3_HTTP --> P3_RESP
    end

    subgraph P4["Paso 4 — Scoring"]
        P4_SCORE["Pesos: 40% mood<br/>30% social<br/>20% logistica<br/>10% calidad"]
        P4_OUT["Top-5 peliculas<br/>compatibilityScore 0-1"]
        P4_SCORE --> P4_OUT
    end

    subgraph P5["Paso 5 — Narrativa"]
        P5_LLM["LLM genera explicacion<br/>en lenguaje natural"]
    end

    subgraph FIN["Persistencia y Respuesta"]
        RESP["RecommendationResponse<br/>{contextExtracted, sparqlQuery,<br/>moviesWithScores, explanation}"]
    end

    START --> P1 --> P2 --> P3 --> P4 --> P5 --> FIN
```

---

## 3. Pipeline ETL de Construccion de Ontologias

```mermaid
flowchart LR
    subgraph FUENTES["Fuentes"]
        ML["MovieLens CSV"]
        TMDB_API["TMDb API"]
        OMDB_API["OMDb API"]
    end

    subgraph ETL["Paso 1 — Carga"]
        DL["data_loader.py<br/>normalizacion y dedup"]
    end

    subgraph ENRICH["Paso 2 — Enriquecimiento"]
        ENR["enrichment.py<br/>elenco, generos, certificacion"]
    end

    subgraph RDF_GEN["Paso 3 — Generacion RDF"]
        RDF_MOV["rdf_generator.py<br/>movies_data.ttl (~159K tripletas)"]
        RDF_BRI["rdf_bridge_generator.py<br/>bridge_data.ttl (~19K tripletas)"]
    end

    subgraph OWL_FILES["TBox"]
        OWL_M["movie-ontology.ttl"]
        OWL_C["context-ontology.ttl"]
        OWL_B["bridge-ontology.ttl<br/>+ reglas SWRL"]
    end

    subgraph CARGA["Paso 4 — Fuseki"]
        PIPE["pipeline.py"]
        G1["grafo: movie-ontology"]
        G2["grafo: context-ontology"]
        G3["grafo: bridge-ontology"]
    end

    ML --> DL
    TMDB_API --> ENR
    OMDB_API --> ENR
    DL --> ENR
    ENR --> RDF_MOV
    ENR --> RDF_BRI
    OWL_M --> PIPE
    OWL_C --> PIPE
    OWL_B --> PIPE
    RDF_MOV --> PIPE
    RDF_BRI --> PIPE
    PIPE --> G1
    PIPE --> G2
    PIPE --> G3
```

---

## 4. Estructura Modular de Ontologias

```mermaid
classDiagram
    namespace MovieOntology {
        class Movie {
            +title: string
            +runtime: integer
            +releaseDate: date
            +voteAverage: float
            +tmdbId: integer
        }
        class Person {
            +name: string
        }
        class Director
        class Actor
        class Genre {
            +genreName: string
        }
        class ProductionCompany
        class Collection
        class Tone
        class Theme
    }

    namespace ContextOntology {
        class ContextSnapshot {
            +hourOfDay: integer
            +dayOfWeek: string
            +userIntent: string
        }
        class SocialContext {
            +companionType: string
            +hasChildren: boolean
        }
        class EmotionalContext {
            +moodDescription: string
            +desiredEnergyLevel: string
        }
        class RequirementContext {
            +availableTime: integer
            +excludedGenre: string
        }
    }

    namespace BridgeOntology {
        class RecommendationLink {
            +compatibilityScore: float
            +moodMatchScore: float
            +socialMatchScore: float
            +isKidFriendly: boolean
        }
    }

    Person <|-- Director
    Person <|-- Actor
    Movie --> Genre : hasMainGenre
    Movie --> Director : hasDirector
    Movie --> Actor : hasActor
    Movie --> Collection : belongsToCollection
    Movie --> Tone : hasTone
    Movie --> Theme : hasTheme

    ContextSnapshot --> SocialContext : withCompanion
    ContextSnapshot --> EmotionalContext : feelsMood
    ContextSnapshot --> RequirementContext : hasRequirement

    Movie .. RecommendationLink
    RecommendationLink .. ContextSnapshot
```

---

## 5. Flujo Conversacional Multi-turno

```mermaid
sequenceDiagram
    actor U as Usuario
    participant FE as Frontend
    participant API as Backend
    participant MONGO as MongoDB
    participant LLM as LLM
    participant FUSE as Fuseki

    Note over U,FUSE: Turno 1

    U->>FE: consulta inicial
    FE->>API: POST /chat {query, session_id: null}
    API->>MONGO: crear sesion {turn: 1, history: []}
    API->>LLM: extraer contexto
    LLM-->>API: QueryContext
    API->>FUSE: SPARQL con contexto
    FUSE-->>API: candidatos
    API->>LLM: generar narrativa
    API->>MONGO: guardar turno 1
    API-->>FE: movies, explanation, session_id

    Note over U,FUSE: Turno 2 — refinamiento

    U->>FE: refinamiento
    FE->>API: POST /chat {query, session_id, history:[t1]}
    API->>MONGO: recuperar historial
    API->>LLM: contexto + historial previo
    LLM-->>API: QueryContext refinado
    API->>FUSE: SPARQL con filtros adicionales
    FUSE-->>API: candidatos filtrados
    API->>LLM: narrativa referenciando turno anterior
    API->>MONGO: guardar turno 2
    API-->>FE: movies, explanation, turn: 2
```

---

## 6. Estrategias de Consulta SPARQL

```mermaid
flowchart TD
    START(["Solicitud de recomendacion"])
    CHECK{"Tiene historial<br/>el usuario?"}

    subgraph WARM["Warm Start"]
        W1["mood_driven<br/>emocion + generos"]
        W2{">= 5 resultados?"}
        W3["social<br/>compania + restricciones"]
        W4{">= 5 resultados?"}
        W5["genre_filter<br/>generos explicitos"]
        W6{">= 5 resultados?"}
        W7["broad<br/>sin filtros, rating >= 7.0"]
        W1 --> W2
        W2 -- No --> W3 --> W4
        W4 -- No --> W5 --> W6
        W6 -- No --> W7
        W2 -- Si --> SCORE
        W4 -- Si --> SCORE
        W6 -- Si --> SCORE
        W7 --> SCORE
    end

    subgraph COLD["Cold Start"]
        C1["Consultas paralelas<br/>por multiples generos"]
        C2["Agrega ~40 candidatos unicos"]
        C3["MMR lambda=0.45<br/>diversidad sobre relevancia"]
        C1 --> C2 --> C3 --> SCORE
    end

    subgraph SCORE["Scoring final"]
        S1["Pesos mood/social/logistica/calidad"]
        S2["Top-5 por compatibilityScore"]
        S1 --> S2
    end

    START --> CHECK
    CHECK -- Si --> WARM
    CHECK -- No --> COLD
```

---

## 7. Diagrama de Clases del Dominio

```mermaid
classDiagram
    class QueryContext {
        +mood: str
        +companion: str
        +genres: List~str~
        +hasChildren: bool
        +availableTime: int
        +excludedGenres: List~str~
    }

    class Movie {
        +uri: str
        +title: str
        +runtime: int
        +genres: List~str~
        +voteAverage: float
        +compatibilityScore: float
        +moodMatchScore: float
        +socialMatchScore: float
        +isKidFriendly: bool
    }

    class RecommendationResponse {
        +query: str
        +contextExtracted: QueryContext
        +sparqlQuery: str
        +moviesWithScores: List~Movie~
        +explanation: str
        +executionTimeMs: int
        +strategyUsed: str
    }

    class ChatSession {
        +sessionId: str
        +userId: str
        +turns: List~ChatTurn~
    }

    class ChatTurn {
        +turnNumber: int
        +userQuery: str
        +extractedContext: QueryContext
        +moviesReturned: List~Movie~
        +explanation: str
    }

    RecommendationResponse --> QueryContext : contextExtracted
    RecommendationResponse --> Movie : moviesWithScores
    ChatSession --> ChatTurn : turns
    ChatTurn --> QueryContext : extractedContext
    ChatTurn --> Movie : moviesReturned
```

---

## 8. Arquitectura Hexagonal del Backend

```mermaid
flowchart LR
    HTTP["Cliente HTTP"]

    subgraph HEXAGONO["Nucleo — FastAPI"]
        subgraph CTRL["Controladores"]
            REC_CTRL["RecommendationController"]
            CHAT_CTRL["ChatController"]
            AUTH_CTRL["AuthController"]
        end

        subgraph UC["Casos de Uso"]
            UC_REC2["RecommendationUseCase"]
            UC_CHAT2["ChatUseCase"]
        end

        subgraph DOM["Dominio"]
            E["Movie<br/>QueryContext<br/>RecommendationResponse"]
        end

        subgraph PORTS["Puertos de salida"]
            P_LLM["ILLMClient"]
            P_GRAPH["IGraphPort"]
            P_HIST["IHistoryRepository"]
            P_FAV["IFavoritesRepository"]
        end
    end

    subgraph ADAPT["Adaptadores"]
        A_GROQ["GroqLLMAdapter"]
        A_FUSEKI["FusekiGraphAdapter"]
        A_MONGO_H["MongoHistoryRepo"]
        A_MONGO_F["MongoFavoritesRepo"]
    end

    subgraph EXT["Servicios externos"]
        GROQ_SRV["Groq Cloud API"]
        FUSEKI_SRV["Fuseki :3030"]
        MONGO_SRV["MongoDB :27017"]
    end

    HTTP --> REC_CTRL --> UC_REC2 --> DOM
    HTTP --> CHAT_CTRL --> UC_CHAT2 --> DOM
    UC_REC2 --> P_LLM --> A_GROQ --> GROQ_SRV
    UC_REC2 --> P_GRAPH --> A_FUSEKI --> FUSEKI_SRV
    UC_REC2 --> P_HIST --> A_MONGO_H --> MONGO_SRV
    UC_REC2 --> P_FAV --> A_MONGO_F --> MONGO_SRV
    UC_REC2 -. "invoca execute_select_query()<br/>directamente en algunos casos" .-> A_FUSEKI

    NOTE["Arquitectura hexagonal con capas de dominio, aplicación, adaptadores e infraestructura, siguiendo el patrón Ports & Adapters con algunas concesiones pragmáticas en la capa de orquestación"]
    style NOTE fill:#fffbe6,stroke:#d4a017,color:#333
```

---

## 9. Flujo de Autenticacion JWT

```mermaid
sequenceDiagram
    actor U as Usuario
    participant FE as Frontend
    participant API as Backend
    participant MONGO as MongoDB

    Note over U,MONGO: Registro

    U->>FE: email + password
    FE->>API: POST /auth/register
    API->>API: bcrypt.hash(password)
    API->>MONGO: insertar usuario
    API->>API: JWT.sign(user_id, 1d)
    API-->>FE: access_token

    Note over U,MONGO: Login

    U->>FE: email + password
    FE->>API: POST /auth/login
    API->>MONGO: buscar por email
    API->>API: bcrypt.verify(password, hash)
    alt Valido
        API-->>FE: access_token
    else Invalido
        API-->>FE: 401 Unauthorized
    end

    Note over U,MONGO: Acceso protegido

    FE->>API: GET /users/favorites — Bearer token
    API->>API: JWT.verify(token)
    alt Token valido
        API->>MONGO: buscar favoritos
        API-->>FE: favorites[]
    else Token invalido
        API-->>FE: 401 — redirigir a /login
    end
```

---

## 10. Consulta Cross-Ontology SPARQL

```mermaid
flowchart TD
    subgraph DISEÑO["Diseno — Metodologia NeOn"]
        D1["Especificacion"] --> D2["Conceptualizacion"]
        D2 --> D3["Formalizacion OWL 2 DL"]
        D3 --> D4["Implementacion .ttl / .owl"]
        D4 --> D5["Evaluacion OOPS! / HermiT"]
    end

    subgraph CARGA["Carga en Fuseki"]
        L1["HTTP PUT/POST /upload"]
        L2["3 grafos nombrados en TDB2"]
        L1 --> L2
    end

    subgraph CONSULTA["Consulta SPARQL Cross-Ontology"]
        Q1["PREFIX mo: movie-ontology<br/>PREFIX co: context-ontology<br/>PREFIX bo: bridge-ontology"]
        Q2["Capa dominio<br/>?movie a mo:Movie<br/>mo:hasTitle, mo:runtime"]
        Q3["Capa puente<br/>bo:companionToGenre<br/>co:companionType 'family'"]
        Q4["Filtros de contexto<br/>runtime <= maxRuntime<br/>rating >= 7.0"]
        Q5["ORDER BY DESC rating<br/>LIMIT 20"]
        Q1 --> Q2 --> Q3 --> Q4 --> Q5
    end

    DISEÑO --> CARGA --> CONSULTA
    CONSULTA --> SCORER(["Scorer — Top-5"])
```

---

## 11. Componentes Frontend (Atomic Design)

```mermaid
graph BT
    subgraph ATOMS["Atomos — components/ui/"]
        BTN["Button"]
        BADGE["Badge"]
        INPUT["Input"]
        SKEL["Skeleton"]
    end

    subgraph MOLECULES["Moleculas — components/molecules/"]
        SCOREBAR["ScoreBar"]
        CTX_CHIPS["ContextChips"]
        WHY_CARD["WhyCard"]
    end

    subgraph ORGANISMS["Organismos — components/organisms/"]
        NAVBAR["Navbar"]
        HERO["HeroSection"]
        MOVIE_CARD["MovieCard"]
        CAROUSEL["RecommendationCarousel"]
        CHAT_MOD["ChatModule"]
        CONN_GRAPH["ConnectionsGraph"]
        TOPO_PROF["TopologicalProfile"]
        FILTER_SB["FilterSidebar"]
    end

    subgraph PAGES["Paginas — app/"]
        P_HOME["/ Home"]
        P_CHAT["/chat"]
        P_SEARCH["/search"]
        P_CONN["/connections"]
        P_TOPO["/topology"]
    end

    BTN --> MOVIE_CARD
    BADGE --> CTX_CHIPS
    INPUT --> FILTER_SB
    SKEL --> CAROUSEL

    SCOREBAR --> MOVIE_CARD
    CTX_CHIPS --> CHAT_MOD
    WHY_CARD --> CHAT_MOD

    MOVIE_CARD --> CAROUSEL
    CAROUSEL --> P_HOME
    HERO --> P_HOME
    CHAT_MOD --> P_CHAT
    FILTER_SB --> P_SEARCH
    MOVIE_CARD --> P_SEARCH
    CONN_GRAPH --> P_CONN
    TOPO_PROF --> P_TOPO
```

---

## 12. Despliegue (Docker Compose)

```mermaid
graph TB
    INTERNET(["Usuario"]) --> NGINX["nginx :80/:443"]

    subgraph DOCKER["Docker Compose Network"]
        subgraph C_FRONT["frontend"]
            NEXT["Next.js :3000"]
        end

        subgraph C_API["fastapi-app"]
            API2["FastAPI :8000"]
        end

        subgraph C_FUSEKI["fuseki"]
            FUS["Fuseki :3030<br/>JVM max 2GB"]
            VOL_F[("fuseki_data")]
        end

        subgraph C_MONGO["mongodb"]
            MDB["MongoDB :27017"]
            VOL_M[("mongo_data")]
        end
    end

    subgraph EXT["Externos"]
        GROQ3["Groq Cloud API"]
        TMDB3["TMDb API"]
    end

    NGINX --> NEXT --> API2
    API2 -- "depends_on healthcheck" --> FUS
    API2 -- "depends_on healthcheck" --> MDB
    API2 --> GROQ3
    FUS --- VOL_F
    MDB --- VOL_M
```

---

> **Exportar a PNG para LaTeX:**
> ```bash
> npm install -g @mermaid-js/mermaid-cli
> mmdc -i DIAGRAMAS_TESIS.md -o ./diagrams/ -t neutral -b white
> ```
