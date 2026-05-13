# 7. Implementación del Prototipo

El presente capítulo documenta la materialización de los Objetivos Específicos 3 y 4 del proyecto: la aplicación de inferencia semántica para generar recomendaciones contextualizadas (OE3) y el desarrollo del prototipo funcional completo (OE4). Se describe la arquitectura del sistema, el pipeline de construcción del grafo de conocimiento, el pipeline de recomendación basado en GraphRAG, la API REST del backend y las vistas principales de la interfaz de usuario.

---

## 7.1. Arquitectura General del Sistema

El prototipo implementa una arquitectura en cuatro capas desacopladas que separan la presentación, la lógica de negocio, el acceso al grafo de conocimiento y el almacenamiento persistente de usuarios.

```
┌──────────────────────────────────────────────────────────────────┐
│                    CineSemantico — Stack Tecnológico             │
│                                                                  │
│  ┌──────────────────┐     ┌───────────────────┐                  │
│  │  Frontend        │     │  Backend           │                  │
│  │  Next.js 15      │◄───►│  FastAPI (Python)  │                  │
│  │  React 19        │     │  Puerto 8000        │                  │
│  │  Tailwind CSS 4  │     └────────┬──────────┘                  │
│  └──────────────────┘             │                              │
│                          ┌────────┴──────────┐                   │
│                          │  Servicios Externos│                   │
│                     ┌────┴────┐  ┌───────────┴──┐               │
│                     │ Fuseki  │  │  Groq Cloud   │               │
│                     │ :3030   │  │  Llama 3.3    │               │
│                     └─────────┘  └──────────────┘               │
│                          │                                       │
│                     ┌────┴────┐                                  │
│                     │ MongoDB │ ← Usuarios + Historial           │
│                     └─────────┘                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 7.1.1. Stack Tecnológico

| Componente | Tecnología | Propósito |
|---|---|---|
| **Frontend** | Next.js 15, React 19, Tailwind CSS 4 | Interfaz de usuario con diseño atómico |
| **Backend** | FastAPI (Python), Arquitectura Limpia | API REST, orquestación del pipeline |
| **Triplestore** | Apache Jena Fuseki + SPARQL 1.1 | Almacenamiento y consulta del grafo de conocimiento |
| **LLM** | Groq Cloud — Llama 3.3 70B Versatile | Extracción de contexto, generación SPARQL, scoring, narrativa |
| **Base de datos** | MongoDB | Usuarios, autenticación JWT, historial de consultas, favoritos |
| **Pipeline ETL** | Python, rdflib, pandas | Transformación CSV → RDF Turtle, enriquecimiento con APIs |

La elección de **FastAPI** como framework del backend responde a tres criterios: rendimiento asíncrono para las llamadas concurrentes al LLM, validación automática de esquemas con Pydantic, y generación automática de documentación OpenAPI. **Groq Cloud** fue seleccionado como proveedor del LLM por su latencia inferior a 500 ms en el modelo Llama 3.3 70B Versatile, un factor crítico para la experiencia del usuario en un pipeline de cinco pasos.

### 7.1.2. Arquitectura Limpia del Backend

El backend sigue los principios de Arquitectura Limpia (*Clean Architecture*, Martin 2017), organizando el código en capas con dependencias que apuntan siempre hacia el dominio:

```
app/
├── domain/          ← Entidades y contratos de repositorios (sin dependencias)
│   └── entities/    ← AuthUser, Movie, ContextSnapshot, QueryHistory
├── application/     ← Casos de uso (lógica de negocio pura)
│   └── use_cases/   ← RecommendationUseCase, MoviesUseCase, ChatUseCase
├── adapters/        ← Implementaciones concretas de los contratos
│   ├── llm/         ← GroqRecommendationLlmAdapter, GeminiRecommendationLlmAdapter
│   └── repositories/← MongoAuthUserRepository, MongoQueryHistoryRepository
├── api/             ← Capa HTTP (FastAPI routers, schemas Pydantic, DI)
│   ├── v1/endpoints/
│   └── schemas/
└── core/            ← Servicios transversales (ProfileService, configuración)
```

Esta separación permite reemplazar el proveedor de LLM (de Groq a Gemini o cualquier otro) sin modificar la lógica de negocio, simplemente registrando un adaptador diferente en el contenedor de inyección de dependencias.

---

## 7.2. Pipeline de Construcción del Grafo de Conocimiento

Antes de que el sistema pueda ejecutar recomendaciones, el grafo de conocimiento debe ser poblado con datos cinematográficos reales. Este proceso se realiza mediante un pipeline ETL (Extract, Transform, Load) implementado en Python que transforma datos tabulares en tripletas RDF y las carga en el triplestore Fuseki.

### 7.2.1. Fuentes de Datos

El grafo de conocimiento se construye a partir de dos fuentes primarias:

- **MovieLens 25M**: Dataset público de GroupLens Research con metadatos de películas y calificaciones de usuarios. Provee el catálogo base de películas con identificadores TMDb.
- **APIs de enriquecimiento**: La API de TMDb (*The Movie Database*) proporciona el cast detallado (directores, actores, productoras), sinopsis en español, pósters, géneros y datos financieros. La API de OMDb complementa con calificaciones de IMDb y Metascore.

### 7.2.2. Etapas del Pipeline

El pipeline se ejecuta mediante el script `pipeline.py`, que orquesta los siguientes pasos en secuencia:

**Paso 1 — ETL base** (`etl/data_loader.py`): Carga el CSV de MovieLens, aplica filtros de calidad (películas sin título o sin géneros son descartadas), normaliza identificadores y genera `movies_processed.csv`.

**Paso 2 — Enriquecimiento** (`enrichment/enrichment.py`): Para cada película del catálogo, realiza llamadas a las APIs de TMDb y OMDb para obtener el cast completo, la sinopsis en español, los géneros canónicos, las compañías productoras, el presupuesto y la recaudación. El resultado se persiste en `movies_enriched.csv`. El pipeline implementa un modo **incremental** que únicamente solicita enriquecimiento para películas nuevas, evitando el consumo innecesario de cuotas de API.

**Paso 3 — Generación RDF de películas** (`rdf/rdf_generator.py`): Convierte el CSV enriquecido a tripletas RDF Turtle siguiendo el esquema de `movie-ontology`. Genera el archivo `movies_data.ttl` con aproximadamente 159,568 líneas de RDF, representando alrededor de 9,400 películas con su cast, géneros y metadatos.

**Paso 4 — Generación RDF de bridges** (`rdf/regenerate_bridge_data.py`): Genera el archivo `bridge_data.ttl` con los 53 mapeos contexto-género predefinidos y los scores iniciales de compatibilidad por película. Este archivo implementa la capa de alineación semántica de la `bridge-ontology`.

**Paso 5 — Importación a Fuseki**: El pipeline realiza un HTTP POST de los archivos `.ttl` al endpoint `/data` del triplestore Fuseki (`http://localhost:3030/movies/data`), completando la carga del grafo. Las credenciales de Fuseki se gestionan exclusivamente mediante variables de entorno (`FUSEKI_URL`, `FUSEKI_USER`, `FUSEKI_PASSWORD`), nunca como argumentos CLI.

```bash
# Ejecución completa del pipeline
python pipeline.py

# Opciones disponibles
python pipeline.py --max-movies 500     # Limitar películas para pruebas
python pipeline.py --skip-enrichment    # Regenerar RDF sin re-consumir APIs
python pipeline.py --skip-import        # Generar TTL sin cargar a Fuseki
python pipeline.py --no-incremental     # Sobrescribir completamente (no merge)
```

### 7.2.3. Estructura del Grafo Resultante

Una vez completado el pipeline, el triplestore Fuseki aloja dos grafos nombrados (*named graphs*):

| Grafo nombrado | Archivo fuente | Tamaño | Contenido |
|---|---|---|---|
| `/movies/data` | `movies_data.ttl` | 159,568 líneas | ~9,400 películas con géneros, cast, calificaciones, metadatos |
| `/movies/data` | `bridge_data.ttl` | 18,920 líneas | 53 mapeos contexto-género, scores de compatibilidad, flags `isKidFriendly` |

*Tabla 14: Composición del grafo de conocimiento en Fuseki*

---

## 7.3. Pipeline de Recomendación GraphRAG

El núcleo del sistema es el pipeline de recomendación basado en GraphRAG (*Graph Retrieval-Augmented Generation*). A diferencia del RAG vectorial tradicional —que recupera documentos por similitud coseno en un espacio de embeddings— GraphRAG realiza el *retrieval* ejecutando consultas SPARQL estructuradas directamente sobre el grafo de conocimiento. Esto permite razonamiento semántico multi-hop, filtros lógicos exactos y trazabilidad completa de cada recomendación hasta las tripletas RDF que la justifican.

### 7.3.1. Flujo del Pipeline

El `RecommendationUseCase` orquesta cinco pasos secuenciales, de los cuales cuatro implican una invocación al LLM:

```
  Consulta del usuario (lenguaje natural)
         │
         ▼
┌────────────────────────┐
│ PASO 1                  │  LLM: extractSemanticContext()
│ Extracción de Contexto  │  → RDF Turtle (ContextSnapshot)
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│ PASO 2                  │  LLM: generateSparqlQuery()
│ Generación SPARQL       │  → Consulta SPARQL SELECT
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│ PASO 3                  │  Fuseki: executeQuery()
│ Retrieval sobre el Grafo│  → ≤20 películas candidatas
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│ PASO 4                  │  LLM: calculateCompatibilityScores()
│ Scoring Contextual      │  → Score 0.0–1.0 por película
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│ PASO 5                  │  LLM: generateNarrativeResponse()
│ Respuesta Narrativa     │  → Texto personalizado (≤150 palabras)
└────────────────────────┘
         │
         ▼
   Persistencia en MongoDB (historial) + Respuesta al frontend
```

### 7.3.2. Paso 1: Extracción de Contexto Semántico

El LLM recibe la consulta del usuario junto con la hora actual y el día de la semana, y produce un fragmento RDF Turtle que instancia un `ContextSnapshot` conforme al esquema de `context-ontology`. El vocabulario controlado definido en la ontología (ver §6.3) es parte del prompt del sistema, garantizando que los valores generados sean exactamente los individuos válidos del ABox.

Ejemplo de salida para la consulta *"Quiero ver algo con mis hijos esta noche, máximo 90 minutos"*:

```turtle
@prefix context: <http://example.org/context-ontology#> .

:snapshot_xyz a context:ContextSnapshot ;
  context:hourOfDay 20 ;
  context:dayOfWeek "friday" ;
  context:userIntent "película familiar divertida" ;
  context:hasSocialContext :social_xyz ;
  context:hasEmotionalContext :emotion_xyz ;
  context:hasRequirementContext :req_xyz .

:social_xyz a context:SocialContext ;
  context:companionType "family" ;
  context:hasChildren true .

:emotion_xyz a context:EmotionalContext ;
  context:emotionalState "happy" ;
  context:energyLevel "moderate" .

:req_xyz a context:RequirementContext ;
  context:maxDuration 90 .
```

El RDF generado es parseado y validado antes de continuar al siguiente paso. Si el LLM produce RDF sintácticamente inválido, el pipeline aplica un mecanismo de reintento con instrucciones de corrección.

### 7.3.3. Paso 2: Generación de Consulta SPARQL

El LLM recibe el `ContextSnapshot` serializado como JSON y produce una consulta SPARQL SELECT que incorpora los filtros contextuales como restricciones nativas de la consulta. La consulta usa los prefijos reales de las tres ontologías y el vocabulario controlado como claves de unión exactas.

Ejemplo de consulta generada para el contexto anterior:

```sparql
PREFIX mo: <http://example.org/movie-ontology#>
PREFIX bo: <http://example.org/bridge-ontology#>
PREFIX co: <http://example.org/context-ontology#>

SELECT DISTINCT ?title ?runtime ?genreName ?releaseDate ?averageRating WHERE {
  { ?m a mo:FeatureFilm } UNION { ?m a mo:AnimatedFilm }
  ?m mo:hasTitle ?title ;
     mo:runtime ?runtime ;
     mo:hasMainGenre ?g .
  ?g mo:genreName ?genreName .
  OPTIONAL { ?m mo:releaseDate ?releaseDate }
  OPTIONAL { ?m mo:hasAverageRating ?averageRating }

  FILTER(?runtime <= 90)
  FILTER(
    CONTAINS(?genreName, "Animation") ||
    CONTAINS(?genreName, "Comedy")    ||
    CONTAINS(?genreName, "Family")    ||
    CONTAINS(?genreName, "Adventure")
  )
  FILTER(
    !CONTAINS(?genreName, "Horror")  &&
    !CONTAINS(?genreName, "Thriller")
  )
}
ORDER BY DESC(?averageRating)
LIMIT 20
```

Esta consulta demuestra tres propiedades del sistema: (1) **multi-ontología**, al navegar de `mo:Movie` a `mo:Genre`; (2) **restricciones contextuales nativas**, los filtros de duración y género son ciudadanos de primera clase de la consulta; (3) **vocabulario controlado como clave de unión**, los strings `"Animation"`, `"family"` son exactamente los valores del ABox.

### 7.3.4. Paso 3: Retrieval sobre el Grafo

La consulta SPARQL se envía al endpoint de consulta de Fuseki mediante HTTP POST (`application/sparql-query`). Fuseki ejecuta la consulta contra el grafo de conocimiento y retorna los bindings en formato JSON estándar SPARQL 1.1. El sistema extrae hasta 20 películas candidatas de la respuesta.

### 7.3.5. Paso 4: Scoring de Compatibilidad Contextual

El LLM recibe las 10 películas con mayor rating del resultado anterior junto con el `ContextSnapshot` completo, y asigna un score de compatibilidad (0.0–1.0) a cada una. Los criterios de scoring están ponderados:

| Criterio | Peso | Descripción |
|---|---|---|
| Alineación emocional | 40% | Correspondencia entre el género/tono de la película y el estado emocional + nivel de energía del usuario |
| Contexto social | 30% | Adecuación de la película para el tipo de compañía (familia con niños, pareja, amigos, solo) |
| Requisitos logísticos | 20% | Cumplimiento de restricciones como duración máxima, idioma o aptitud para menores |
| Calidad cinematográfica | 10% | Calificación promedio de la película en el grafo (`mo:hasAverageRating`) |

*Tabla 15: Criterios de scoring de compatibilidad contextual*

### 7.3.6. Paso 5: Generación de Respuesta Narrativa

Las 5 películas con mayor score son entregadas al LLM junto con la consulta original y el contexto. El LLM genera un texto narrativo personalizado (máximo 150 palabras) que justifica cada recomendación en términos del contexto específico del usuario, usando el nombre de la película, sus características relevantes y la razón contextual de su adecuación.

### 7.3.7. Respuesta Completa al Frontend

El `RecommendationUseCase` consolida los resultados de los cinco pasos y retorna al frontend el siguiente objeto JSON:

```json
{
  "query": "Quiero ver algo con mis hijos esta noche, máximo 90 minutos",
  "contextExtracted": {
    "snapshotID": "snapshot_xyz",
    "requestTimestamp": "2026-04-29T20:15:00Z",
    "userIntent": "película familiar divertida",
    "socialContext": { "companionType": "family", "hasChildren": true },
    "emotionalContext": { "emotionalState": "happy", "energyLevel": "moderate" },
    "requirementContext": { "maxDuration": 90 }
  },
  "rdfGenerated": "@prefix context: <...>\n:snapshot_xyz a context:ContextSnapshot ; ...",
  "sparqlQuery": "PREFIX mo: <...> SELECT DISTINCT ?title ...",
  "moviesFound": 20,
  "moviesWithScores": [
    { "title": "Toy Story", "runtime": 81, "genreName": "Animation", "compatibilityScore": 0.95 },
    { "title": "Finding Nemo", "runtime": 100, "genreName": "Animation", "compatibilityScore": 0.92 }
  ],
  "explanation": "¡Perfecta elección para una noche en familia! Toy Story (81 min) es ideal...",
  "executionTimeMs": 4523
}
```

La inclusión de `rdfGenerated` y `sparqlQuery` en la respuesta permite que el frontend muestre la trazabilidad completa del proceso al usuario, una característica diferenciadora que ningún sistema de recomendación tradicional puede ofrecer.

---

## 7.4. API REST del Backend

El backend expone una API REST documentada automáticamente vía OpenAPI (Swagger UI en `/docs`). Los endpoints se organizan en módulos temáticos.

### 7.4.1. Módulo de Recomendación

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/recommendation?query={text}` | Ejecuta el pipeline completo de 5 pasos |
| `POST` | `/recommendation` | Idem, con query en el cuerpo JSON |
| `GET` | `/recommendation/activity` | Recomendación personalizada basada en perfil del usuario: historial, favoritos, hora del día y exploración topológica de clusters |

El endpoint `/recommendation/activity` combina tres señales para construir una consulta contextualizada automáticamente: el momento del día (inferido del timestamp del servidor), los géneros favoritos ponderados por frecuencia en el historial, y el índice de exploración topológica del usuario (proporción de clusters visitados vs. no visitados).

### 7.4.2. Módulo de Películas

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/movies/search` | Búsqueda con filtros: `q`, `genre`, `director`, `yearFrom`, `yearTo`, `limit` |
| `GET` | `/movies/autocomplete?q={text}` | Sugerencias de películas para búsqueda en tiempo real (SPARQL) |
| `GET` | `/movies/connections?from={uri}&to={uri}` | Conexiones directas e indirectas entre dos películas en el grafo |
| `GET` | `/movies/examples` | Películas representativas para onboarding |

La búsqueda SPARQL en `/movies/search` implementa un sistema de scoring por relevancia: coincidencia exacta de título (200 puntos), mismo director (80 puntos), mismo género (40 puntos). Esto garantiza que los resultados más relevantes aparezcan primero sin depender de embeddings ni índices vectoriales.

### 7.4.3. Módulo de Autenticación y Usuarios

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/auth/register` | Registro con email + contraseña (bcrypt, 12 rounds) |
| `POST` | `/auth/login` | Login con JWT (expiración: 24 horas) |
| `GET` | `/users/me` | Perfil del usuario autenticado |
| `GET` | `/users/me/favorites` | Lista de películas favoritas |
| `POST` | `/users/me/favorites` | Añadir película a favoritos |
| `DELETE` | `/users/me/favorites/{movieId}` | Eliminar de favoritos |
| `GET` | `/history` | Historial de consultas del usuario |

Los endpoints que requieren autenticación aplican el middleware `get_current_user` que valida el JWT de la cabecera `Authorization: Bearer {token}` y recupera el perfil del usuario desde MongoDB.

### 7.4.4. Módulo de Clusters y Grafo

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/clusters` | Lista de clusters del grafo con películas representativas |
| `GET` | `/clusters/{id}` | Detalle de un cluster específico |
| `GET` | `/graph/topology` | Métricas topológicas del grafo (en desarrollo) |

---

## 7.5. Interfaz de Usuario

La interfaz de usuario fue desarrollada en Next.js 15 siguiendo la metodología de Diseño Atómico (*Atomic Design*, Frost 2016), que organiza los componentes en cinco niveles de complejidad creciente: átomos, moléculas, organismos, plantillas y páginas. Esta estructura garantiza la consistencia visual y la reutilización de componentes en todo el sistema.

### 7.5.1. Sistema de Diseño

El sistema de diseño implementa un conjunto de tokens de color semánticos definidos en `globals.css` mediante variables CSS nativas (`@theme inline`):

| Token | Valor | Uso |
|---|---|---|
| `--color-bg` | `#0D0D0F` | Fondo principal oscuro |
| `--color-surface` | `#16161A` | Tarjetas y paneles |
| `--color-accent` | `#E53E3E` | Acciones primarias |
| `--color-teal` | `#38B2AC` | Indicadores semánticos |
| `--color-text` | `#F7FAFC` | Texto principal |
| `--color-muted` | `#718096` | Texto secundario |

*Tabla 16: Tokens de color del sistema de diseño CineSemantico*

Las tipografías son **Bebas Neue** (headings, display) y **DM Sans** (cuerpo y UI), importadas desde Google Fonts.

### 7.5.2. Página Principal (`/`)

La página principal combina búsqueda semántica y descubrimiento pasivo en una sola vista. Sus componentes principales son:

- **HeroSection**: Búsqueda en lenguaje natural con autocompletado SPARQL en tiempo real. El usuario puede escribir el título de una película, el nombre de un director o un género, y el sistema retorna sugerencias consultando el grafo directamente.
- **ContextRecommendation**: Película destacada calculada según el momento del día del usuario, inferida del timestamp del servidor y personalizada por el perfil topológico.
- **FeaturedMoviesSection**: Carrusel de películas con calificación promedio ≥ 4.0 en el grafo, consultadas dinámicamente vía SPARQL.
- **DiscoverySection**: Sección educativa que explica brevemente el paradigma de recomendación por grafos de conocimiento, orientada a reducir la fricción cognitiva del usuario ante un sistema diferente a los convencionales.

### 7.5.3. Interfaz de Chat (`/chat`)

La interfaz de chat implementa el flujo conversacional de recomendación. Su diseño de tres columnas separa el historial de sesiones (izquierda), la conversación activa (centro) y el detalle del contexto extraído (derecha).

El componente central es el `AssistantBubble`, que para cada respuesta del sistema muestra:

1. La narrativa de recomendación en lenguaje natural.
2. Las tarjetas `MovieRecommendationCard` de las 5 películas recomendadas, con título, género, duración, año y el `compatibilityScore` visualizado mediante una barra de progreso animada.
3. El fragmento RDF generado por el LLM (panel colapsable), permitiendo al usuario ver la representación formal de su contexto.
4. La consulta SPARQL ejecutada (panel colapsable), proporcionando trazabilidad completa del proceso de retrieval.
5. El tiempo de ejecución total del pipeline (`executionTimeMs`).

Esta transparencia es un diferenciador clave del sistema: el usuario puede verificar exactamente qué información fue usada para generar cada recomendación, algo imposible en sistemas de recomendación basados en redes neuronales.

### 7.5.4. Explorador de Conexiones (`/connections`)

El explorador de conexiones materializa la naturaleza de grafo del sistema, permitiendo al usuario descubrir cómo dos películas cualesquiera se relacionan a través de entidades compartidas.

El flujo de interacción es:
1. El usuario selecciona dos películas mediante el autocompletado.
2. El sistema ejecuta una consulta SPARQL de navegación de grafo que busca conexiones directas (1-hop: mismo director, mismo actor, mismo género) e indirectas (2-hop: a través de una entidad intermedia).
3. Los resultados se visualizan como un grafo interactivo con nodos codificados por color según el tipo de entidad (azul: película, naranja: género, verde: director/actor) y aristas etiquetadas con el tipo de relación.
4. La consulta SPARQL ejecutada se muestra al usuario para fines educativos.

### 7.5.5. Autenticación

El sistema implementa autenticación JWT completa con flujos de registro y login. Las contraseñas se almacenan en MongoDB usando bcrypt con 12 rounds de salt. El token JWT tiene una validez de 24 horas y se transmite en la cabecera `Authorization: Bearer` en cada petición a endpoints protegidos. Un componente `ProtectedRoute` en el frontend intercepta las rutas que requieren autenticación y redirige al login si el token ha expirado o es inválido.

---

## 7.6. Integración entre Componentes

La Figura 7 ilustra el flujo completo de una consulta de recomendación desde el usuario hasta el triplestore y de regreso, detallando qué componente es responsable de cada transformación.

Para cerrar el ciclo de integración, la Tabla 17 resume la correspondencia entre los cinco pasos del pipeline de recomendación y los componentes de software que los implementan:

| Paso | Responsabilidad | Componente |
|---|---|---|
| 1 — Extracción de contexto | Interpretar la consulta del usuario | `GroqRecommendationLlmAdapter.extractSemanticContext()` |
| 2 — Generación SPARQL | Traducir el contexto a una consulta formal | `GroqRecommendationLlmAdapter.generateSparqlQuery()` |
| 3 — Retrieval | Ejecutar la consulta contra el grafo | `GraphService.executeQuery()` → Fuseki HTTP API |
| 4 — Scoring | Calcular la compatibilidad contextual | `GroqRecommendationLlmAdapter.calculateCompatibilityScores()` |
| 5 — Narrativa | Generar la respuesta para el usuario | `GroqRecommendationLlmAdapter.generateNarrativeResponse()` |
| Persistencia | Guardar el historial de consultas | `MongoQueryHistoryRepository.save()` |

*Tabla 17: Correspondencia entre pasos del pipeline y componentes de implementación*

---

## 7.7. Ejemplo Completo de Ejecución

Para ilustrar el funcionamiento integrado del sistema, se presenta un ejemplo completo con la consulta *"Estoy con mis hijos, tenemos 90 minutos, quiero algo divertido"*:

**Entrada**: Consulta en lenguaje natural enviada mediante `POST /recommendation`.

**Paso 1 — Contexto extraído**:
```json
{
  "companionType": "family",
  "hasChildren": true,
  "emotionalState": "happy",
  "energyLevel": "moderate",
  "maxDuration": 90
}
```

**Paso 2 — SPARQL generado**: Consulta con `UNION { ?m a mo:AnimatedFilm }`, `FILTER(?runtime <= 90)`, y exclusiones de Horror y Thriller.

**Paso 3 — Retrieval**: Fuseki retorna 20 películas candidatas en 112 ms.

**Paso 4 — Scores de compatibilidad**:
- *Toy Story* → 0.95 (animada, 81 min, familiar, alegre)
- *Finding Nemo* → 0.92 (animada, aventura, 100 min)
- *Shrek* → 0.88 (animada, comedia, 90 min)

**Paso 5 — Narrativa**:
> "¡Perfecta elección para una noche en familia! Te recomiendo *Toy Story* (81 min): divertida, emotiva y con un mensaje sobre la amistad que encantará a los niños. Si prefieren algo aventurero, *Finding Nemo* es ideal para toda la familia, con paisajes espectaculares que mantendrán a todos pegados a la pantalla."

**Tiempo total de ejecución**: 4,523 ms (4 llamadas al LLM + 1 consulta Fuseki).
