import api from '@/lib/api';

export interface ClusterMovie {
  title: string;
  rating: number | null;
  imdbRating?: number | null;
  genre: string | null;
  posterUrl: string | null;
  runtime?: number | null;
  description?: string | null;
  director?: string | null;
}

export interface ClusterInfo {
  id: string;
  label: string;
  size: number;
  dominantGenres: string[];
}

export interface AdjacentCluster {
  clusterId: string;
  label: string;
  sharedGenres: string[];
  bridgeMovies: ClusterMovie[];
}

export interface MovieClusterResponse {
  movie: string;
  cluster: ClusterInfo;
  intraCluster: ClusterMovie[];
  adjacentClusters: AdjacentCluster[];
}

export interface ClusterListItem {
  clusterId: string;
  label: string;
  size: number;
  exampleMovies: string[];
}

export interface ClusterListResponse {
  clusters: ClusterListItem[];
  total: number;
}

export const getMovieCluster = async (title: string): Promise<MovieClusterResponse> => {
  const response = await api.get<MovieClusterResponse>(
    `/movies/${encodeURIComponent(title)}/cluster`
  );
  return response.data;
};

export const listClusters = async (): Promise<ClusterListResponse> => {
  const response = await api.get<ClusterListResponse>('/clusters');
  return response.data;
};
