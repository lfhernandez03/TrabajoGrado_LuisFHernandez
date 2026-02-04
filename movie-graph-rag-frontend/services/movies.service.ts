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
  genre?: string;
  director?: string;
  yearFrom?: number;
  yearTo?: number;
  limit?: number;
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
 * Busca películas según diferentes criterios
 */
export const searchMovies = async (
  params: SearchMovieParams
): Promise<Movie[]> => {
  const response = await api.get<Movie[]>('/movies/search', { params });
  return response.data;
};
