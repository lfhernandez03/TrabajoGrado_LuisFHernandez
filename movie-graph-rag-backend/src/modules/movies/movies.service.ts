import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import axios from 'axios';
import { GraphService } from '../graph/graph.service';
import { HistoryService } from '../history/history.service';
import { MovieDto, SearchMovieDto } from './dto/movie.dto';
import {
  ConnectionExplorerDto,
  ConnectionExplorerResponseDto,
  ConnectionNodeDto,
  ConnectionEdgeDto,
  ConnectionPathStepDto,
} from './dto/connection-explorer.dto';
import { NAMESPACES } from '../../common/constants/namespaces';

@Injectable()
export class MoviesService {
  private readonly logger = new Logger(MoviesService.name);

  constructor(
    private readonly graphService: GraphService,
    private readonly historyService: HistoryService,
    private readonly configService: ConfigService,
  ) {}

  private getNormalizedPosterUrl(rawPoster?: string): string | undefined {
    if (!rawPoster) return undefined;
    if (rawPoster.startsWith('http://') || rawPoster.startsWith('https://')) {
      return rawPoster;
    }
    if (rawPoster.startsWith('/')) {
      return `https://image.tmdb.org/t/p/w500${rawPoster}`;
    }
    return rawPoster;
  }

  private async enrichPostersFromTmdb(movies: MovieDto[]): Promise<MovieDto[]> {
    const tmdbApiKey = this.configService.get<string>('TMDB_API_KEY');
    if (!tmdbApiKey || movies.length === 0) {
      return movies;
    }

    const enriched = await Promise.all(
      movies.map(async (movie) => {
        if (movie.posterUrl || !movie.tmdbId) {
          return movie;
        }

        try {
          const response = await axios.get<{ poster_path?: string }>(
            `https://api.themoviedb.org/3/movie/${movie.tmdbId}`,
            {
              params: { api_key: tmdbApiKey },
              timeout: 5000,
            },
          );

          const posterPath = response.data?.poster_path;
          return {
            ...movie,
            posterUrl: posterPath
              ? `https://image.tmdb.org/t/p/w500${posterPath}`
              : undefined,
          };
        } catch {
          return movie;
        }
      }),
    );

    return enriched;
  }

  /**
   * Busca películas por título para autocompletado rápido.
   * Retorna coincidencias parciales ordenadas por relevancia.
   */
  async autocomplete(
    term: string,
    limit: number = 8,
  ): Promise<Array<{ uri: string; title: string; director?: string; year?: string }>> {
    const searchTerm = term.toLowerCase().trim();
    if (searchTerm.length < 2) return [];

    const sparql = `
      PREFIX movie: <${NAMESPACES.MOVIE}>
      PREFIX rdf: <${NAMESPACES.RDF}>

      SELECT DISTINCT ?movie ?title ?directorName
      WHERE {
        ?movie rdf:type movie:FeatureFilm ;
               movie:hasTitle ?title .
        FILTER(CONTAINS(LCASE(?title), "${searchTerm}"))
        OPTIONAL {
          ?movie movie:hasDirector ?dir .
          ?dir movie:personName ?directorName
        }
      }
      ORDER BY STRLEN(?title)
      LIMIT ${limit}
    `;

    try {
      const results = await this.graphService.executeQuery<{
        movie: string;
        title: string;
        directorName?: string;
      }>(sparql);

      // Deduplicar por URI (puede haber múltiples directores)
      const seen = new Set<string>();
      return results
        .filter((r) => {
          if (seen.has(r.movie)) return false;
          seen.add(r.movie);
          return true;
        })
        .map((r) => ({
          uri: r.movie,
          title: r.title,
          director: r.directorName,
        }));
    } catch (error) {
      this.logger.error('Error en autocomplete', error);
      return [];
    }
  }

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
      
      SELECT DISTINCT ?movie ?title ?director ?directorName ?genreName ?rating ?description ?posterUrl ?tmdbId ?releaseDate ?runtime ?certification
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
        OPTIONAL { ?movie movie:hasTMDbID ?tmdbId }
        OPTIONAL { ?movie movie:hasPosterUrl ?posterUrl }
        OPTIONAL { ?movie movie:hasPosterURL ?posterUrl }
        OPTIONAL { ?movie movie:posterUrl ?posterUrl }
        OPTIONAL { ?movie <http://schema.org/image> ?posterUrl }
        OPTIONAL { ?movie movie:releaseDate ?releaseDate }
        OPTIONAL { ?movie movie:runtime ?runtime }
        OPTIONAL { ?movie movie:hasCertification/movie:certificationRating ?certification }
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
        posterUrl?: string;
        tmdbId?: string;
        releaseDate?: string;
        runtime?: string;
        certification?: string;
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
            posterUrl: this.getNormalizedPosterUrl(result.posterUrl),
            tmdbId: result.tmdbId,
            year: result.releaseDate
              ? new Date(result.releaseDate).getFullYear()
              : undefined,
            runtime: result.runtime ? parseInt(result.runtime, 10) : undefined,
            certification: result.certification,
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
      const movies = Array.from(moviesMap.values()).slice(0, limit);
      return this.enrichPostersFromTmdb(movies);
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
      
      SELECT DISTINCT ?movie ?title ?directorName ?genreName ?rating ?description ?posterUrl ?tmdbId ?releaseDate ?runtime ?certification ?matchScore ?relationReason
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
        OPTIONAL { ?movie movie:hasTMDbID ?tmdbId }
        OPTIONAL { ?movie movie:hasPosterUrl ?posterUrl }
        OPTIONAL { ?movie movie:hasPosterURL ?posterUrl }
        OPTIONAL { ?movie movie:posterUrl ?posterUrl }
        OPTIONAL { ?movie <http://schema.org/image> ?posterUrl }
        OPTIONAL { ?movie movie:releaseDate ?releaseDate }
        OPTIONAL { ?movie movie:runtime ?runtime }
        OPTIONAL { ?movie movie:hasCertification/movie:certificationRating ?certification }
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
        posterUrl?: string;
        tmdbId?: string;
        releaseDate?: string;
        runtime?: string;
        certification?: string;
        rating?: string;
        description?: string;
        matchScore?: string;
        relationReason?: string;
      }>(sparql);

      const groupedMovies = this.groupMovieResults(results, limit);
      const movies = await this.enrichPostersFromTmdb(groupedMovies);
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
      posterUrl?: string;
      tmdbId?: string;
      releaseDate?: string;
      runtime?: string;
      certification?: string;
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
          posterUrl: this.getNormalizedPosterUrl(result.posterUrl),
          tmdbId: result.tmdbId,
          year: result.releaseDate
            ? new Date(result.releaseDate).getFullYear()
            : undefined,
          runtime: result.runtime ? parseInt(result.runtime, 10) : undefined,
          certification: result.certification,
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

  /**
   * Encuentra conexiones entre dos películas explorando el grafo.
   * Busca caminos a través de directores, actores y géneros compartidos.
   */
  async findConnections(
    dto: ConnectionExplorerDto,
    userId?: string,
  ): Promise<ConnectionExplorerResponseDto> {
    const startTime = Date.now();
    const maxDepth = dto.maxDepth || 3;
    const fromTerm = dto.from.toLowerCase();
    const toTerm = dto.to.toLowerCase();

    // PASO 1: Obtener las URIs de las películas de origen y destino
    const resolveSparql = `
      PREFIX movie: <${NAMESPACES.MOVIE}>
      PREFIX rdf: <${NAMESPACES.RDF}>

      SELECT ?movie ?title
      WHERE {
        ?movie rdf:type movie:FeatureFilm ;
               movie:hasTitle ?title .
        FILTER(
          CONTAINS(LCASE(?title), "${fromTerm}") ||
          CONTAINS(LCASE(?title), "${toTerm}")
        )
      }
      LIMIT 20
    `;

    try {
      const resolveResults = await this.graphService.executeQuery<{
        movie: string;
        title: string;
      }>(resolveSparql);

      // Encontrar la mejor coincidencia para from y to
      const fromMovie = resolveResults.find((r) =>
        r.title.toLowerCase().includes(fromTerm),
      );
      const toMovie = resolveResults.find((r) =>
        r.title.toLowerCase().includes(toTerm),
      );

      if (!fromMovie || !toMovie) {
        const executionTimeMs = Date.now() - startTime;
        return {
          found: false,
          nodes: [],
          edges: [],
          pathSteps: [],
          distance: 0,
          sparqlQuery: resolveSparql,
          executionTimeMs,
          fromTitle: fromMovie?.title,
          toTitle: toMovie?.title,
        };
      }

      if (fromMovie.movie === toMovie.movie) {
        const executionTimeMs = Date.now() - startTime;
        const node: ConnectionNodeDto = {
          uri: fromMovie.movie,
          label: fromMovie.title,
          type: 'movie',
        };
        return {
          found: true,
          nodes: [node],
          edges: [],
          pathSteps: [
            { step: 1, description: `${fromMovie.title} es la misma película`, node },
          ],
          distance: 0,
          sparqlQuery: resolveSparql,
          executionTimeMs,
          fromTitle: fromMovie.title,
          toTitle: toMovie.title,
        };
      }

      // PASO 2: Buscar conexiones a 1 salto (director, género compartido)
      const connection1Sparql = `
        PREFIX movie: <${NAMESPACES.MOVIE}>
        PREFIX rdf: <${NAMESPACES.RDF}>

        SELECT ?sharedEntity ?sharedLabel ?relType
        WHERE {
          {
            <${fromMovie.movie}> movie:hasDirector ?sharedEntity .
            <${toMovie.movie}> movie:hasDirector ?sharedEntity .
            ?sharedEntity movie:personName ?sharedLabel .
            BIND("director" AS ?relType)
          }
          UNION
          {
            <${fromMovie.movie}> movie:hasMainGenre ?sharedEntity .
            <${toMovie.movie}> movie:hasMainGenre ?sharedEntity .
            ?sharedEntity movie:genreName ?sharedLabel .
            BIND("genre" AS ?relType)
          }
          UNION
          {
            <${fromMovie.movie}> movie:hasActor ?sharedEntity .
            <${toMovie.movie}> movie:hasActor ?sharedEntity .
            ?sharedEntity movie:personName ?sharedLabel .
            BIND("actor" AS ?relType)
          }
        }
      `;

      const direct = await this.graphService.executeQuery<{
        sharedEntity: string;
        sharedLabel: string;
        relType: string;
      }>(connection1Sparql);

      if (direct.length > 0) {
        // Construir path directo
        const result = this.buildDirectPath(
          fromMovie,
          toMovie,
          direct,
          connection1Sparql,
          Date.now() - startTime,
        );

        this.saveConnectionHistory(
          userId,
          dto,
          connection1Sparql,
          result,
          Date.now() - startTime,
        );

        return result;
      }

      // PASO 3: Buscar conexiones a 2 saltos (película intermedia)
      if (maxDepth >= 2) {
        const connection2Sparql = `
          PREFIX movie: <${NAMESPACES.MOVIE}>
          PREFIX rdf: <${NAMESPACES.RDF}>

          SELECT ?intermediateMovie ?intermediateTitle ?sharedEntity1 ?sharedLabel1 ?relType1 ?sharedEntity2 ?sharedLabel2 ?relType2
          WHERE {
            ?intermediateMovie rdf:type movie:FeatureFilm ;
                               movie:hasTitle ?intermediateTitle .
            FILTER(?intermediateMovie != <${fromMovie.movie}> && ?intermediateMovie != <${toMovie.movie}>)

            {
              <${fromMovie.movie}> movie:hasDirector ?sharedEntity1 .
              ?intermediateMovie movie:hasDirector ?sharedEntity1 .
              ?sharedEntity1 movie:personName ?sharedLabel1 .
              BIND("director" AS ?relType1)
            }
            UNION
            {
              <${fromMovie.movie}> movie:hasMainGenre ?sharedEntity1 .
              ?intermediateMovie movie:hasMainGenre ?sharedEntity1 .
              ?sharedEntity1 movie:genreName ?sharedLabel1 .
              BIND("genre" AS ?relType1)
            }
            UNION
            {
              <${fromMovie.movie}> movie:hasActor ?sharedEntity1 .
              ?intermediateMovie movie:hasActor ?sharedEntity1 .
              ?sharedEntity1 movie:personName ?sharedLabel1 .
              BIND("actor" AS ?relType1)
            }

            {
              ?intermediateMovie movie:hasDirector ?sharedEntity2 .
              <${toMovie.movie}> movie:hasDirector ?sharedEntity2 .
              ?sharedEntity2 movie:personName ?sharedLabel2 .
              BIND("director" AS ?relType2)
            }
            UNION
            {
              ?intermediateMovie movie:hasMainGenre ?sharedEntity2 .
              <${toMovie.movie}> movie:hasMainGenre ?sharedEntity2 .
              ?sharedEntity2 movie:genreName ?sharedLabel2 .
              BIND("genre" AS ?relType2)
            }
            UNION
            {
              ?intermediateMovie movie:hasActor ?sharedEntity2 .
              <${toMovie.movie}> movie:hasActor ?sharedEntity2 .
              ?sharedEntity2 movie:personName ?sharedLabel2 .
              BIND("actor" AS ?relType2)
            }
          }
          LIMIT 5
        `;

        const indirect = await this.graphService.executeQuery<{
          intermediateMovie: string;
          intermediateTitle: string;
          sharedEntity1: string;
          sharedLabel1: string;
          relType1: string;
          sharedEntity2: string;
          sharedLabel2: string;
          relType2: string;
        }>(connection2Sparql);

        if (indirect.length > 0) {
          const result = this.buildIndirectPath(
            fromMovie,
            toMovie,
            indirect[0],
            connection2Sparql,
            Date.now() - startTime,
          );

          this.saveConnectionHistory(
            userId,
            dto,
            connection2Sparql,
            result,
            Date.now() - startTime,
          );

          return result;
        }
      }

      // No se encontró conexión
      const executionTimeMs = Date.now() - startTime;
      const noResult: ConnectionExplorerResponseDto = {
        found: false,
        nodes: [
          { uri: fromMovie.movie, label: fromMovie.title, type: 'movie' },
          { uri: toMovie.movie, label: toMovie.title, type: 'movie' },
        ],
        edges: [],
        pathSteps: [],
        distance: -1,
        sparqlQuery: connection1Sparql,
        executionTimeMs,
        fromTitle: fromMovie.title,
        toTitle: toMovie.title,
      };

      this.saveConnectionHistory(
        userId,
        dto,
        connection1Sparql,
        noResult,
        executionTimeMs,
      );

      return noResult;
    } catch (error) {
      this.logger.error('Error buscando conexiones en el grafo', error);
      throw error;
    }
  }

  /**
   * Construye un path directo (1 salto) entre dos películas
   */
  private buildDirectPath(
    fromMovie: { movie: string; title: string },
    toMovie: { movie: string; title: string },
    shared: Array<{
      sharedEntity: string;
      sharedLabel: string;
      relType: string;
    }>,
    sparqlQuery: string,
    executionTimeMs: number,
  ): ConnectionExplorerResponseDto {
    const nodes: ConnectionNodeDto[] = [
      { uri: fromMovie.movie, label: fromMovie.title, type: 'movie' },
    ];
    const edges: ConnectionEdgeDto[] = [];
    const pathSteps: ConnectionPathStepDto[] = [
      {
        step: 1,
        description: fromMovie.title,
        node: { uri: fromMovie.movie, label: fromMovie.title, type: 'movie' },
      },
    ];

    // Usar la primera conexión encontrada (prioridad: director > actor > genre)
    const priorityOrder = ['director', 'actor', 'genre'];
    const sortedShared = [...shared].sort(
      (a, b) =>
        priorityOrder.indexOf(a.relType) - priorityOrder.indexOf(b.relType),
    );
    const best = sortedShared[0];

    const relLabels: Record<string, { fromLabel: string; toLabel: string; property: string }> = {
      director: {
        fromLabel: 'dirigida por',
        toLabel: 'también dirigió',
        property: 'movie:hasDirector',
      },
      actor: {
        fromLabel: 'protagonizada por',
        toLabel: 'también actuó en',
        property: 'movie:hasActor',
      },
      genre: {
        fromLabel: 'pertenece al género',
        toLabel: 'también del género',
        property: 'movie:hasMainGenre',
      },
    };

    const rel = relLabels[best.relType] || relLabels['genre'];
    const nodeType: 'person' | 'genre' =
      best.relType === 'genre' ? 'genre' : 'person';

    nodes.push({
      uri: best.sharedEntity,
      label: best.sharedLabel,
      type: nodeType,
    });
    nodes.push({ uri: toMovie.movie, label: toMovie.title, type: 'movie' });

    edges.push({
      from: fromMovie.movie,
      to: best.sharedEntity,
      label: rel.fromLabel,
      property: rel.property,
    });
    edges.push({
      from: best.sharedEntity,
      to: toMovie.movie,
      label: rel.toLabel,
      property: rel.property,
    });

    pathSteps.push({
      step: 2,
      description: `${rel.fromLabel} ${best.sharedLabel}`,
      node: { uri: best.sharedEntity, label: best.sharedLabel, type: nodeType },
    });
    pathSteps.push({
      step: 3,
      description: `${rel.toLabel} ${toMovie.title}`,
      node: { uri: toMovie.movie, label: toMovie.title, type: 'movie' },
    });

    return {
      found: true,
      nodes,
      edges,
      pathSteps,
      distance: 1,
      sparqlQuery,
      executionTimeMs,
      fromTitle: fromMovie.title,
      toTitle: toMovie.title,
    };
  }

  /**
   * Construye un path indirecto (2 saltos) a través de una película intermedia
   */
  private buildIndirectPath(
    fromMovie: { movie: string; title: string },
    toMovie: { movie: string; title: string },
    connection: {
      intermediateMovie: string;
      intermediateTitle: string;
      sharedEntity1: string;
      sharedLabel1: string;
      relType1: string;
      sharedEntity2: string;
      sharedLabel2: string;
      relType2: string;
    },
    sparqlQuery: string,
    executionTimeMs: number,
  ): ConnectionExplorerResponseDto {
    const relLabels: Record<string, { fromLabel: string; toLabel: string; property: string }> = {
      director: {
        fromLabel: 'dirigida por',
        toLabel: 'también dirigió',
        property: 'movie:hasDirector',
      },
      actor: {
        fromLabel: 'protagonizada por',
        toLabel: 'también actuó en',
        property: 'movie:hasActor',
      },
      genre: {
        fromLabel: 'pertenece al género',
        toLabel: 'también del género',
        property: 'movie:hasMainGenre',
      },
    };

    const rel1 = relLabels[connection.relType1] || relLabels['genre'];
    const rel2 = relLabels[connection.relType2] || relLabels['genre'];
    const nodeType1: 'person' | 'genre' =
      connection.relType1 === 'genre' ? 'genre' : 'person';
    const nodeType2: 'person' | 'genre' =
      connection.relType2 === 'genre' ? 'genre' : 'person';

    const nodes: ConnectionNodeDto[] = [
      { uri: fromMovie.movie, label: fromMovie.title, type: 'movie' },
      {
        uri: connection.sharedEntity1,
        label: connection.sharedLabel1,
        type: nodeType1,
      },
      {
        uri: connection.intermediateMovie,
        label: connection.intermediateTitle,
        type: 'movie',
      },
      {
        uri: connection.sharedEntity2,
        label: connection.sharedLabel2,
        type: nodeType2,
      },
      { uri: toMovie.movie, label: toMovie.title, type: 'movie' },
    ];

    const edges: ConnectionEdgeDto[] = [
      {
        from: fromMovie.movie,
        to: connection.sharedEntity1,
        label: rel1.fromLabel,
        property: rel1.property,
      },
      {
        from: connection.sharedEntity1,
        to: connection.intermediateMovie,
        label: rel1.toLabel,
        property: rel1.property,
      },
      {
        from: connection.intermediateMovie,
        to: connection.sharedEntity2,
        label: rel2.fromLabel,
        property: rel2.property,
      },
      {
        from: connection.sharedEntity2,
        to: toMovie.movie,
        label: rel2.toLabel,
        property: rel2.property,
      },
    ];

    const pathSteps: ConnectionPathStepDto[] = [
      {
        step: 1,
        description: fromMovie.title,
        node: { uri: fromMovie.movie, label: fromMovie.title, type: 'movie' },
      },
      {
        step: 2,
        description: `${rel1.fromLabel} ${connection.sharedLabel1}`,
        node: {
          uri: connection.sharedEntity1,
          label: connection.sharedLabel1,
          type: nodeType1,
        },
      },
      {
        step: 3,
        description: `${rel1.toLabel} ${connection.intermediateTitle}`,
        node: {
          uri: connection.intermediateMovie,
          label: connection.intermediateTitle,
          type: 'movie',
        },
      },
      {
        step: 4,
        description: `${rel2.fromLabel} ${connection.sharedLabel2}`,
        node: {
          uri: connection.sharedEntity2,
          label: connection.sharedLabel2,
          type: nodeType2,
        },
      },
      {
        step: 5,
        description: `${rel2.toLabel} ${toMovie.title}`,
        node: { uri: toMovie.movie, label: toMovie.title, type: 'movie' },
      },
    ];

    return {
      found: true,
      nodes,
      edges,
      pathSteps,
      distance: 2,
      sparqlQuery,
      executionTimeMs,
      fromTitle: fromMovie.title,
      toTitle: toMovie.title,
    };
  }

  /**
   * Guarda la exploración de conexiones en el historial
   */
  private async saveConnectionHistory(
    userId: string | undefined,
    dto: ConnectionExplorerDto,
    sparqlQuery: string,
    result: ConnectionExplorerResponseDto,
    executionTimeMs: number,
  ): Promise<void> {
    if (!userId) return;

    try {
      await this.historyService.createEntry({
        userId,
        query: `Explorador de Conexiones: ${dto.from} → ${dto.to}`,
        sparqlExecuted: sparqlQuery,
        resultsFound: result.pathSteps,
        executionTimeMs,
        wasSuccessful: result.found,
        contextExtracted: dto,
      });
    } catch (error) {
      this.logger.warn('No se pudo guardar conexión en historial', error);
    }
  }
}
