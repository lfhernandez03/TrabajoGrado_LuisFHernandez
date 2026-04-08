/**
 * Generates display-only SPARQL query strings for the Explainable AI panel.
 * These are NOT executed — they show the user what kind of semantic query was run.
 */

export type SearchMode = 'title' | 'director' | 'genre';

export function buildDisplaySparqlQuery(
  searchTerm: string,
  mode: SearchMode = 'title',
): string {
  const safe = searchTerm.toLowerCase().replace(/"/g, '\\"');

  if (mode === 'director') {
    return `PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT DISTINCT ?movie ?title ?directorName ?genreName ?rating ?description
WHERE {
  ?movie rdf:type movie:FeatureFilm ;
         movie:hasTitle ?title .
  ?movie movie:hasDirector/movie:personName ?directorName .
  FILTER(CONTAINS(LCASE(?directorName), "${safe}"))

  OPTIONAL { ?movie movie:hasMainGenre/movie:genreName ?genreName }
  OPTIONAL { ?movie movie:hasAverageRating ?rating }
  OPTIONAL { ?movie movie:hasPlotSummary ?description }
}
ORDER BY DESC(?rating)
LIMIT 30`;
  }

  if (mode === 'genre') {
    return `PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT DISTINCT ?movie ?title ?directorName ?genreName ?rating ?description
WHERE {
  ?movie rdf:type movie:FeatureFilm ;
         movie:hasTitle ?title .
  ?movie movie:hasMainGenre/movie:genreName ?genreName .
  FILTER(CONTAINS(LCASE(?genreName), "${safe}"))

  OPTIONAL { ?movie movie:hasDirector/movie:personName ?directorName }
  OPTIONAL { ?movie movie:hasAverageRating ?rating }
  OPTIONAL { ?movie movie:hasPlotSummary ?description }
}
ORDER BY DESC(?rating)
LIMIT 30`;
  }

  // Default: title search with related movies via director and genre
  return `PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT DISTINCT ?movie ?title ?directorName ?genreName ?rating ?description ?matchScore ?relationReason
WHERE {
  # 1. Coincidencia directa por título
  {
    ?movie rdf:type movie:FeatureFilm ;
           movie:hasTitle ?title .
    FILTER(CONTAINS(LCASE(?title), "${safe}"))
    BIND(200 AS ?baseScore)
    BIND("Coincidencia exacta con tu búsqueda" AS ?relationReason)
  }
  UNION
  # 2. Películas del mismo director
  {
    ?seed rdf:type movie:FeatureFilm ;
          movie:hasTitle ?seedTitle .
    FILTER(CONTAINS(LCASE(?seedTitle), "${safe}"))
    ?seed movie:hasDirector ?dir .
    ?dir movie:personName ?sharedDirector .
    ?movie movie:hasDirector ?dir .
    FILTER(?seed != ?movie)
    BIND(80 AS ?relScore)
    BIND(CONCAT("Comparten el director ", ?sharedDirector) AS ?relationReason)
  }
  UNION
  # 3. Películas del mismo género
  {
    ?seed rdf:type movie:FeatureFilm ;
          movie:hasTitle ?seedTitle .
    FILTER(CONTAINS(LCASE(?seedTitle), "${safe}"))
    ?seed movie:hasMainGenre ?g .
    ?movie movie:hasMainGenre ?g .
    FILTER(?seed != ?movie)
    BIND(40 AS ?relScore)
    BIND("Comparten género" AS ?relationReason)
  }

  ?movie movie:hasTitle ?title .
  OPTIONAL { ?movie movie:hasDirector/movie:personName ?directorName }
  OPTIONAL { ?movie movie:hasMainGenre/movie:genreName ?genreName }
  OPTIONAL { ?movie movie:hasAverageRating ?rating }
  OPTIONAL { ?movie movie:hasPlotSummary ?description }

  BIND(COALESCE(?baseScore, 0) + COALESCE(?relScore, 0) AS ?matchScore)
}
ORDER BY DESC(?matchScore) DESC(?rating)
LIMIT 36`;
}
