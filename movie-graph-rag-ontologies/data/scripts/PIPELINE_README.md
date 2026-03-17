# Pipeline de Procesamiento de Películas

Script automatizado que ejecuta todo el flujo de procesamiento de datos de películas en secuencia.

## Uso

```bash
# Pipeline completo (todas las películas)
python pipeline.py

# Pipeline con límite de películas
python pipeline.py --max-movies 100

# Pipeline incremental (default): completa hasta 5000 sin borrar existentes
python pipeline.py --max-movies 5000

# Sobrescritura total (sin incremental)
python pipeline.py --max-movies 5000 --no-incremental

# Regenerar RDF sin enriquecer nuevamente (usa datos existentes)
python pipeline.py --skip-enrichment

# Generar archivos sin importar a GraphDB
python pipeline.py --skip-import

# Combinación: 500 películas sin importar
python pipeline.py --max-movies 500 --skip-import
```

## Pasos del Pipeline

1. **ETL** - Carga y procesamiento base de MovieLens
2. **Enrichment** (opcional) - Enriquecimiento con TMDb/OMDb APIs
3. **NLP Inference** (opcional) - Inferencias contextuales mediante NLP
4. **RDF Generation - Movies** - Genera tripletas RDF de películas
5. **RDF Generation - Contexts** - Genera contextos predefinidos
6. **RDF Generation - Bridges** - Genera conexiones película-contexto
7. **Fuseki Import** (opcional) - Importa datos al dataset de Fuseki

## Opciones

- `--max-movies N`: Limita el procesamiento a N películas (default: todas)
- `--skip-enrichment`: Omite pasos 2 y 3 (usa datos ya enriquecidos)
- `--skip-import`: Omite paso 7 (solo genera archivos TTL)
- `--no-incremental`: Desactiva modo incremental y sobrescribe archivos de salida
- `--fuseki-url`: URL base de Fuseki (default: `http://localhost:3030`)
- `--fuseki-dataset`: Dataset de Fuseki (default: `movies`)
- `--fuseki-user` / `--fuseki-password`: credenciales opcionales de Fuseki

## Modo incremental (default)

- Los CSV (`movies_processed.csv`, `movies_enriched.csv`, `movies_nlp_enriched.csv`) se actualizan por `movieId` (upsert).
- Los TTL (`movies_data.ttl`, `bridge_data.ttl`) reemplazan solo el subgrafo de las películas procesadas, manteniendo el resto.
- Con `--max-movies 5000`, el pipeline intenta dejar el dataset de salida en 5000 películas máximas (ordenadas por rating/popularidad disponible).

## Flujo de Datos

```
MovieLens CSV
    ↓
[data_loader.py] → movies_processed.csv
    ↓
[enrichment.py] → movies_enriched.csv (TMDb/OMDb data)
    ↓
[nlp_inference.py] → movies_nlp_enriched.csv (NLP inferences)
    ↓
[rdf_generator.py] → movies_data.ttl
[rdf_context_generator.py] → contexts_data.ttl
[rdf_bridge_generator.py] → bridge_data.ttl
    ↓
[GraphDB Import] → Triple Store
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

## Prerequisitos

- Python 3.10+
- Dependencias instaladas (ver requirements.txt)
- Docker corriendo con contenedor `graphdb-tesis`
- Variables de entorno configuradas (.env con API keys)
