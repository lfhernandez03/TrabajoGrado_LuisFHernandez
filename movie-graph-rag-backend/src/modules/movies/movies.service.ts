import { Injectable, Logger } from '@nestjs/common';
import { GraphService } from '../graph/graph.service';
import { HistoryService } from '../history/history.service';
import { MovieDto, SearchMovieDto } from './dto/movie.dto';
import { NAMESPACES } from '../../common/constants/namespaces';

@Injectable()
export class MoviesService {
  private readonly logger = new Logger(MoviesService.name);

  constructor(
    private readonly graphService: GraphService,
    private readonly historyService: HistoryService,
  ) {}

  /**
   * Obtiene películas de ejemplo para mostrar en la página principal
   * @param limit Número de películas a retornar (por defecto 3)
   */
  async getExamples(limit: number = 9): Promise<MovieDto[]> {
    // Pedimos más resultados porque habrá duplicados por múltiples géneros
    const sparqlLimit = limit * 4;

    const sparql = `
      PREFIX movie: <${NAMESPACES.MOVIE}>
      PREFIX rdf: <${NAMESPACES.RDF}>
      PREFIX rdfs: <${NAMESPACES.RDFS}>
      PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
      
      SELECT DISTINCT ?movie ?title ?director ?directorName ?genreName ?rating ?description
      WHERE {
        ?movie rdf:type movie:FeatureFilm ;
               movie:hasTitle ?title .
        
        OPTIONAL { 
          ?movie movie:hasDirector ?director .
          ?director movie:personName ?directorName 
        }
        OPTIONAL { 
          ?movie movie:hasMainGenre ?genre .
          ?genre movie:genreName ?genreName
        }
        OPTIONAL { ?movie movie:hasAverageRating ?rating }
        OPTIONAL { ?movie movie:hasPlotSummary ?description }
        
        # Solo películas con rating para asegurar calidad mínima
        FILTER(BOUND(?rating) && ?rating >= 4.0)
      }
      ORDER BY RAND()
      LIMIT ${sparqlLimit}
    `;

    try {
      const results = await this.graphService.executeQuery<{
        movie: string;
        title: string;
        director?: string;
        directorName?: string;
        genreName?: string;
        rating?: string;
        description?: string;
      }>(sparql);

      // Agrupar resultados por película (ya que puede haber múltiples géneros)
      const moviesMap = new Map<string, MovieDto>();

      for (const result of results) {
        if (!moviesMap.has(result.movie)) {
          moviesMap.set(result.movie, {
            uri: result.movie,
            title: result.title,
            director: result.directorName,
            genres: result.genreName ? [result.genreName] : [],
            rating: result.rating ? parseFloat(result.rating) : undefined,
            description: result.description,
          });
        } else if (result.genreName) {
          // Agregar género adicional
          const movie = moviesMap.get(result.movie)!;
          if (!movie.genres?.includes(result.genreName)) {
            movie.genres?.push(result.genreName);
          }
        }
      }

      // Limitar a la cantidad solicitada después de agrupar
      return Array.from(moviesMap.values()).slice(0, limit);
    } catch (error) {
      this.logger.error('Error obteniendo películas de ejemplo', error);
      throw error;
    }
  }

  /**
   * Busca películas según diferentes criterios y retorna películas similares
   * usando exploración de relaciones en el grafo (director, género)
   */
  async searchMovies(
    searchDto: SearchMovieDto,
    userId?: string,
  ): Promise<MovieDto[]> {
    const startTime = Date.now();
    const limit = searchDto.limit || 10;
    const searchTerm = searchDto.q?.toLowerCase() || '';
    const sparqlLimit = limit * 4;

    // Query con UNION para encontrar película objetivo y similares por relaciones
    const sparql = `
      PREFIX movie: <${NAMESPACES.MOVIE}>
      PREFIX rdf: <${NAMESPACES.RDF}>
      
      SELECT DISTINCT ?movie ?title ?directorName ?genreName ?rating ?description ?matchScore ?relationReason
      WHERE {
        # 1. Encontrar la película objetivo (Seed)
        {
          ?seed rdf:type movie:FeatureFilm ;
                movie:hasTitle ?seedTitle .
          FILTER(CONTAINS(LCASE(?seedTitle), "${searchTerm}"))
          BIND(?seed AS ?movie)
          BIND(200 AS ?baseScore)
          BIND("Coincidencia exacta con tu búsqueda" AS ?relationReason)
        }
        UNION
        # 2. Encontrar películas similares por Director
        {
          ?seed rdf:type movie:FeatureFilm ;
                movie:hasTitle ?seedTitle .
          FILTER(CONTAINS(LCASE(?seedTitle), "${searchTerm}"))
          
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
          FILTER(CONTAINS(LCASE(?seedTitle), "${searchTerm}"))
          
          ?seed movie:hasMainGenre ?g . 
          ?g movie:genreName ?sharedGenre .
          ?movie movie:hasMainGenre ?g .
          FILTER(?seed != ?movie)
          BIND(40 AS ?relScore)
          BIND(CONCAT("Recomendado porque comparten el género ", ?sharedGenre) AS ?relationReason)
        }

        # 4. Extraer info de la película resultante (?movie)
        ?movie movie:hasTitle ?title .
        OPTIONAL { ?movie movie:hasDirector/movie:personName ?directorName }
        OPTIONAL { ?movie movie:hasMainGenre/movie:genreName ?genreName }
        OPTIONAL { ?movie movie:hasAverageRating ?rating }
        OPTIONAL { ?movie movie:hasPlotSummary ?description }

        # Filtros adicionales opcionales
        ${searchDto.genre ? `FILTER (CONTAINS(LCASE(STR(?genreName)), LCASE("${searchDto.genre}")))` : ''}
        ${searchDto.director ? `FILTER (CONTAINS(LCASE(STR(?directorName)), LCASE("${searchDto.director}")))` : ''}

        BIND(COALESCE(?baseScore, 0) + COALESCE(?relScore, 0) AS ?matchScore)
      }
      ORDER BY DESC(?matchScore) DESC(?rating)
      LIMIT ${sparqlLimit}
    `;

    try {
      const results = await this.graphService.executeQuery<{
        movie: string;
        title: string;
        directorName?: string;
        genreName?: string;
        rating?: string;
        description?: string;
        matchScore?: string;
        relationReason?: string;
      }>(sparql);

      const movies = this.groupMovieResults(results, limit);
      const executionTime = Date.now() - startTime;

      // Guardar en historial si hay un usuario autenticado
      if (userId) {
        try {
          await this.historyService.createEntry({
            userId,
            query: searchDto.q || 'Búsqueda de películas',
            sparqlExecuted: sparql,
            resultsFound: movies,
            executionTimeMs: executionTime,
            wasSuccessful: true,
            contextExtracted: searchDto,
          });
        } catch (error) {
          this.logger.warn('No se pudo guardar en el historial', error);
          // No lanzar error, solo advertir
        }
      }

      return movies;
    } catch (error) {
      this.logger.error('Error buscando películas', error);

      // Guardar error en historial si hay usuario
      if (userId) {
        try {
          await this.historyService.createEntry({
            userId,
            query: searchDto.q || 'Búsqueda de películas',
            sparqlExecuted: sparql,
            resultsFound: [],
            executionTimeMs: Date.now() - startTime,
            wasSuccessful: false,
            contextExtracted: searchDto,
          });
        } catch (histError) {
          this.logger.warn('No se pudo guardar error en historial', histError);
        }
      }

      throw error;
    }
  }

  /**
   * Agrupa resultados de películas por URI para manejar múltiples géneros
   */
  private groupMovieResults(
    results: Array<{
      movie: string;
      title: string;
      director?: string;
      directorName?: string;
      genreName?: string;
      rating?: string;
      description?: string;
      relationReason?: string;
    }>,
    limit: number,
  ): MovieDto[] {
    const moviesMap = new Map<string, MovieDto>();

    for (const result of results) {
      if (!moviesMap.has(result.movie)) {
        moviesMap.set(result.movie, {
          uri: result.movie,
          title: result.title,
          director: result.directorName,
          genres: result.genreName ? [result.genreName] : [],
          rating: result.rating ? parseFloat(result.rating) : undefined,
          description: result.description,
          relationReason: result.relationReason,
        });
      } else if (result.genreName) {
        const movie = moviesMap.get(result.movie)!;
        if (!movie.genres?.includes(result.genreName)) {
          movie.genres?.push(result.genreName);
        }
      }
    }

    return Array.from(moviesMap.values()).slice(0, limit);
  }
}
