# CineSemantico — Arquitectura Completa, Teoría y Propuestas de Redes Complejas

> **Trabajo de Grado** — Luis F. Hernández · Universidad del Valle · 2026
> Motor de recomendación de películas basado en Ontologías + GraphRAG + LLM

---

## Tabla de Contenidos

1. [Visión General del Sistema](#1-visión-general-del-sistema)
2. [Arquitectura de las Ontologías](#2-arquitectura-de-las-ontologías)
3. [Pipeline de Datos: De MovieLens al Grafo de Conocimiento](#3-pipeline-de-datos-de-movielens-al-grafo-de-conocimiento)
4. [GraphRAG: Retrieval-Augmented Generation sobre Grafos](#4-graphrag-retrieval-augmented-generation-sobre-grafos)
5. [Integración con LLM (Large Language Model)](#5-integración-con-llm-large-language-model)
6. [Pipeline de Recomendación: Los 5 Pasos](#6-pipeline-de-recomendación-los-5-pasos)
7. [Funcionalidades Actuales del Frontend](#7-funcionalidades-actuales-del-frontend)
8. [Teoría de Redes Complejas: Oportunidades de Integración](#8-teoría-de-redes-complejas-oportunidades-de-integración)
9. [Nuevas Funcionalidades Propuestas](#9-nuevas-funcionalidades-propuestas)
10. [Ventajas frente a Sistemas de Recomendación Tradicionales](#10-ventajas-frente-a-sistemas-de-recomendación-tradicionales)
11. [Roadmap de Implementación](#11-roadmap-de-implementación)

---

## 1. Visión General del Sistema

CineSemantico es un sistema de recomendación de películas que combina tres pilares tecnológicos:

```
┌─────────────────────────────────────────────────────────────────┐
│                    CineSemantico Architecture                   │
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────────┐  │
│  │   Frontend    │   │   Backend    │   │  Knowledge Graph   │  │
│  │  (Next.js)   │◄─►│  (NestJS)    │◄─►│  (Apache Fuseki)   │  │
│  └──────────────┘   └──────┬───────┘   └────────────────────┘  │
│                            │                                    │
│                     ┌──────┴───────┐                            │
│                     │   LLM (Groq) │                            │
│                     │  Llama 3.3   │                            │
│                     └──────────────┘                            │
│                                                                 │
│  ┌──────────────┐                                               │
│  │   MongoDB     │  ← Usuarios + Historial de consultas        │
│  └──────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
```

### Stack Tecnológico

| Componente | Tecnología | Propósito |
|---|---|---|
| **Frontend** | Next.js 16 + React 19 + Tailwind CSS 4 + Radix UI | Interfaz de usuario SPA con tema oscuro |
| **Backend** | NestJS 11 + TypeScript | API REST con Swagger, módulos desacoplados |
| **Grafo** | Apache Jena Fuseki + SPARQL 1.1 | Triple store para ontologías OWL/RDF |
| **LLM** | Groq Cloud + Llama 3.3 70B (via LangChain) | Extracción semántica, generación SPARQL, scoring, narrativa |
| **Base de datos** | MongoDB (Mongoose) | Usuarios, autenticación (JWT + bcrypt), historial |
| **Ontologías** | OWL 2 DL + RDF Turtle | 3 ontologías: Movie, Context, Bridge |
| **Pipeline** | Python + rdflib + KeyBERT + APIs TMDb/OMDb | ETL, enriquecimiento, inferencia NLP, generación RDF |

---

## 2. Arquitectura de las Ontologías

El sistema emplea una **arquitectura de ontologías en tres capas** diseñada para separar el dominio del cine, el contexto del usuario y la lógica de integración.

### 2.1 Capa 1: Movie Ontology (TBox del Dominio)

**Namespace:** `http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#`

Define el vocabulario completo del dominio cinematográfico:

```
Entity (raíz)
├── Movie
│   ├── FeatureFilm        ← Largometraje
│   ├── Documentary         ← Documental
│   ├── ShortFilm           ← Cortometraje
│   └── AnimatedFilm        ← Película animada
├── Person
│   ├── Director
│   ├── Actor
│   ├── Producer
│   ├── Screenwriter
│   ├── Cinematographer
│   ├── Composer
│   └── Editor
├── Attribute
│   ├── Genre
│   │   ├── MainGenre       ← Acción, Comedia, Drama...
│   │   └── Subgenre        ← Neo-noir, Space Opera...
│   ├── Keyword
│   └── NarrativeElement
│       ├── Theme            ← Redención, Amor prohibido...
│       ├── Tone             ← Oscuro, Ligero, Épico...
│       └── PlotStructure    ← Lineal, No-lineal, Marco...
├── Role
│   ├── ActingRole
│   │   ├── LeadRole
│   │   ├── SupportingRole
│   │   └── CameoRole
│   └── CreativeRole
├── ProductionCompany
├── Certification           ← G, PG, PG-13, R, NC-17
├── Award / AwardParticipation
├── Rating                  ← IMDb, Metacritic, RottenTomatoes
└── MovieCluster            ← Agrupación por grafo (Louvain/Leiden)
```

**Propiedades clave:**
- `movie:hasTitle`, `movie:runtime`, `movie:releaseDate`
- `movie:hasMainGenre` → instancias como `genre:Action`, `genre:Comedy`
- `movie:hasDirector`, `movie:hasActor` → instancias de `Person`
- `movie:hasAverageRating`, `movie:hasIMDbRating` (xsd:float)
- `movie:hasTone`, `movie:hasTheme`, `movie:hasPlotStructure`
- `movie:hasPlotSummary` (xsd:string)

**Alineamientos externos:** `schema:Movie`, `dbo:Film`, `schema:Person`, `foaf:Person`

### 2.2 Capa 2: Context Ontology (Modelado de Interacción)

**Namespace:** `http://www.semanticweb.org/movierecommendation/ontologies/2025/context-ontology#`

Esta ontología modela cada interacción del usuario como un **snapshot contextual multidimensional**:

```
┌────────────────────────────────────────────────────────────┐
│                    ContextSnapshot                          │
│  (nodo central de cada interacción)                        │
│                                                            │
│  • snapshotID        • requestTimestamp                    │
│  • dayOfWeek         • hourOfDay                           │
│  • userIntent                                              │
│                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │SocialContext  │  │EmotionalCtx  │  │RequirementCtx   │  │
│  │              │  │              │  │                 │  │
│  │companionType │  │moodDescrip.  │  │availableTime    │  │
│  │hasChildren   │  │energyLevel   │  │excludedGenre    │  │
│  │groupSize     │  │moodIntensity │  │negativeConstr.  │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
│                                                            │
│  ┌──────────────┐                                          │
│  │    User       │  ← Perfil persistente                  │
│  │  userID       │                                         │
│  │  userName     │                                         │
│  └──────────────┘                                          │
└────────────────────────────────────────────────────────────┘
```

**Vocabulario Controlado (valores normalizados):**

| Dimensión | Valores |
|---|---|
| **Compañía** | `solo`, `pareja`, `familia`, `familia con niños`, `amigos`, `compañeros de trabajo`, `grupo grande` |
| **Energía** | `bajo`, `medio`, `alto` |
| **Mood** | `feliz`, `alegre`, `relajado`, `romántico`, `aventurero`, `curioso`, `estresado`, `triste`, `aburrido`, `nostálgico`, `reflexivo`, `social`, `contemplativo` |

Las 5 clases están declaradas como `owl:AllDisjointClasses` y todas las relaciones tienen `owl:inverseOf`.

### 2.3 Capa 3: Bridge Ontology (Integración Semántica)

**Namespace:** `http://www.semanticweb.org/movierecommendation/ontologies/2025/bridge-ontology#`

La ontología puente conecta **películas ↔ contextos** mediante propiedades semánticas y scores de compatibilidad:

**Object Properties:**
| Propiedad | Dominio → Rango | Inversa |
|---|---|---|
| `isRecommendedIn` | Movie → ContextSnapshot | `recommends` |
| `satisfiesRequirement` | Movie → RequirementContext | `isSatisfiedBy` |
| `alignsWithMood` | Movie → EmotionalContext | `isAlignedWith` |
| `suitableForSocialContext` | Movie → SocialContext | `isSuitableFor` |
| `hasWatched` | User → Movie | `wasWatchedBy` |
| `hasRated` | User → Movie | `wasRatedBy` |

**Data Properties (Scoring Multidimensional):**
- `compatibilityScore` (0.0–1.0) — Score general
- `moodMatchScore` — Alineación emocional
- `socialMatchScore` — Adecuación social
- `energyMatchScore` — Coincidencia de nivel de energía
- `temporalMatchScore` — Relevancia temporal
- `requirementMatchScore` — Cumplimiento de requisitos
- `compatibleMood`, `compatibleCompanion`, `compatibleEnergyLevel` — Valores directos para matching SPARQL
- `isKidFriendly` (boolean) — Apto para niños

**Reglas SWRL:**
1. Si `runtime ≤ availableTime` → `satisfiesRequirement`
2. Si `hasChildren = true` → solo películas con certificación G/PG
3. Exclusión automática por género

### 2.4 Datos Instanciados (ABox)

| Archivo | Líneas | Contenido |
|---|---|---|
| `movies_data.ttl` | 159,568 | Películas con géneros, cast, crew, keywords, ratings (TMDb/IMDb/MovieLens), tones, themes, plot structures |
| `bridge_data.ttl` | 18,920 | Scores de compatibilidad por película, moods/companions/energy levels compatibles, flags `isKidFriendly` |
| `contexts_data.ttl` | ~200 | 4 sesiones de ejemplo con 3 usuarios de prueba |

---

## 3. Pipeline de Datos: De MovieLens al Grafo de Conocimiento

```
MovieLens CSV
     │
     ▼
┌─────────────────┐
│  1. ETL          │  data_loader.py
│  Limpieza +      │  → movies_processed.csv
│  normalización   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. Enrichment   │  enrichment.py
│  TMDb + OMDb API │  → movies_enriched.csv
│  Cast, crew,     │  (director, actores, sinopsis,
│  one-hot genres  │   compañías, países, idiomas)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  3. NLP Inference│  nlp_inference.py
│  KeyBERT +       │  → movies_nlp_enriched.csv
│  Sentiment       │  (tones, themes, plot structures,
│  Analysis        │   historical periods, movie types)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  4. RDF Gen      │  rdf_generator.py
│  Movies → TTL    │  → movies_data.ttl (159K líneas)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  5. Context Gen  │  rdf_context_generator.py
│  Contexts → TTL  │  → contexts_data.ttl
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  6. Bridge Gen   │  rdf_bridge_generator.py
│  Bridges → TTL   │  → bridge_data.ttl (19K líneas)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  7. Import       │  GraphDB / Fuseki
│  Cargar TTL      │  → Triple Store listo
└─────────────────┘
```

**Inferencia NLP (KeyBERT + Sentiment):**
- **Tone**: Se analiza la sinopsis para clasificar el tono narrativo (dark, light, epic, suspenseful, etc.)
- **Theme**: Se extraen temáticas principales (redemption, forbidden love, survival, etc.)
- **Plot Structure**: Se infiere la estructura narrativa (linear, non-linear, frame, etc.)
- **Historical Period**: Se detecta el período histórico si aplica
- **Movie Type**: Se clasifica por tipo (feature film, documentary, animated, short)

---

## 4. GraphRAG: Retrieval-Augmented Generation sobre Grafos

### 4.1 ¿Qué es GraphRAG?

GraphRAG es una extensión del paradigma RAG (Retrieval-Augmented Generation) que, en lugar de usar un vector store plano, utiliza un **grafo de conocimiento** como fuente de información estructurada. Las ventajas fundamentales son:

1. **Relaciones explícitas**: Las conexiones entre entidades (película ↔ director ↔ género ↔ tono) están modeladas como tripletas RDF, no latentes en embeddings
2. **Razonamiento multi-hop**: Se pueden navegar paths de longitud arbitraria (e.g., "películas del mismo director que comparten tone 'dark'")
3. **Explicabilidad**: Cada recomendación puede trazarse hasta las tripletas específicas que la justifican
4. **Contexto estructurado**: El contexto que recibe el LLM es semánticamente preciso, no un bloque de texto recuperado por similitud coseno

### 4.2 GraphRAG en CineSemantico

El sistema implementa GraphRAG mediante este flujo:

```
Consulta en Lenguaje Natural
         │
         ▼
┌────────────────────────┐
│  LLM: Extrae contexto  │  → RDF Turtle (tripletas)
│  semántico del usuario  │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│  LLM: Genera consulta   │  → SPARQL SELECT
│  SPARQL multi-ontología │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│  Fuseki: Ejecuta SPARQL │  → Bindings JSON
│  contra el grafo        │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│  LLM: Calcula scores    │  → Movies + compatibilityScore
│  de compatibilidad      │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│  LLM: Genera respuesta  │  → Narrativa personalizada
│  narrativa              │
└────────────────────────┘
```

El **Retrieval** ocurre directamente sobre el grafo de conocimiento mediante SPARQL, lo que permite:
- Filtrar por propiedades semánticas exactas (`movie:hasMainGenre genre:Action`)
- Aplicar restricciones lógicas (`FILTER(?runtime <= 120)`)
- Hacer UNION entre tipos de película
- Ordenar por rating, relevancia o score calculado

### 4.3 Diferencia con RAG Vectorial

| Aspecto | RAG Vectorial Tradicional | GraphRAG (CineSemantico) |
|---|---|---|
| **Almacenamiento** | Embeddings en vector DB | Tripletas RDF en triple store |
| **Retrieval** | Similitud coseno | Consultas SPARQL estructuradas |
| **Relaciones** | Implícitas en vectores | Explícitas como propiedades RDF |
| **Multi-hop** | Limitado (re-ranking) | Nativo (SPARQL paths, UNION) |
| **Explicabilidad** | Baja (chunks de texto) | Alta (tripletas + consulta SPARQL visible) |
| **Contexto del usuario** | Embedding del query | RDF contextual (social, emocional, temporal) |
| **Actualización** | Re-embed todo el corpus | INSERT/DELETE tripletas específicas |

---

## 5. Integración con LLM (Large Language Model)

### 5.1 Modelo Utilizado

**Llama 3.3 70B Versatile** via Groq Cloud (temperature: 0.1 para máxima determinismo)

LangChain actúa como orquestador con:
- `ChatGroq` — cliente del modelo
- `ChatPromptTemplate` — prompts estructurados con variables
- `StringOutputParser` — parsing de respuestas textuales
- `N3.js Parser` — parsing de RDF Turtle generado por el LLM
- `Zod` — validación de esquemas del contexto extraído

### 5.2 Las 4 Invocaciones al LLM

El sistema hace **4 llamadas al LLM** por cada consulta del usuario:

#### Invocación 1: `extractSemanticContext(query)`
- **Input**: Consulta en lenguaje natural + hora actual + día de la semana
- **Output**: Tripletas RDF Turtle con SocialContext, EmotionalContext, RequirementContext, ContextSnapshot
- **Validación**: Parsing con N3.js + validación Zod del esquema extraído
- **Ejemplo**: "Estoy con mis hijos, tengo 90 minutos" → `companionType: "familia con niños"`, `hasChildren: true`, `availableTime: 90`

#### Invocación 2: `generateSparqlQuery(query, context)`
- **Input**: Consulta + ContextSnapshot completo (serializado como JSON)
- **Output**: Consulta SPARQL SELECT con PREFIXes, FILTER, UNION, ORDER BY, LIMIT
- **Reglas**: Usa vocabulario controlado, propiedades reales del grafo, géneros en inglés
- **Ejemplo**:
```sparql
PREFIX movie: <...movie-ontology#>
SELECT DISTINCT ?title ?runtime ?genreName WHERE {
  { ?m a movie:FeatureFilm } UNION { ?m a movie:AnimatedFilm }
  ?m movie:hasTitle ?title ; movie:runtime ?runtime ; movie:hasMainGenre ?g .
  ?g movie:genreName ?genreName .
  FILTER(?runtime <= 120)
  FILTER(!CONTAINS(?genreName, "Horror"))
}
ORDER BY DESC(?averageRating) LIMIT 20
```

#### Invocación 3: `calculateCompatibilityScores(movies, context)`
- **Input**: Top 10 películas del grafo + contexto completo
- **Output**: Score 0.0–1.0 por película
- **Criterios ponderados**:
  - 40% Alineación emocional (género ↔ mood + energyLevel)
  - 30% Contexto social (adecuación para la compañía)
  - 20% Logística (runtime ≤ availableTime)
  - 10% Calidad (averageRating)

#### Invocación 4: `generateNarrativeResponse(query, moviesWithScores, context)`
- **Input**: Query + top 5 con scores + contexto
- **Output**: Texto narrativo de 150 palabras máx. recomendando 2-3 películas con justificación contextual

---

## 6. Pipeline de Recomendación: Los 5 Pasos

El `RecommendationService` orquesta el siguiente pipeline:

```
PASO 1: Extracción Semántica Enriquecida
│  LlmService.extractSemanticContext()
│  Query → RDF Turtle (tripletas de contexto)
│  → ContextSnapshot { social, emotional, requirement, temporal }
│
PASO 2: Generación de Consulta SPARQL Multi-Ontología
│  LlmService.generateSparqlQuery()
│  ContextSnapshot → SPARQL SELECT
│  Usa las 3 ontologías + vocabulario controlado
│
PASO 3: Retrieval (Ejecución contra el Grafo)
│  GraphService.executeQuery()
│  SPARQL → HTTP POST a Fuseki → JSON Bindings → Objetos JS
│  Retorna hasta 20 películas candidatas
│
PASO 4: Cálculo de Compatibility Scores
│  LlmService.calculateCompatibilityScores()
│  10 películas × 4 criterios → Score 0.0-1.0
│  Reordenamiento por compatibilidad contextual
│
PASO 5: Generación Narrativa Contextualizada
│  LlmService.generateNarrativeResponse()
│  Top 5 → Texto personalizado para el usuario
│
└── Persistencia en MongoDB (historial) + Respuesta al frontend
```

**Response completo al frontend:**
```json
{
  "query": "...",
  "contextExtracted": { "snapshotID", "socialContext", "emotionalContext", "requirementContext", ... },
  "rdfGenerated": "@prefix context: <...>\n:snapshot1 a context:ContextSnapshot ; ...",
  "sparqlQuery": "PREFIX movie: <...> SELECT ...",
  "moviesFound": 20,
  "moviesWithScores": [{ "title", "runtime", "genreName", "compatibilityScore" }],
  "explanation": "Texto narrativo personalizado...",
  "executionTimeMs": 4523
}
```

---

## 7. Funcionalidades Actuales del Frontend

### 7.1 Página Principal (`/`)
- **SearchBar**: Búsqueda de películas por título, director o género → ejecuta SPARQL con scoring por relevancia (título exacto: 200pts, mismo director: 80pts, mismo género: 40pts)
- **ContextRecommendation**: Película destacada según el momento del día
- **DiscoverySection**: Sección educativa sobre ontologías y GraphRAG
- **FeaturedMoviesSection**: Películas destacadas con rating ≥ 4.0 del grafo
- **MovieDetailsDialog**: Modal con detalles de película, rating, géneros, sinopsis
- **HistoryDialog**: Historial de consultas pasadas del usuario
- **FloatingChatButton**: Acceso rápido al chat con el asistente

### 7.2 Chat con Asistente (`/chat`)
- Interfaz conversacional tipo ChatGPT
- Prompts de sugerencia pre-definidos
- El usuario escribe en lenguaje natural → se ejecuta el pipeline completo de 5 pasos
- **AssistantBubble** muestra: explicación narrativa + tarjetas de película + RDF generado + SPARQL ejecutado + tiempo de ejecución
- **MovieRecommendationCard**: Tarjeta visual con título, género, runtime, score de compatibilidad

### 7.3 Explorador de Conexiones (`/connections`)
- Selección de 2 películas mediante autocompletado SPARQL
- Búsqueda de conexiones en el grafo: directas (1-hop) e indirectas (2-hop)
- **Tipos de conexión**: mismo director, mismo género, mismo actor
- Visualización de nodos y aristas con colores por tipo
- Path step-by-step entre ambas películas
- Consulta SPARQL visible

### 7.4 Autenticación (`/login`, `/register`)
- Registro con email + contraseña (bcrypt)
- Login con JWT (expira en 1 día)
- `ProtectedRoute` HOC para rutas autenticadas

---

## 8. Teoría de Redes Complejas: Oportunidades de Integración

El grafo de conocimiento de CineSemantico es, por naturaleza, una **red compleja** con nodos heterogéneos (películas, personas, géneros, tones, themes) y aristas semánticas tipadas. A continuación se presenta cómo cada concepto de redes complejas podría enriquecer el sistema.

### 8.1 Centralidad (Centrality Measures) .

**Teoría**: Las métricas de centralidad identifican los nodos más "importantes" en una red según diferentes criterios.

| Métrica | Aplicación en CineSemantico |
|---|---|
| **Degree Centrality** | Películas con más conexiones (más actores, más géneros, más keywords) son "hub movies" — ideales como punto de entrada para usuarios indecisos |
| **Betweenness Centrality** | Películas que actúan como puente entre clusters de género diferentes (ej: una película que conecta el cluster de Sci-Fi con el de Drama) — perfectas para "expandir horizonte" |
| **Closeness Centrality** | Películas que están semánticamente cerca de todas las demás — buenas para recomendaciones "safe" con alta probabilidad de aceptación |
| **Eigenvector Centrality** | Películas conectadas a otros nodos importantes (ej: dirigida por director influyente + actor de alto perfil + género popular) — recomendaciones "premium" |
| **PageRank** | Variante ponderada: películas a las que "apuntan" muchas entidades relevantes — ranking de influencia cinematográfica |

**Implementación potencial**: Calcular centralidades offline y almacenarlas como `movie:degreeCentrality`, `movie:betweennessCentrality` en el grafo. Usar en SPARQL como criterio de desempate o como nuevo factor en el compatibility score.

### 8.2 Detección de Comunidades (Community Detection) .

**Teoría**: Algoritmos como Louvain, Leiden o Label Propagation agrupan nodos densamente conectados en comunidades.

**Aplicación**:
- La ontología ya tiene la clase `movie:MovieCluster` preparada pero sin explotar
- **Clusters por similitud narrativa**: Películas con mismos tones + themes + plot structures formarían comunidades naturales ("cine noir contemplativo", "aventura épica familiar", "thriller psicológico no-lineal")
- **Clusters por equipo creativo**: Director + actores recurrentes forman comunidades de "filmografías interconectadas"
- **Recomendación intra-cluster**: "Te gustó X, que está en el cluster de Thriller Psicológico Europeo, aquí hay otras 5 del mismo cluster"
- **Recomendación inter-cluster**: "Para expandir tu zona de confort, podrías probar películas del cluster adyacente"

**Algoritmo sugerido**: Leiden (mejora de Louvain) sobre un grafo proyectado bipartito (películas-películas ponderado por features compartidas).

### 8.3 Distribución de Grados (Degree Distribution) .

**Teoría**: La mayoría de redes complejas reales siguen una distribución de ley de potencias (power law) — pocos nodos tienen muchas conexiones (hubs) y muchos nodos tienen pocas.

**Aplicación**:
- Verificar si el grafo de películas es **scale-free** → si lo es, los hubs (películas muy conectadas) dominan la topología
- **Anti-popularity bias**: Los sistemas de recomendación tradicionales sufren de sesgo de popularidad. Si identificamos que el grafo es scale-free, podemos intencionalmente **penalizar hubs** para promover descubrimiento de long-tail movies
- **Visualización**: Mostrar al usuario la distribución de grados del grafo para entender la diversidad del catálogo

### 8.4 Coeficiente de Clustering (Clustering Coefficient) .

**Teoría**: Mide qué tan conectados entre sí están los vecinos de un nodo. Un coeficiente alto indica una "camarilla" densa.

**Aplicación**:
- **Películas con alto clustering**: Sus vecinos (director, actores, género) están muy interconectados → película "mainstream" dentro de un nicho bien definido
- **Películas con bajo clustering**: Sus vecinos no se conectan entre sí → película "bridge" que cruza fronteras de nicho → ideal para recomendaciones de exploración
- **Serendipity Score**: `serendipity = (1 - clusteringCoeff) × relevance` — recomendar películas relevantes pero sorprendentes

### 8.5 Shortest Path y Distancia Semántica .

**Teoría**: El camino más corto entre dos nodos define su "distancia" en la red.

**Aplicación** (ya parcialmente implementada en `/connections`):
- **Distancia semántica entre películas**: Número mínimo de hops para ir de Película A a Película B
- **Distancia semántica entre usuario y película**: Cuántos hops separan las preferencias del usuario de una película candidata
- **Diámetro del grafo**: Entender la máxima distancia entre cualquier par de películas
- **Explicabilidad mejorada**: "Esta película está a 2 pasos de tu favorita: comparten director con Film X, que tiene el mismo tone que la recomendada"

### 8.6 Small-World Networks

**Teoría**: Redes con alto clustering y path length corto (como las redes sociales). La mayoría de pares de nodos se conectan en pocos pasos.

**Aplicación**:
- Verificar si el grafo de CineSemantico tiene propiedad small-world
- Si es así, justifica que **el explorador de conexiones siempre encontrará relaciones** en ≤ 3 hops
- **"Six Degrees of Kevin Bacon" pero para películas**: Demostrar que cualquier par de películas se conecta en muy pocos pasos a través del grafo
- **Implicación para la UI**: Garantizar al usuario que "siempre hay una conexión"

### 8.7 Redes Bipartitas y Proyecciones

**Teoría**: Un grafo bipartito tiene dos tipos de nodos (ej: películas y personas), y las aristas van solo entre tipos. Se puede proyectar a un grafo unipartito (película-película) ponderado.

**Aplicación**:
- **Proyección Película-Película**: Dos películas comparten arista si comparten ≥1 actor/director/genre → peso = número de features compartidas
- **Proyección Actor-Actor**: Dos actores se conectan si aparecen en la misma película → red de colaboración
- **Proyección Género-Género**: Dos géneros se conectan si aparecen juntos en películas → "afinidad entre géneros"
- Estas proyecciones son la base para aplicar corectamente los algoritmos de comunidades y centralidad

### 8.8 Propagación de Influencia y Difusión .

**Teoría**: Modelos como SIR/SIS simulan cómo se propaga información/influencia a través de la red.

**Aplicación**:
- **Propagación de preferencias**: Si al usuario le gustó una película, ¿hasta dónde se "propaga" esa preferencia en el grafo?
- **Influence maximization**: ¿Cuáles son las 5 películas que, si el usuario las ve, maximizan su exposición a la mayor diversidad del catálogo?
- **"Si te gustó X, inevitablemente llegarás a Y"**: Simular cascadas de recomendación

### 8.9 Modularidad (Modularity) .

**Teoría**: Métrica que mide la calidad de una partición de la red en comunidades. Alta modularidad → comunidades bien separadas.

**Aplicación**:
- Calcular la modularidad del grafo de películas para validar que la estructura ontológica captura bien las agrupaciones naturales
- **Auto-tuning de recomendaciones**: Si el grafo tiene alta modularidad, las recomendaciones intra-cluster serán precisas; si tiene baja modularidad, el sistema debería ser más arriesgado en sus recomendaciones

### 8.10 Resiliencia y Robustez de la Red 

**Teoría**: Qué pasa cuando se eliminan nodos de la red. Las redes scale-free son robustas a ataques aleatorios pero vulnerables a ataques dirigidos a hubs.

**Aplicación**:
- **A/B testing**: Simular qué pasa con la calidad de recomendación si eliminamos los 10 nodos más centrales (películas más populares) — ¿el sistema sigue funcionando?
- **Feature importance**: ¿Qué tipo de arista (género, director, actor) es más crítica para mantener la conectividad del grafo?
- **Diversificación**: Si el sistema depende mucho de hubs, implementar redundancia en las recomendaciones

---

## 9. Nuevas Funcionalidades Propuestas

Basándose en la teoría de redes complejas y las ventajas del GraphRAG, las siguientes funcionalidades demostrarían el poder único de este enfoque:

### 9.1 🔬 Análisis Topológico del Grafo (Dashboard) .

**Funcionalidad**: Panel interactivo que muestra métricas de redes complejas del grafo de conocimiento en tiempo real.

**Qué muestra**:
- Distribución de grados (histograma log-log para verificar power law)
- Top 10 películas por cada centralidad (degree, betweenness, closeness, PageRank)
- Número de comunidades detectadas + modularidad
- Diámetro del grafo + average path length
- Coeficiente de clustering promedio
- Verificación small-world (clustering alto + path corto)

**Ventaja demostrativa**: Ningún sistema de recomendación basado en collaborative filtering o content-based filtering puede mostrar la estructura topológica de sus datos. Solo un sistema basado en grafos puede hacerlo.

**Implementación**: Endpoint `GET /graph/topology` que ejecute SPARQL analíticos + cálculos de NetworkX en Python, con cache en Redis.

### 9.2 🎯 Recomendación por Comunidad (Cluster-Based) .

**Funcionalidad**: El usuario selecciona una película → el sistema identifica su comunidad en el grafo → recomienda las mejores películas del mismo cluster y de clusters adyacentes.

**Qué muestra**:
- Nombre y descripción del cluster (generado por LLM a partir de features dominantes)
- Películas top del cluster + "bridge movies" hacia clusters vecinos
- Visualización del cluster como subgrafo
- Opción "explorar cluster vecino" para serendipity

**Ventaja demostrativa**: Demuestra que el grafo tiene estructura real diferenciada — no es una bolsa de features planas como en content-based filtering.

### 9.3 🌐 Explorador de Influencia Cinematográfica 

**Funcionalidad**: Seleccionar una película y ver su "zona de influencia" — hasta dónde llega su conectividad en el grafo a 1, 2 y 3 hops.

**Qué muestra**:
- Grafo expandible por niveles (1-hop: conexiones directas, 2-hop: conexiones indirectas...)
- Métricas de centralidad de la película seleccionada
- "Reach": cuántas películas son alcanzables en N hops
- Comparación: "Esta película tiene un reach de 450 películas en 2 hops vs. el promedio de 120"

**Ventaja demostrativa**: Visualiza la riqueza semántica del grafo que es imposible de representar en un sistema vectorial.

### 9.4 🎲 Serendipity Engine (Motor de Descubrimiento) .

**Funcionalidad**: Recomendar películas que son relevantes pero sorprendentes — combinando compatibility score con métricas de redes.

**Algoritmo**:
```
serendipityScore = compatibilityScore × (1 - clusteringCoefficient) 
                   × betweennessCentrality × (1 - popularityNorm)
```

**Qué muestra**:
- "Película sorpresa del día" basada en el perfil del usuario
- Explicación: "Esta película es un puente entre el cine de detectives y la ciencia ficción — su director es reconocido en ambos géneros"
- Gráfico radar comparando: relevancia, sorpresa, calidad, diversidad

**Ventaja demostrativa**: Los sistemas tradicionales tienden a recomendar lo popular y lo obvio. Este sistema puede cuantificar y optimizar la sorpresa usando métricas topológicas.

### 9.5 📊 Diversidad de Recomendación (Diversity Score) .

**Funcionalidad**: Para cada set de recomendaciones, calcular y mostrar un score de diversidad basado en la distancia en el grafo entre las películas recomendadas.

**Algoritmo**:
```
diversityScore = avg(distance(movie_i, movie_j)) para todo par i,j en recomendaciones
```

**Qué muestra**:
- Score de diversidad 0-100 con indicador visual
- "Este set de recomendaciones cubre 4 clusters diferentes del grafo"
- Slider para que el usuario ajuste: más diverso ↔ más enfocado
- Comparación: "Un sistema content-based te daría 5 películas del mismo director; nosotros te damos películas de 3 clusters conectados"

**Ventaja demostrativa**: Métrica cuantificable y transparente de diversidad que no existe en sistemas tradicionales.

### 9.6 🔗 "Grados de Separación" Cinematográficos

**Funcionalidad**: Extensión del explorador de conexiones actual con métricas de redes complejas.

**Mejoras**:
- Calcular y mostrar la distribución de distancias del grafo completo
- "¿Sabías que el 95% de las películas se conectan en 3 hops o menos?"
- Identificar los "bridge nodes" (personas o géneros) que más reducen la distancia promedio
- Modo competitivo: "¿Puedes encontrar dos películas con distancia > 4?"

### 9.7 🧬 Perfil Topológico del Usuario .

**Funcionalidad**: Basado en el historial del usuario, construir un "perfil topológico" que describe su posición en el grafo.

**Qué muestra**:
- Clusters favoritos del usuario (donde caen sus películas vistas/buscadas)
- "Eres un explorador" (historial disperso) vs "Eres un especialista" (historial concentrado)
- Zonas del grafo inexploradas → sugerencias de expansión
- Evolución temporal del perfil (¿se está diversificando o especializando?)

### 9.8 ⚡ Recomendación por Propagación de Preferencias

**Funcionalidad**: Cuando el usuario marca una película como favorita, propagar la preferencia por el grafo usando un modelo de difusión (tipo PageRank Personalizado).

**Algoritmo**:
```
PersonalizedPageRank(seed = película favorita del usuario)
→ Score de "proximidad personalizada" para todas las películas
→ Recomendar las top-K con mayor score + filtro de contexto
```

**Ventaja demostrativa**: Demuestra aprendizaje incremental sobre el grafo sin reentrenamiento de modelos.

---

## 10. Ventajas frente a Sistemas de Recomendación Tradicionales

### 10.1 Tabla Comparativa

| Criterio | Collaborative Filtering | Content-Based | CineSemantico (Ontología + GraphRAG) |
|---|---|---|---|
| **Cold Start** | Falla (necesita ratings) | Parcial (necesita features) | **Funciona** (el grafo tiene relaciones pre-existentes, el contexto del usuario se extrae en tiempo real) |
| **Explicabilidad** | "Usuarios similares vieron X" | "Comparte features con Y" | **"Comparte director + tono narrativo 'dark' + ganaron el mismo premio, y se ajusta a tu mood actual"** |
| **Contexto del usuario** | No modela contexto | No modela contexto | **Modela 4 dimensiones: social, emocional, temporal, requisitos** |
| **Multi-hop reasoning** | No existe | No existe | **Nativo: SPARQL paths de longitud arbitraria** |
| **Diversidad** | Baja (popularity bias) | Baja (feature bubble) | **Cuantificable via métricas topológicas** |
| **Serendipity** | Baja | Muy baja | **Calculable como función de betweenness + clustering** |
| **Actualización** | Re-entrenar modelo | Re-calcular similitudes | **INSERT tripleta → disponible inmediatamente** |
| **Transparencia** | Caja negra | Semi-transparente | **Caja blanca: RDF visible + SPARQL auditable** |
| **Escalabilidad semántica** | No existe | Requiere feature engineering | **Las ontologías se extienden añadiendo clases/propiedades** |
| **Estructura de datos** | Matriz usuario-item | Feature vectors | **Grafo de conocimiento con semántica formal** |

### 10.2 Funcionalidades que Solo un Sistema Basado en Grafos Puede Ofrecer

1. **Explorador de Conexiones**: Mostrar cómo dos películas cualquiera se conectan a través del grafo → imposible en CF/CB
2. **Análisis Topológico**: Métricas de redes complejas sobre el catálogo → no existe en sistemas planos
3. **Comunidades Semánticas**: Agrupaciones emergentes del grafo (no features manuales) → solo posible con estructura de grafo
4. **Diversidad Cuantificable**: Distancia en grafo entre recomendaciones → en CF/CB la diversidad es heurística
5. **Propagación de Preferencias**: Difusión sobre el grafo → requiere topología explícita
6. **Contexto como Ontología**: El contexto del usuario es también RDF, integrado bidireccionalemnte con el dominio → en CF/CB el contexto es un filtro plano
7. **Razonamiento SWRL**: Reglas lógicas ejecutables sobre las tripletas → imposible en matrices dispersas

### 10.3 Métricas Demostrable para la Tesis

| Métrica | Cómo demostrarlo | Qué demuestra |
|---|---|---|
| **Precision@K contextual** | Evaluar si las top-K recomendaciones respetan el contexto (niños → no horror) | Superioridad del modelado contextual |
| **Diversidad intra-lista** | Medir distancia promedio en grafo entre las K recomendaciones | Capacidad de diversificación |
| **Serendipity** | Encuesta de usuario: "¿Esta recomendación te sorprendió positivamente?" | Descubrimiento vs. burbuja |
| **Explicabilidad** | Evaluar si el usuario entiende por qué se recomendó algo (A/B test con/sin grafo visible) | Transparencia del sistema |
| **Cold Start resilience** | Test con usuario nuevo → recomendaciones basadas solo en contexto temporal/social | Funcionamiento sin historial |
| **Cobertura del catálogo** | % de películas en el grafo que alguna vez se recomiendan | Anti-popularity bias |
| **Tiempo de respuesta** | Medir executionTimeMs del pipeline | Viabilidad práctica |
| **Topological metrics correlation** | Correlación entre betweenness y serendipity percibida | Validación de la tesis de redes complejas |

---

## 11. Roadmap de Implementación

### 11.0 Seguimiento de Implementación (Redes Complejas)

> Checklist vivo para ir marcando lo que ya está implementado en backend/frontend.

- [x] **Cold start con señal de red compleja**: estrategia para usuarios sin historial/favoritos basada en centralidad estructural (conectividad por género/director) + rating global + diversidad por género.
- [x] **Recomendación por actividad del usuario**: endpoint dedicado que sintetiza preferencias desde historial y favoritos para personalizar la recomendación principal del home.
- [ ] **Centralidades persistidas en ontología**: almacenar explícitamente `degree`, `betweenness`, `closeness`, `pagerank` como tripletas RDF para consumo directo en SPARQL.
- [ ] **Detección de comunidades (Leiden/Louvain)**: asignar `movie:belongsToCluster` y habilitar recomendación intra/inter cluster.
- [ ] **Métricas topológicas expuestas por API**: endpoint analítico (`/graph/topology`) con distribución de grados, clustering promedio, modularidad y path length.
- [ ] **Serendipity formal**: integrar score de sorpresa (combinando centralidad/anti-popularity/clustering) en el ranking final.
- [ ] **Diversity score en respuesta**: reportar diversidad intra-lista vía distancia media en grafo entre recomendaciones.

### Fase 1: Métricas de Redes (Backend — 2-3 semanas)

| # | Tarea | Módulo |
|---|---|---|
| 1.1 | Crear `NetworkAnalysisModule` con servicio de cálculo de centralidades | `modules/network/` |
| 1.2 | Exportar subgrafo proyectado (película-película) desde Fuseki a NetworkX (Python microservice o script) | `scripts/` |
| 1.3 | Calcular y almacenar: degree, betweenness, closeness, PageRank, clustering coefficient por película | Fuseki (nuevas tripletas) |
| 1.4 | Ejecutar detección de comunidades (Leiden) y asignar `movie:belongsToCluster` | Fuseki |
| 1.5 | Endpoint `GET /graph/topology` con métricas globales del grafo | `modules/network/` |

### Fase 2: Nuevas Funcionalidades de Recomendación (Backend + Frontend — 3-4 semanas)

| # | Tarea | Ubicación |
|---|---|---|
| 2.1 | Endpoint `GET /movies/:uri/cluster` — comunidad + vecinos | Backend |
| 2.2 | Endpoint `GET /movies/:uri/influence` — expansión por hops | Backend |
| 2.3 | Serendipity score como factor adicional en `calculateCompatibilityScores()` | `LlmService` |
| 2.4 | Diversity score en la respuesta del `RecommendationService` | Backend |
| 2.5 | Frontend: Dashboard topológico con gráficos (D3.js / Recharts) | Frontend |
| 2.6 | Frontend: Página de comunidades con visualización de clusters | Frontend |
| 2.7 | Frontend: Expansión del explorador de conexiones con métricas | Frontend |

### Fase 3: Perfil Topológico y Propagación (2-3 semanas)

| # | Tarea | Ubicación |
|---|---|---|
| 3.1 | Construir perfil topológico del usuario basado en historial | Backend |
| 3.2 | Personalized PageRank sobre el grafo | Python microservice |
| 3.3 | Frontend: Visualización del perfil topológico del usuario | Frontend |
| 3.4 | Slider diversidad/enfoque en la UI de recomendaciones | Frontend |

### Fase 4: Evaluación y Tesis (2-3 semanas)

| # | Tarea |
|---|---|
| 4.1 | Diseñar estudio de usuario (A/B test: con/sin métricas topológicas) |
| 4.2 | Recopilar métricas cuantitativas (precision, diversity, serendipity, coverage) |
| 4.3 | Documentar resultados y correlaciones topología ↔ calidad de recomendación |
| 4.4 | Redactar capítulo de tesis con análisis comparativo |

---

## Apéndice A: Namespaces del Sistema

```turtle
@prefix movie:      <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#> .
@prefix context:    <http://www.semanticweb.org/movierecommendation/ontologies/2025/context-ontology#> .
@prefix bridge:     <http://www.semanticweb.org/movierecommendation/ontologies/2025/bridge-ontology#> .
@prefix moviedata:  <http://www.semanticweb.org/movierecommendation/data/movie/> .
@prefix genre:      <http://www.semanticweb.org/movierecommendation/data/genre/> .
@prefix person:     <http://www.semanticweb.org/movierecommendation/data/person/> .
@prefix company:    <http://www.semanticweb.org/movierecommendation/data/company/> .
@prefix rdf:        <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:       <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:        <http://www.w3.org/2002/07/owl#> .
@prefix xsd:        <http://www.w3.org/2001/XMLSchema#> .
@prefix schema:     <http://schema.org/> .
```

## Apéndice B: Ejemplo Completo de Flujo

**Input del usuario**: "Estoy con mis hijos, tenemos 90 minutos, quiero algo divertido"

**Paso 1 — RDF generado**:
```turtle
:snapshot1 a context:ContextSnapshot ;
  context:hourOfDay 20 ;
  context:dayOfWeek "Sábado" ;
  context:userIntent "película divertida para ver con hijos" ;
  context:withCompanion :social1 ;
  context:feelsMood :emotion1 ;
  context:hasRequirement :req1 .

:social1 a context:SocialContext ;
  context:companionType "familia con niños" ;
  context:hasChildren true .

:emotion1 a context:EmotionalContext ;
  context:moodDescription "alegre" ;
  context:desiredEnergyLevel "medio" .

:req1 a context:RequirementContext ;
  context:availableTime 90 .
```

**Paso 2 — SPARQL generado**:
```sparql
PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>
PREFIX genre: <http://www.semanticweb.org/movierecommendation/data/genre/>

SELECT DISTINCT ?title ?runtime ?genreName ?releaseDate ?averageRating WHERE {
  { ?m a movie:FeatureFilm } UNION { ?m a movie:AnimatedFilm }
  ?m movie:hasTitle ?title ;
     movie:runtime ?runtime ;
     movie:hasMainGenre ?g .
  ?g movie:genreName ?genreName .
  OPTIONAL { ?m movie:releaseDate ?releaseDate }
  OPTIONAL { ?m movie:hasAverageRating ?averageRating }
  FILTER(?runtime <= 120)
  FILTER(
    CONTAINS(?genreName, "Animation") ||
    CONTAINS(?genreName, "Comedy") ||
    CONTAINS(?genreName, "Family") ||
    CONTAINS(?genreName, "Adventure")
  )
  FILTER(
    !CONTAINS(?genreName, "Horror") &&
    !CONTAINS(?genreName, "Thriller") &&
    !CONTAINS(?genreName, "Crime") &&
    !CONTAINS(?genreName, "War")
  )
}
ORDER BY DESC(?averageRating)
LIMIT 20
```

**Paso 3**: Fuseki retorna 20 películas candidatas

**Paso 4**: LLM calcula compatibility scores:
- "Toy Story" → 0.95 (animada, familiar, 81 min, alegre)
- "Finding Nemo" → 0.92 (animada, aventura, 100 min, divertida)
- "Shrek" → 0.88 (animada, comedia, 90 min, familiar)

**Paso 5**: Respuesta narrativa:
> "¡Perfecta elección para una noche en familia! Te recomiendo Toy Story, una película animada de 81 minutos ideal para tus hijos — divertida, emotiva, y con un mensaje sobre la amistad. Si quieren algo más aventurero, Finding Nemo es una excelente opción con paisajes marinos espectaculares que mantendrá a todos entretenidos."

---

*Documento generado para planificación del Trabajo de Grado — Marzo 2026*
