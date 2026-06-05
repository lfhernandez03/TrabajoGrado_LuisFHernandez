# MOVIQ — Sistema de Recomendación Cinematográfica Semántica

> Trabajo de Grado · Universidad del Valle · Escuela de Ingeniería de Sistemas y Computación
> Autor: Luis F. Hernández · 2026

**MOVIQ** es un sistema de recomendación de películas que combina ontologías OWL/RDF, GraphRAG (*Graph Retrieval-Augmented Generation*) y modelos de lenguaje de gran escala (LLM) para ofrecer recomendaciones explicables y contextualizadas a partir de lenguaje natural.

El usuario escribe algo como *"quiero una película relajante para ver en familia esta noche"* y el sistema extrae su contexto semántico, genera una consulta SPARQL sobre el grafo de conocimiento y devuelve recomendaciones con una justificación narrativa.

---

## Cómo funciona

```
Usuario: "Quiero algo emocionante para ver con amigos, menos de 2 horas"
         │
         ▼
① Extracción de contexto (LLM)
   mood: emocionante · compañía: amigos · tiempo: < 2 h
         │
         ▼
② Construcción de consulta SPARQL
   cruzando movie-ontology + context-ontology + bridge-ontology
         │
         ▼
③ Ejecución en Apache Jena Fuseki (triple store RDF)
   estrategia progresiva: strict → relaxed_runtime → relaxed_genre → broad
         │
         ▼
④ Scoring de compatibilidad + serendipity score
         │
         ▼
⑤ Explicación narrativa generada por LLM
         │
         ▼
5 películas recomendadas con justificación personalizada
```

---

## Arquitectura del sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   Navegador                                                         │
│   Next.js 16 + React 19 + Tailwind CSS                             │
│   (movie-graph-rag-frontend)                                        │
│         │                                                           │
│         │ REST / JSON                                               │
│         ▼                                                           │
│   API Backend                                                       │
│   FastAPI + Arquitectura Hexagonal                                  │
│   (movie-graph-rag-backend-fastapi)                                 │
│         │                          │                               │
│         │ SPARQL 1.1               │ MongoDB                       │
│         ▼                          ▼                               │
│   Apache Jena Fuseki          MongoDB Atlas                        │
│   Triple Store RDF            Usuarios · Historial · Favoritos     │
│         ▲                                                           │
│         │                                                           │
│   Pipeline ETL + Ontologías                                         │
│   (movie-graph-rag-ontologies)                                      │
│   MovieLens → enriquecimiento TMDb/OMDb → RDF → Fuseki             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

| Componente | Tecnología |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS v4, Radix UI |
| Backend | FastAPI, Python 3.11+, arquitectura hexagonal |
| Triple Store | Apache Jena Fuseki, SPARQL 1.1 |
| Base de datos | MongoDB |
| LLM principal | Google Gemini Flash 2.5 |
| LLM auxiliar | Llama 3.3 70B (Groq) |
| Ontologías | OWL 2 DL, RDF/Turtle, rdflib |
| Datos | MovieLens + enriquecimiento TMDb/OMDb |

---

## Repositorio

El proyecto está dividido en tres módulos independientes:

| Módulo | Descripción |
|---|---|
| [`movie-graph-rag-ontologies`](movie-graph-rag-ontologies/) | Ontologías OWL/RDF y pipeline ETL para poblar Fuseki |
| [`movie-graph-rag-backend-fastapi`](movie-graph-rag-backend-fastapi/) | API REST con lógica de recomendación semántica |
| [`movie-graph-rag-frontend`](movie-graph-rag-frontend/) | Interfaz web de usuario |

Cada módulo tiene su propio README con instrucciones de instalación y ejecución.

---

## Inicio rápido

### Prerequisitos

- Python 3.11+
- Node.js 18+
- MongoDB (local o Atlas)
- Apache Jena Fuseki (local o Docker)
- Clave de API de Google Gemini (opcional pero recomendada)

### 1 — Configurar Fuseki y cargar las ontologías

```bash
cd movie-graph-rag-ontologies

# Instalar dependencias
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install rdflib

# Configurar variables de entorno
cp .env.example .env   # editar con credenciales de Fuseki y APIs

# Ejecutar pipeline ETL completo
cd data/scripts
python pipeline.py --max-movies 500   # prueba rápida con 500 películas
```

### 2 — Iniciar el backend

```bash
cd movie-graph-rag-backend-fastapi

python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -e .[dev]

# Configurar variables de entorno
cp .env.example .env   # editar MONGO_URI, FUSEKI_URL, GEMINI_API_KEY

uvicorn app.main:app --reload --port 8000
```

La documentación interactiva queda disponible en `http://localhost:8000/docs`.

### 3 — Iniciar el frontend

```bash
cd movie-graph-rag-frontend

npm install

# Configurar backend URL
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
echo "NEXT_PUBLIC_API_PREFIX=/api/v1" >> .env.local

npm run dev
```

La aplicación queda disponible en `http://localhost:3000`.

---

## Ontologías

El conocimiento cinematográfico se representa mediante tres ontologías interdependientes:

**`movie-ontology`** — modela entidades del dominio: `Movie`, `Genre`, `Director`, `Actor`. Define propiedades como `hasGenre`, `hasRating`, `hasRuntime`.

**`context-ontology`** — modela el contexto del usuario: `ContextSnapshot`, `EmotionalContext`, `SocialContext`, `RequirementContext`. Captura estado de ánimo, compañía, energía deseada y tiempo disponible.

**`bridge-ontology`** — conecta película y contexto mediante reglas de compatibilidad (`compatibleMood`, `compatibleCompanion`, `compatibleEnergyLevel`), habilitando consultas SPARQL contextuales.

Los diagramas de las ontologías están disponibles en [`movie-graph-rag-ontologies/docs/figures/`](movie-graph-rag-ontologies/docs/figures/).

---

## Funcionalidades

### Chat de recomendación
Interfaz conversacional donde el usuario describe qué quiere ver. El sistema extrae el contexto semántico, ejecuta SPARQL y retorna películas con explicación narrativa generada por LLM.

### Página principal personalizada
Hero con la recomendación del día y tres carruseles adaptativos basados en el grafo:
- *Because you watched* — vecindad de 2 saltos desde un favorito
- *Like* — vecindad de otro favorito
- *Explore new genres* — películas de clusters aún no explorados

### Búsqueda avanzada
Grid con filtros por género, año, director y duración. Resultados enriquecidos con metadatos del grafo.

### Explorador de conexiones
Visualización de las relaciones entre películas en el grafo de conocimiento. Permite trazar caminos entre dos títulos con profundidad configurable.

### Perfil topológico
Vista del perfil del usuario en la red: clusters explorados, clusters adyacentes no visitados y estadísticas de actividad.

### Favoritos
Colección persistente de películas marcadas por el usuario, usada como señal para personalizar recomendaciones.

---

## Documentación

| Documento | Descripción |
|---|---|
| [`MANUAL_DE_USUARIO.md`](MANUAL_DE_USUARIO.md) | Guía de uso de la aplicación para el usuario final |
| [`MANUAL_TECNICO.md`](MANUAL_TECNICO.md) | Referencia técnica del sistema completo |
| [`ARQUITECTURA_COMPLETA.md`](ARQUITECTURA_COMPLETA.md) | Teoría de redes complejas e integración con ontologías |
| [`movie-graph-rag-backend-fastapi/README.md`](movie-graph-rag-backend-fastapi/README.md) | Instalación y endpoints del backend |
| [`movie-graph-rag-frontend/README.md`](movie-graph-rag-frontend/README.md) | Instalación y estructura del frontend |
| [`movie-graph-rag-ontologies/README.md`](movie-graph-rag-ontologies/README.md) | Ontologías y pipeline ETL |

---

## Contexto académico

Este proyecto es el Trabajo de Grado presentado ante la **Universidad del Valle**, Cali, Colombia, para optar al título de Ingeniero de Sistemas. Investiga la aplicación de tecnologías de web semántica (OWL 2, RDF, SPARQL), GraphRAG y LLMs en el dominio de la recomendación cinematográfica explicable, comparando ventajas frente a sistemas colaborativos y basados en contenido tradicionales.

**Palabras clave:** GraphRAG · Ontologías OWL · SPARQL · Recomendación explicable · Web semántica · LLM · Grafo de conocimiento
!(MovieOntology GIF)[https://drive.google.com/file/d/1ZvaYDaSPI0CgJNJneNup-zXcCkF-ZjZH/view?usp=sharing]


---

*Universidad del Valle · Escuela de Ingeniería de Sistemas y Computación · 2026*
