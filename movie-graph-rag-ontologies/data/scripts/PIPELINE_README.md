# Pipeline de Procesamiento de Peliculas

Script automatizado que ejecuta todo el flujo de procesamiento de datos de peliculas en secuencia.

## Uso

```bash
# Pipeline completo (todas las peliculas)
python pipeline.py

# Pipeline con limite de peliculas
python pipeline.py --max-movies 100

# Pipeline incremental (default): completa hasta 5000 sin borrar existentes
python pipeline.py --max-movies 5000

# Sobrescritura total (sin incremental)
python pipeline.py --max-movies 5000 --no-incremental

# Regenerar RDF sin enriquecer nuevamente (usa datos existentes)
python pipeline.py --skip-enrichment

# Generar archivos sin importar a Fuseki
python pipeline.py --skip-import

# Combinacion: 500 peliculas sin importar
python pipeline.py --max-movies 500 --skip-import

# DEPRECATED - Incluir NLP inference (no recomendado)
python pipeline.py --include-nlp
```

## Pasos del Pipeline

El pipeline ejecuta los siguientes pasos en orden (por defecto sin NLP):

1. **ETL** - Carga y procesamiento base de MovieLens CSV
2. **Enrichment** (opcional) - Enriquecimiento con TMDb/OMDb APIs (genera movies_enriched.csv)
3. **RDF Generation - Movies** - Genera tripletas RDF de peliculas desde movies_enriched.csv (o movies_nlp_enriched.csv si existe)
4. **RDF Generation - Bridges** - Genera conexiones pelicula-contexto con propiedades temporales usando regenerate_bridge_data.py
5. **Fuseki Import** (opcional) - Importa movies_data.ttl y bridge_data.ttl al dataset de Fuseki

### Notas sobre Pasos:
- **NLP Inference** (DEPRECATED): Anteriormente era parte del pipeline por defecto. Ahora es opcional con `--include-nlp`. Se mantiene para compatibilidad backward pero NO se recomienda usar.
- **Context Generation** (DEPRECATED): Los contextos se generan dinamicamente mediante ontology_query_builder.py. El archivo rdf_context_generator.py esta deprecated y ya no es ejecutado por el pipeline.

## Opciones

- `--max-movies N`: Limita el procesamiento a N peliculas (default: todas)
- `--skip-enrichment`: Omite enriquecimiento con APIs (paso 2) - usa datos ya enriquecidos
- `--include-nlp`: DEPRECATED - Incluye NLP inference (paso 3 opcional). No recomendado.
- `--skip-import`: Omite paso 5 (solo genera archivos TTL sin importarlos)
- `--no-incremental`: Desactiva modo incremental y sobrescribe archivos de salida
- `--fuseki-url`: URL base de Fuseki (default: `http://localhost:3030`)
- `--fuseki-dataset`: Dataset de Fuseki (default: `Cine`)
- `--fuseki-user` / `--fuseki-password`: credenciales opcionales de Fuseki (tambien pueden usar variables de entorno FUSEKI_USER, FUSEKI_PASSWORD)

## Modo incremental (default)

- Los CSV (`movies_processed.csv`, `movies_enriched.csv`, `movies_nlp_enriched.csv`) se actualizan por `movieId` (upsert).
- Los TTL (`movies_data.ttl`, `bridge_data.ttl`) reemplazan solo el subgrafo de las peliculas procesadas, manteniendo el resto.
- Con `--max-movies 5000`, el pipeline intenta dejar el dataset de salida en 5000 peliculas maximas (ordenadas por rating/popularidad disponible).

## Flujo de Datos

```
MovieLens CSV
    ↓
[data_loader.py] → movies_processed.csv
    ↓
[enrichment.py] → movies_enriched.csv (TMDb/OMDb data)
    ↓
[rdf_generator.py] → movies_data.ttl
    ├─ Input: movies_enriched.csv (o movies_nlp_enriched.csv si existe)
    │ 
[regenerate_bridge_data.py] → bridge_data.ttl
    ├─ Input: movies_data.ttl + opcional bridge_data.ttl previo
    │
[Fuseki Import] → Triple Store
    ├─ movies_data.ttl
    └─ bridge_data.ttl
```

### Flujo con NLP (DEPRECATED - con --include-nlp):

```
MovieLens CSV
    ↓
[data_loader.py] → movies_processed.csv
    ↓
[enrichment.py] → movies_enriched.csv
    ↓
[nlp_inference.py] → movies_nlp_enriched.csv
    ↓
[rdf_generator.py] → movies_data.ttl
    (usa movies_nlp_enriched.csv como input)
```

## Escenarios de Uso

### Añadir nuevas películas (full pipeline)
```bash
python pipeline.py
```

### Probar con dataset pequeño
```bash
python pipeline.py --max-movies 50
```

### Actualizar solo la generación RDF
```bash
python pipeline.py --skip-enrichment
```

### Generar archivos para revisión manual
```bash
python pipeline.py --skip-import
# Revisa los .ttl generados
# Luego importa ejecutando el pipeline sin --skip-import
```

### Importar en dataset Fuseki específico
```bash
python pipeline.py --max-movies 5000 --fuseki-dataset Cine
```

## Archivos Legacy

Los siguientes scripts han sido reemplazados o removidos del pipeline automático:

### rdf_bridge_generator.py
- **Estado**: LEGACY - Mantenido por compatibilidad backward
- **Razón**: Reemplazado por `regenerate_bridge_data.py`
- **Diferencia**: 
  - `rdf_bridge_generator.py` generaba propiedades con valores concatenados (p.ej., `bridge:allCompatibleMoods "feliz|relajado"`)
  - `regenerate_bridge_data.py` genera tripletas individuales (p.ej., `bridge:compatibleMood "feliz"` para cada valor)
- **Ubicación**: `data/scripts/rdf/rdf_bridge_generator.py`
- **NO utilizar**: Si necesitas bridges, ejecuta `regenerate_bridge_data.py` manualmente

### rdf_context_generator.py
- **Estado**: LEGACY - Mantenido por auditoría histórica
- **Razón**: Eliminated - Contextos se generan dinámicamente
- **Funcionalidad anterior**: Generaba 4 contextos ficticios de prueba
- **Alternativa**: Usar `ontology_query_builder.py` para generar contextos dinámicos según el usuario
- **Ubicación**: `data/scripts/rdf/rdf_context_generator.py`
- **NO incluir**: Ya no es necesario y contexts_data.ttl no se importa a Fuseki

### nlp_inference.py (Opcionalmente DEPRECATED)
- **Estado**: DEPRECATED pero aún funcional
- **Razón**: Proporciona limitado valor en ranking de recomendaciones
- **Comportamiento**: Si se ejecuta, genera `movies_nlp_enriched.csv`
- **Uso**: `python pipeline.py --include-nlp` (NO recomendado)
- **Alternativa**: Las inferencias de contexto se derivan de propiedades de película + contexto del usuario actual

## Prerequisitos

- Python 3.10+
- Dependencias instaladas (ver requirements.txt)
- Docker corriendo con contenedor Fuseki
- Variables de entorno configuradas (.env con API keys y Fuseki credentials)

## Variables de Entorno

```bash
# Obligatorio si usando Fuseki con autenticación
export FUSEKI_URL=http://fuseki-server:3030
export FUSEKI_USER=admin
export FUSEKI_PASSWORD=your_secure_password

# Para APIs de películas
export TMDB_API_KEY=your_tmdb_key
export OMDB_API_KEY=your_omdb_key
```
