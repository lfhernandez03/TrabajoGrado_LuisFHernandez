import api from "@/lib/api";
import { Movie } from "@/services/movies.service";

export interface FavoriteMovie extends Movie {
  addedAt?: Date;
}

interface BackendFavoriteMovie extends Movie {
  addedAt?: string;
}

interface FavoritesResponse {
  favorites: BackendFavoriteMovie[];
}

const mapFavoriteMovie = (movie: BackendFavoriteMovie): FavoriteMovie => ({
  ...movie,
  addedAt: movie.addedAt ? new Date(movie.addedAt) : undefined,
});

export const getMyFavorites = async (): Promise<FavoriteMovie[]> => {
  const response = await api.get<FavoritesResponse>("/users/me/favorites");
  return (response.data.favorites || []).map(mapFavoriteMovie);
};

export const addMyFavorite = async (movie: Movie): Promise<FavoriteMovie[]> => {
  const response = await api.post<FavoritesResponse>("/users/me/favorites", {
    uri: movie.uri,
    title: movie.title,
    posterUrl: movie.posterUrl,
    year: movie.year,
    runtime: movie.runtime,
    certification: movie.certification,
    director: movie.director,
    genres: movie.genres || [],
    description: movie.description,
    rating: movie.rating,
    relationReason: movie.relationReason,
  });
  return (response.data.favorites || []).map(mapFavoriteMovie);
};

export const removeMyFavorite = async (uri: string): Promise<FavoriteMovie[]> => {
  const response = await api.delete<FavoritesResponse>("/users/me/favorites", {
    data: { uri },
  });
  return (response.data.favorites || []).map(mapFavoriteMovie);
};
