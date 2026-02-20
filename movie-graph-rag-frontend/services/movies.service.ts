import api from '@/lib/api';

export interface Movie {
  uri: string;
  title: string;
  year?: number;
  director?: string;
  genres?: string[];
  description?: string;
  rating?: number;
  relationReason?: string;
}

export interface SearchMovieParams {
  q?: string;
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
export const getMovieExamples = async (limit: number = 3): Promise<Movie[]> => {
  const response = await api.get<Movie[]>('/movies/examples', {
    params: { limit },
  });
  return response.data;
};

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
