import api from '@/lib/api';
import { withCache, TTL } from '@/lib/cache';

export interface Movie {
  uri: string;
  title: string;
  posterUrl?: string;
  year?: number;
  runtime?: number;
  certification?: string;
  director?: string;
  genres?: string[];
  description?: string;
  rating?: number;
  relationReason?: string;
}

export interface SearchMovieParams {
  q?: string;
  genre?: string;
  director?: string;
  yearFrom?: number;
  yearTo?: number;
  limit?: number;
}

// ===== Connection Explorer Types =====

export interface ConnectionNode {
  uri: string;
  label: string;
  type: 'movie' | 'person' | 'genre';
}

export interface ConnectionEdge {
  from: string;
  to: string;
  label: string;
  property: string;
}

export interface ConnectionPathStep {
  step: number;
  description: string;
  node: ConnectionNode;
}

export interface ConnectionExplorerParams {
  from: string;
  to: string;
  maxDepth?: number;
}

export interface ConnectionExplorerResponse {
  found: boolean;
  nodes: ConnectionNode[];
  edges: ConnectionEdge[];
  pathSteps: ConnectionPathStep[];
  distance: number;
  sparqlQuery: string;
  executionTimeMs: number;
  fromTitle?: string;
  toTitle?: string;
}

// ===== Autocomplete Types =====

export interface MovieSuggestion {
  uri: string;
  title: string;
  director?: string;
}

/**
 * Obtiene películas de ejemplo para mostrar en la página principal
 */
export const getMovieExamples = (limit: number = 3): Promise<Movie[]> =>
  withCache(`examples:${limit}`, TTL.LONG, () =>
    api.get<Movie[]>('/movies/examples', { params: { limit } }).then(r => r.data)
  );

/**
 * Autocompletado de títulos de películas
 */
export const autocompleteMovies = async (
  q: string,
  limit: number = 8
): Promise<MovieSuggestion[]> => {
  if (q.trim().length < 2) return [];
  const response = await api.get<MovieSuggestion[]>('/movies/autocomplete', {
    params: { q, limit },
  });
  return response.data;
};

/**
 * Busca películas según diferentes criterios
 */
export const searchMovies = async (
  params: SearchMovieParams
): Promise<Movie[]> => {
  const response = await api.get<Movie[]>('/movies/search', { params });
  return response.data;
};

/**
 * Explora conexiones entre dos películas en el grafo de conocimiento
 */
export const findConnections = async (
  params: ConnectionExplorerParams
): Promise<ConnectionExplorerResponse> => {
  const response = await api.get<ConnectionExplorerResponse>(
    '/movies/connections',
    { params }
  );
  return response.data;
};

// ===== Phase 5/6 — Connections v2 (neighborhood, centrality, path) =====

export interface RecommendedMovie {
  title: string;
  posterUrl?: string | null;
  runtime?: number | null;
  genreName?: string | null;
  genres?: string[];
  director?: string | null;
  year?: number | null;
  releaseDate?: string | null;
  averageRating?: number | null;
  compatibilityScore?: number;
  serendipityScore?: number;
  description?: string | null;
}

export interface CentralityResponse {
  genre: string | null;
  movies: RecommendedMovie[];
  total: number;
}

export interface NetworkNode {
  uri: string;
  title: string;
  genre?: string | null;
  rating?: number | null;
  posterUrl?: string | null;
  description?: string | null;
  runtime?: number | null;
  director?: string | null;
  year?: number | null;
}

export interface NetworkEdge {
  source_uri: string;
  target_uri: string;
  relation: string; // "same_director" | "same_genre"
}

export interface NetworkGraphResponse {
  center_title: string;
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  node_count: number;
  edge_count: number;
}

export interface ConnectionHop {
  from_title: string;
  to_title: string;
  relation: string; // "same_director" | "same_genre" | "same_mood_profile"
}

export interface ConnectionPathResponse {
  source: string;
  target: string;
  found: boolean;
  hops: ConnectionHop[];
  length: number;
}

export interface ClusterMovie {
  title: string;
  rating?: number | null;
  genres: string[];
  posterUrl?: string | null;
  runtime?: number | null;
}

/** Movies ranked by graph centrality (most "connected" in the knowledge graph) */
export const getMoviesByCentrality = (
  genre?: string,
  limit = 12
): Promise<CentralityResponse> =>
  withCache(`centrality:${genre ?? ''}:${limit}`, TTL.MED, () =>
    api.get<CentralityResponse>('/movies/connections/centrality', {
      params: { ...(genre ? { genre } : {}), limit },
    }).then(r => r.data)
  );

/** Neighbourhood graph around a movie (for GraphMinimap) */
export const getMovieNeighborhood = (
  title: string,
  depth = 1
): Promise<NetworkGraphResponse> =>
  withCache(`neighborhood:${title}:${depth}`, TTL.MED, () =>
    api.get<NetworkGraphResponse>('/movies/connections/neighborhood', {
      params: { title, depth },
    }).then(r => r.data)
  );

/** Shortest semantic path between two movies */
export const getConnectionPath = async (
  source: string,
  target: string
): Promise<ConnectionPathResponse> => {
  const response = await api.get<ConnectionPathResponse>('/movies/connections/path', {
    params: { source, target },
  });
  return response.data;
};

/** Get user's topological profile (unexplored clusters, dominant genres, etc) */
export const getTopologicalProfile = async () => {
  const response = await api.get('/users/me/topology');
  return response.data;
};

/** Get movies from a specific cluster (for exploring unexplored clusters) */
export const getClusterMovies = (
  clusterId: string,
  limit = 12
): Promise<{ cluster_id: string; movies: ClusterMovie[] }> =>
  api.get(`/clusters/${clusterId}/movies`, {
    params: { limit },
  }).then(r => r.data);
