import api from '@/lib/api';

// ── TopologicalProfileResponse ──────────────────────────────────────────────

export interface ClusterWeight {
  clusterId: string;
  label: string;
  /** Fraction of the user's favorites in this cluster [0, 1] */
  weight: number;
  moviesSeen: number;
}

export interface UnexploredCluster {
  clusterId: string;
  label: string;
  /** Graph distance to dominant cluster (always 1) */
  distanceToDominant: number;
}

export interface TopologicalProfileResponse {
  userId: string;
  /** Shannon entropy normalized [0, 1]. 0 = specialist, 1 = explorer */
  explorationIndex: number;
  /** 'especialista' | 'equilibrado' | 'explorador' */
  userType: 'especialista' | 'equilibrado' | 'explorador';
  dominantClusters: ClusterWeight[];
  unexploredAdjacent: UnexploredCluster[];
  /** 'specializing' | 'diversifying' | 'stable' */
  temporalTrend: 'specializing' | 'diversifying' | 'stable';
  trendExplanation: string;
  totalFavorites: number;
  clusteredFavorites: number;
}

export const getUserTopology = async (): Promise<TopologicalProfileResponse> => {
  const response = await api.get<TopologicalProfileResponse>('/users/me/topology');
  return response.data;
};
