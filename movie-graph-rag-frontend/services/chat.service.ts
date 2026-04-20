import api from '@/lib/api';
import { withCache, TTL } from '@/lib/cache';

export interface ChatMovieResponse {
  uri?: string;
  title: string;
  posterUrl?: string;
  runtime?: number;
  genreName?: string;
  genres?: string[];
  description?: string;
  director?: string;
  year?: number;
  certification?: string;
  releaseDate?: string;
  averageRating?: number;
  compatibilityScore?: number;
  moodMatchScore?: number;
  socialMatchScore?: number;
  energyMatchScore?: number;
  timeMatchScore?: number;
  kidFriendly?: boolean;
  serendipityScore?: number;
}

export interface ChatResponse {
  session_id: string;
  movies: ChatMovieResponse[];
  explanation: string;
  strategy_used: string;
  context_extracted: {
    mood?: string;
    companion?: string;
    has_children?: boolean;
    energy?: string;
    genres?: string[];
    runtime_max?: number;
    exclusions?: string[];
    confidence?: number;
    time_of_day?: string;
    raw_query?: string;
  };
  sparql_query?: string;
  execution_ms: number;
  turn_count: number;
  metrics?: {
    ild: number;
    graphDiversityScore: number;
    semanticPrecision: number;
    coldStartThreshold: number;
    movieCount: number;
  };
}

// Kept for getActivityRecommendation which uses the single-turn endpoint
export interface ChatRecommendationResponse {
  query: string;
  isColdStart?: boolean;
  contextExtracted?: {
    snapshotID: string;
    userIntent: string;
    socialContext?: {
      companionType: string;
      hasChildren: boolean;
      numberOfPeople?: number;
    };
    emotionalContext?: {
      moodDescription: string;
      desiredEnergyLevel: string;
    };
    requirementContext?: {
      availableTime?: number;
      excludedGenre?: string[];
    };
  };
  rdfGenerated?: string;
  sparqlQuery?: string;
  moviesFound: number;
  moviesWithScores: ChatMovieResponse[];
  explanation: string;
  executionTimeMs: number;
  metrics?: {
    ild: number;
    graphDiversityScore: number;
    semanticPrecision: number;
    coldStartThreshold: number;
    movieCount: number;
  };
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  recommendation?: ChatResponse;
}

export const sendChatConversation = async (
  sessionId: string,
  messages: { role: 'user' | 'assistant'; content: string }[]
): Promise<ChatResponse> => {
  const response = await api.post<ChatResponse>(
    '/recommendation/chat',
    { session_id: sessionId, messages },
    { timeout: 180000 }
  );
  return response.data;
};

export const getActivityRecommendation = (): Promise<ChatRecommendationResponse> =>
  withCache('activity-recommendation', TTL.SHORT, () =>
    api.get<ChatRecommendationResponse>('/recommendation/activity', { timeout: 180000 })
      .then(r => r.data)
  );
