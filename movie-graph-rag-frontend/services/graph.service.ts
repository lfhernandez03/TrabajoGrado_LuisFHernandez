import api from '@/lib/api';

export interface GraphSummary {
  totalMovies: number;
  totalEdges: number;
  averageDegree: number;
  averageClusteringCoefficient: number;
  communityCount: number;
  modularity: number;
  isSmallWorld: boolean;
}

export interface CentralityEntry {
  title: string;
  value: number;
  genre: string | null;
}

export interface ClusterEntry {
  clusterId: string;
  label: string;
  size: number;
}

export interface GraphTopologyResponse {
  graphSummary: GraphSummary;
  topByDegree: CentralityEntry[];
  topByBetweenness: CentralityEntry[];
  topByPageRank: CentralityEntry[];
  clusterSummary: ClusterEntry[];
}

export const getGraphTopology = async (): Promise<GraphTopologyResponse> => {
  const response = await api.get<GraphTopologyResponse>('/graph/topology');
  return response.data;
};
