# movie-graph-rag-ontologies

Módulo de ontologías y pipeline ETL para el sistema **MOVIQ**. Define tres ontologías OWL/RDF que modelan películas, contexto del usuario y sus relaciones semánticas, y proporciona el pipeline automatizado para poblar Apache Fuseki con datos de MovieLens enriquecidos con TMDb y OMDb.

## Ontologías

El sistema usa tres ontologías interdependientes:

### `movie-ontology.ttl`
Modela entidades cinematográficas: `Movie`, `Genre`, `Director`, `Actor`, `ProductionCompany`. Define propiedades como `hasGenre`, `hasDirector`, `hasRating`, `hasRuntime`, `releaseDate`.

### `context-ontology.ttl`
Modela el contexto del usuario en el momento de la recomendación: `ContextSnapshot`, `EmotionalContext`, `SocialContext`, `RequirementContext`. Captura estado de ánimo (`moodDescription`), compañía (`companionType`), energía deseada (`desiredEnergyLevel`) y tiempo disponible (`availableTime`).

### `bridge-ontology.ttl` + `bridge-ontology-rules.owl`
Conecta las dos ontologías anteriores mediante reglas de compatibilidad (`compatibleMood`, `compatibleCompanion`, `compatibleEnergyLevel`). Cada película en el grafo recibe tripletas puente que permiten consultas SPARQL contextuales.

Los archivos fuente se encuentran en `data/ontologies/`:

```
data/ontologies/
├── base/
│   ├── movie-ontology.ttl
│   └── context-ontology.ttl
├── bridge/
│   ├── bridge-ontology.ttl
│   └── bridge-ontology-rules.owl
└── instances/
    ├── movies_data.ttl      # Tripletas de películas generadas
    └── bridge_data.ttl      # Conexiones película-contexto generadas
```

## Pipeline ETL

El pipeline transforma datos de MovieLens en tripletas RDF e importa el resultado a Fuseki.

### Flujo de datos

```
MovieLens CSV (movies.csv, ratings.csv, links.csv)
        ↓
[data_loader.py]      →  movies_processed.csv
        ↓
[enrichment.py]       →  movies_enriched.csv  (TMDb + OMDb)
        ↓
[rdf_generator.py]    →  movies_data.ttl
        ↓
[regenerate_bridge_data.py]  →  bridge_data.ttl
        ↓
[Fuseki Import]       →  Dataset "Cine" en Apache Fuseki
```

### Ejecución del pipeline

```bash
cd data/scripts

# Pipeline completo
python pipeline.py

# Limitar número de películas
python pipeline.py --max-movies 500

# Modo incremental hasta 5000 películas
python pipeline.py --max-movies 5000

# Saltar enriquecimiento (usar datos ya enriquecidos)
python pipeline.py --skip-enrichment

# Generar archivos TTL sin importar a Fuseki
python pipeline.py --skip-import

# Dataset Fuseki específico
python pipeline.py --fuseki-dataset Cine
```

### Opciones del pipeline

| Opción | Descripción |
|---|---|
| `--max-movies N` | Limita el procesamiento a N películas |
| `--skip-enrichment` | Omite el paso de enriquecimiento con APIs |
| `--skip-import` | Genera archivos TTL sin importarlos a Fuseki |
| `--no-incremental` | Sobrescribe archivos en lugar de hacer upsert |
| `--fuseki-url` | URL base de Fuseki (default: `http://localhost:3030`) |
| `--fuseki-dataset` | Nombre del dataset (default: `Cine`) |
| `--fuseki-user` | Usuario de Fuseki |
| `--fuseki-password` | Contraseña de Fuseki |

El modo incremental (activo por defecto) actualiza los CSVs por `movieId` y reemplaza solo el subgrafo de las películas procesadas en los TTL, preservando el resto del dataset.

## Requisitos

- Python 3.10+
- Apache Fuseki corriendo (recomendado via Docker)
- Claves de API para enriquecimiento (opcionales)

### Instalación de dependencias

```bash
cd movie-graph-rag-ontologies
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install rdflib
```

## Variables de entorno

Crear un archivo `.env` en la raíz del módulo:

```env
# Fuseki
FUSEKI_URL=http://localhost:3030
FUSEKI_USER=admin
FUSEKI_PASSWORD=your_password

# APIs de enriquecimiento
TMDB_API_KEY=your_tmdb_key
OMDB_API_KEY=your_omdb_key
```

## Estructura del módulo

```
data/
├── dataset/
│   ├── raw/             # CSVs originales de MovieLens
│   └── processed/       # CSVs intermedios del pipeline
├── ontologies/          # Archivos TTL/OWL de ontologías e instancias
└── scripts/
    ├── pipeline.py      # Orquestador principal
    ├── config/          # Configuración, namespaces, vocabulario
    ├── etl/             # data_loader.py — carga y limpieza de MovieLens
    ├── enrichment/      # enrichment.py — enriquecimiento TMDb/OMDb
    └── rdf/             # rdf_generator.py, regenerate_bridge_data.py

docs/
├── figures/             # Diagramas SVG/PNG de las ontologías
└── markdown/            # Documentación técnica del proceso RDF

lib/                     # Librerías JS (vis.js, tom-select) para visualización local
```

## Pre-carga en Fuseki

Para preparar el dataset de Fuseki desde cero con los archivos TTL ya generados:

```powershell
# Windows — valida la instancia de Fuseki
.\data\scripts\validate-fuseki.ps1

# Carga las ontologías base e instancias
.\data\scripts\pre-load.ps1
```

Ver `data/scripts/README_PRELOAD.md` para instrucciones detalladas.

## Diagramas

Los diagramas de las ontologías se encuentran en `docs/figures/`:

| Archivo | Contenido |
|---|---|
| `movie-ontology-diagram.png` | Clases y propiedades de la ontología de películas |
| `context-ontology-diagram.png` | Clases y propiedades de la ontología de contexto |
| `bridge-ontology-diagram.png` | Relaciones de la ontología puente |
| `ontology-integration.png` | Integración de las tres ontologías |
| `graphrag-flow.png` | Flujo completo Graph RAG |

## Vocabulario controlado

El vocabulario de valores válidos para atributos semánticos (géneros, estados de ánimo, tipos de compañía, niveles de energía) está documentado en `data/ontologies/VOCABULARIO_CONTROLADO.md`. Este vocabulario es compartido entre el pipeline ETL y el backend para garantizar coherencia en las consultas SPARQL.
