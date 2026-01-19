"""
Configuración centralizada para scripts RDF del sistema de recomendación de películas.

Este paquete contiene:
- namespaces.py: Definiciones centralizadas de namespaces RDF/OWL
- config.py: Configuración general (si existe)
"""

from .namespaces import *

__all__ = [
    # Namespaces de ontologías
    'MOVIE_NS',
    'CONTEXT_NS',
    'BRIDGE_NS',
    
    # Namespaces de datos
    'MOVIE_DATA_NS',
    'CONTEXT_DATA_NS',
    'GENRE_DATA_NS',
    'PERSON_DATA_NS',
    'COMPANY_DATA_NS',
    'KEYWORD_DATA_NS',
    'COUNTRY_DATA_NS',
    'LANGUAGE_DATA_NS',
    'PERIOD_DATA_NS',
    'PLOTSTRUCTURE_DATA_NS',
    'ROLE_DATA_NS',
    'THEME_DATA_NS',
    'TONE_DATA_NS',
    
    # Aliases
    'HISTORICAL_PERIOD_DATA_NS',
    'PLOT_STRUCTURE_DATA_NS',
    
    # Namespaces externos
    'SCHEMA',
    'DBO',
    
    # Namespaces estándar
    'RDF', 'RDF_NS',
    'RDFS', 'RDFS_NS',
    'OWL', 'OWL_NS',
    'XSD', 'XSD_NS',
    'FOAF', 'FOAF_NS',
    
    # Utilidades
    'bind_all_namespaces',
    'get_sparql_prefix_header',
    'SPARQL_PREFIXES',
    'ALL_NAMESPACES',
    
    # Clases y propiedades
    'MOVIE_CLASSES',
    'CONTEXT_CLASSES',
    'BRIDGE_CLASSES',
    'MOVIE_PROPERTIES',
    'CONTEXT_PROPERTIES',
    'BRIDGE_PROPERTIES',
]
