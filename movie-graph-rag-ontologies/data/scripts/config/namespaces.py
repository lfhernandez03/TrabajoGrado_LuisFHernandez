"""
Configuracion centralizada de namespaces y URIs para las ontologias del sistema.
Define los prefijos RDF y URIs base para movie, context y bridge ontologies.

IMPORTANTE: Este es el UNICO lugar donde se definen los namespaces para los scripts.
Todos los scripts RDF deben importar desde aqui para evitar inconsistencias.

Este archivo es una copia del archivo de configuracion del backend para mantener
consistencia entre los scripts de generacion de datos y el backend.
"""

from rdflib import Namespace
from rdflib.namespace import RDF, RDFS, OWL, XSD, FOAF

# Base URIs
BASE_URI = "http://www.semanticweb.org/movierecommendation/"

# ============================================================================
# NAMESPACES PRINCIPALES (TBox - Ontologias)
# ============================================================================
MOVIE_NS = Namespace(f"{BASE_URI}ontologies/2025/movie-ontology#")
CONTEXT_NS = Namespace(f"{BASE_URI}ontologies/2025/context-ontology#")
BRIDGE_NS = Namespace(f"{BASE_URI}ontologies/2025/bridge-ontology#")

# ============================================================================
# NAMESPACES DE DATOS (ABox - Instancias)
# Nota: Todos los namespaces de datos usan '/' al final
# ============================================================================
MOVIE_DATA_NS = Namespace(f"{BASE_URI}data/movie/")
GENRE_DATA_NS = Namespace(f"{BASE_URI}data/genre/")
CONTEXT_DATA_NS = Namespace(f"{BASE_URI}data/context/")
COMPANY_DATA_NS = Namespace(f"{BASE_URI}data/company/")
COUNTRY_DATA_NS = Namespace(f"{BASE_URI}data/country/")
KEYWORD_DATA_NS = Namespace(f"{BASE_URI}data/keyword/")
LANGUAGE_DATA_NS = Namespace(f"{BASE_URI}data/language/")
PERSON_DATA_NS = Namespace(f"{BASE_URI}data/person/")
PERIOD_DATA_NS = Namespace(f"{BASE_URI}data/historicalperiod/")
PLOTSTRUCTURE_DATA_NS = Namespace(f"{BASE_URI}data/plotstructure/")
ROLE_DATA_NS = Namespace(f"{BASE_URI}data/role/")
THEME_DATA_NS = Namespace(f"{BASE_URI}data/theme/")
TONE_DATA_NS = Namespace(f"{BASE_URI}data/tone/")

# Aliases para compatibilidad con codigo existente
HISTORICAL_PERIOD_DATA_NS = PERIOD_DATA_NS  # Alias para consistencia
PLOT_STRUCTURE_DATA_NS = PLOTSTRUCTURE_DATA_NS  # Alias para consistencia

# ============================================================================
# NAMESPACES EXTERNOS ESTANDAR
# ============================================================================
SCHEMA = Namespace("http://schema.org/")
DBO = Namespace("http://dbpedia.org/ontology/")

# Namespaces estandar de RDFLib (re-exportados para conveniencia)
RDF_NS = RDF
RDFS_NS = RDFS
OWL_NS = OWL
XSD_NS = XSD
FOAF_NS = FOAF

# ============================================================================
# MAPEOS Y UTILIDADES
# ============================================================================

# Mapeo de prefijos para SPARQL (alineado con las ontologias TTL)
SPARQL_PREFIXES = {
    "movie": MOVIE_NS,
    "context": CONTEXT_NS,
    "bridge": BRIDGE_NS,
    "moviedata": MOVIE_DATA_NS,
    "contextdata": CONTEXT_DATA_NS,
    "genre": GENRE_DATA_NS,
    "company": COMPANY_DATA_NS,
    "country": COUNTRY_DATA_NS,
    "keyword": KEYWORD_DATA_NS,
    "language": LANGUAGE_DATA_NS,
    "person": PERSON_DATA_NS,
    "period": PERIOD_DATA_NS,
    "plotstructure": PLOTSTRUCTURE_DATA_NS,
    "role": ROLE_DATA_NS,
    "theme": THEME_DATA_NS,
    "tone": TONE_DATA_NS,
    "schema": SCHEMA,
    "dbo": DBO,
    "rdf": RDF_NS,
    "rdfs": RDFS_NS,
    "owl": OWL_NS,
    "xsd": XSD_NS,
    "foaf": FOAF_NS,
}

# Lista de todos los namespaces para vincular a un grafo
ALL_NAMESPACES = {
    "movie": MOVIE_NS,
    "context": CONTEXT_NS,
    "bridge": BRIDGE_NS,
    "moviedata": MOVIE_DATA_NS,
    "contextdata": CONTEXT_DATA_NS,
    "genre": GENRE_DATA_NS,
    "company": COMPANY_DATA_NS,
    "country": COUNTRY_DATA_NS,
    "keyword": KEYWORD_DATA_NS,
    "language": LANGUAGE_DATA_NS,
    "person": PERSON_DATA_NS,
    "period": PERIOD_DATA_NS,
    "plotstructure": PLOTSTRUCTURE_DATA_NS,
    "role": ROLE_DATA_NS,
    "theme": THEME_DATA_NS,
    "tone": TONE_DATA_NS,
    "schema": SCHEMA,
    "dbo": DBO,
    "rdf": RDF,
    "rdfs": RDFS,
    "owl": OWL,
    "xsd": XSD,
    "foaf": FOAF,
}

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def get_sparql_prefix_header() -> str:
    """
    Genera el header con todos los prefijos SPARQL.
    
    Returns:
        String con todas las declaraciones PREFIX para usar en queries SPARQL
        
    Example:
        >>> header = get_sparql_prefix_header()
        >>> query = f"{header}\\nSELECT ?movie WHERE {{ ?movie rdf:type movie:Movie }}"
    """
    lines = [f"PREFIX {prefix}: <{ns}>" for prefix, ns in SPARQL_PREFIXES.items()]
    return "\n".join(lines)


def bind_all_namespaces(graph):
    """
    Vincula todos los namespaces definidos a un grafo RDFLib.
    
    Args:
        graph: Una instancia de rdflib.Graph
        
    Returns:
        El mismo grafo con los namespaces vinculados
        
    Example:
        >>> from rdflib import Graph
        >>> g = Graph()
        >>> g = bind_all_namespaces(g)
    """
    for prefix, namespace in ALL_NAMESPACES.items():
        graph.bind(prefix, namespace)
    return graph


# ============================================================================
# CLASES Y PROPIEDADES PRINCIPALES (Para referencia y autocompletado)
# ============================================================================

# Clases principales de Movie Ontology
MOVIE_CLASSES = {
    "Movie": MOVIE_NS.Movie,
    "Genre": MOVIE_NS.Genre,
    "Director": MOVIE_NS.Director,
    "Actor": MOVIE_NS.Actor,
    "Review": MOVIE_NS.Review,
    "ProductionCompany": MOVIE_NS.ProductionCompany,
    "Keyword": MOVIE_NS.Keyword,
}

# Clases principales de Context Ontology
CONTEXT_CLASSES = {
    "User": CONTEXT_NS.User,
    "ContextSnapshot": CONTEXT_NS.ContextSnapshot,
    "SocialContext": CONTEXT_NS.SocialContext,
    "EmotionalContext": CONTEXT_NS.EmotionalContext,
    "RequirementContext": CONTEXT_NS.RequirementContext,
}

# Clases principales de Bridge Ontology
BRIDGE_CLASSES = {
    "Recommendation": BRIDGE_NS.Recommendation,
    "ContextMovieMapping": BRIDGE_NS.ContextMovieMapping,
}

# Propiedades principales de Movie Ontology
MOVIE_PROPERTIES = {
    "hasGenre": MOVIE_NS.hasGenre,
    "hasDirector": MOVIE_NS.hasDirector,
    "hasActor": MOVIE_NS.hasActor,
    "hasRating": MOVIE_NS.hasRating,
    "releaseYear": MOVIE_NS.releaseYear,
    "duration": MOVIE_NS.duration,
    "budget": MOVIE_NS.budget,
}

# Propiedades principales de Context Ontology
CONTEXT_PROPERTIES = {
    "hasSocialContext": CONTEXT_NS.hasSocialContext,
    "hasEmotionalContext": CONTEXT_NS.hasEmotionalContext,
    "hasRequirementContext": CONTEXT_NS.hasRequirementContext,
    "companionType": CONTEXT_NS.companionType,
    "desiredEnergyLevel": CONTEXT_NS.desiredEnergyLevel,
    "maxDuration": CONTEXT_NS.maxDuration,
}

# Propiedades principales de Bridge Ontology
BRIDGE_PROPERTIES = {
    "satisfiesRequirement": BRIDGE_NS.satisfiesRequirement,
    "moodMatchScore": BRIDGE_NS.moodMatchScore,
    "socialMatchScore": BRIDGE_NS.socialMatchScore,
    "contextToMovie": BRIDGE_NS.contextToMovie,
    "confidence": BRIDGE_NS.confidence,
}
