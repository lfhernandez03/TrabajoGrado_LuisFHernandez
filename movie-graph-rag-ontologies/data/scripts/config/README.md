# Configuración Centralizada de Namespaces

Este directorio contiene la configuración centralizada de namespaces para el sistema de recomendación de películas.

## Archivos

### `namespaces.py`
**Archivo central de definición de namespaces RDF/OWL**

Define todos los namespaces usados en el proyecto en un solo lugar para evitar inconsistencias y duplicación de código.

## Uso

### En Scripts de RDF

```python
from config.namespaces import (
    MOVIE_NS, CONTEXT_NS, BRIDGE_NS,
    MOVIE_DATA_NS, CONTEXT_DATA_NS,
    RDF, RDFS, OWL, XSD,
    bind_all_namespaces
)

# Crear grafo y vincular todos los namespaces
g = Graph()
bind_all_namespaces(g)

# Usar los namespaces
movie_uri = MOVIE_DATA_NS[f"movie_{movie_id}"]
g.add((movie_uri, RDF.type, MOVIE_NS.Movie))
```

### En Queries SPARQL

```python
from config.namespaces import get_sparql_prefix_header

# Obtener prefijos para SPARQL
prefixes = get_sparql_prefix_header()

query = f"""
{prefixes}

SELECT ?movie ?title WHERE {{
    ?movie rdf:type movie:Movie .
    ?movie movie:title ?title .
}}
"""
```

## Namespaces Definidos

### Ontologías (TBox)
- `MOVIE_NS` - Ontología de películas
- `CONTEXT_NS` - Ontología de contextos
- `BRIDGE_NS` - Ontología de conexiones

### Datos (ABox)
- `MOVIE_DATA_NS` - Instancias de películas
- `CONTEXT_DATA_NS` - Instancias de contextos
- `GENRE_DATA_NS` - Instancias de géneros
- `PERSON_DATA_NS` - Instancias de personas
- `COMPANY_DATA_NS` - Instancias de compañías
- `KEYWORD_DATA_NS` - Instancias de palabras clave
- `COUNTRY_DATA_NS` - Instancias de países
- `LANGUAGE_DATA_NS` - Instancias de idiomas
- `ROLE_DATA_NS` - Instancias de roles
- `TONE_DATA_NS` - Instancias de tonos
- `THEME_DATA_NS` - Instancias de temas
- `PLOTSTRUCTURE_DATA_NS` - Instancias de estructuras de trama
- `PERIOD_DATA_NS` - Instancias de períodos históricos

### Namespaces Externos
- `SCHEMA` - Schema.org
- `DBO` - DBpedia Ontology
- `RDF`, `RDFS`, `OWL`, `XSD`, `FOAF` - Namespaces estándar

## Funciones Auxiliares

### `bind_all_namespaces(graph)`
Vincula todos los namespaces a un grafo RDFLib.

```python
from rdflib import Graph
from config.namespaces import bind_all_namespaces

g = Graph()
bind_all_namespaces(g)
```

### `get_sparql_prefix_header()`
Genera el header de prefijos para consultas SPARQL.

```python
from config.namespaces import get_sparql_prefix_header

prefixes = get_sparql_prefix_header()
query = f"{prefixes}\nSELECT ?s ?p ?o WHERE {{ ?s ?p ?o }} LIMIT 10"
```

## Ventajas de la Centralización

1. **Consistencia**: Todos los archivos usan los mismos URIs
2. **Mantenibilidad**: Cambiar un namespace solo requiere editar un archivo
3. **Documentación**: Un solo lugar para documentar todos los namespaces
4. **Autocompletado**: Mejor experiencia de desarrollo con IDEs
5. **Validación**: Fácil verificar que todos usen los namespaces correctos

## Archivos que Usan Este Módulo

- `rdf/rdf_generator.py` - Generador de datos de películas
- `rdf/rdf_context_generator.py` - Generador de datos de contexto
- `rdf/rdf_bridge_generator.py` - Generador de conexiones bridge
- `test_sparql_queries.py` - Tests de queries SPARQL
- `test_context_queries.py` - Tests de queries de contexto
- `test_bridge_queries.py` - Tests de queries de bridge

## Notas Importantes

- **NO** definir namespaces localmente en otros archivos
- Siempre importar desde `config.namespaces`
- Si necesitas un namespace nuevo, añádelo aquí primero
- Los aliases `HISTORICAL_PERIOD_DATA_NS` y `PLOT_STRUCTURE_DATA_NS` se mantienen por compatibilidad

## Sincronización con Backend

Este archivo está sincronizado con:
```
Backend/src/config/ontology_namespaces.py
```

Ambos archivos deben mantenerse consistentes para evitar diferencias entre los scripts de generación de datos y el backend.
