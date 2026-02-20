/**
 * Generates a display-only SPARQL query string for the Explainable AI panel.
 * This is NOT executed — it shows the user what kind of semantic query was run.
 */
export function buildDisplaySparqlQuery(searchTerm: string): string {
  const lowerTerm = searchTerm.toLowerCase();

  return `PREFIX movie: <http://www.movies.org/movie/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT DISTINCT ?movie ?title ?directorName ?genreName ?rating ?description ?matchScore ?relationReason
WHERE {
  # 1. Encontrar la película objetivo (Seed)
  {
    ?seed rdf:type movie:FeatureFilm ;
          movie:hasTitle ?seedTitle .
    FILTER(CONTAINS(LCASE(?seedTitle), "${lowerTerm}"))
    BIND(?seed AS ?movie)
    BIND(200 AS ?baseScore)
    BIND("Coincidencia exacta con tu búsqueda" AS ?relationReason)
  }
  UNION
  # 2. Encontrar películas similares por Director
  {
    ?seed rdf:type movie:FeatureFilm ;
          movie:hasTitle ?seedTitle .
    FILTER(CONTAINS(LCASE(?seedTitle), "${lowerTerm}"))
    
    ?seed movie:hasDirector ?dir . 
    ?dir movie:personName ?sharedDirector .
    ?movie movie:hasDirector ?dir .
    FILTER(?seed != ?movie)
    BIND(80 AS ?relScore)
    BIND(CONCAT("Recomendado porque comparten el director ", ?sharedDirector) AS ?relationReason)
  }
  UNION
  # 3. Encontrar películas similares por Género
  {
    ?seed rdf:type movie:FeatureFilm ;
          movie:hasTitle ?seedTitle .
    FILTER(CONTAINS(LCASE(?seedTitle), "${lowerTerm}"))
    
    ?seed movie:hasMainGenre ?g . 
    ?g movie:genreName ?sharedGenre .
    ?movie movie:hasMainGenre ?g .
    FILTER(?seed != ?movie)
    BIND(40 AS ?relScore)
    BIND(CONCAT("Recomendado porque comparten el género ", ?sharedGenre) AS ?relationReason)
  }

  # 4. Extraer info de la película resultante
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
