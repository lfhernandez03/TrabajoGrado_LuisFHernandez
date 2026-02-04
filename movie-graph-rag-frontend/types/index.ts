export interface Movie {
  title: string;
  runtime: number;
  genreName: string;
  compatibilityScore: number;
}

export interface MovieDetail {
  uri: string;
  title: string;
  year?: number;
  director?: string;
  genres?: string[];
  description?: string;
  rating?: number;
}

export interface RecommendationResponse {
  query: string;
  explanation: string;
  moviesWithScores: Movie[];
  rdfGenerated: string;
  sparqlQuery: string;
  executionTimeMs: number;
}