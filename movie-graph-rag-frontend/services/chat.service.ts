import api from '@/lib/api';

export interface ChatRecommendationResponse {
  query: string;
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
  moviesWithScores: {
    title: string;
    posterUrl?: string;
    runtime?: number;
    genreName?: string;
    releaseDate?: string;
    averageRating?: number;
    compatibilityScore?: number;
  }[];
  explanation: string;
  executionTimeMs: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  recommendation?: ChatRecommendationResponse;
}

/**
 * Envía una consulta al endpoint de recomendación y retorna la respuesta
 */
export const sendChatMessage = async (query: string): Promise<ChatRecommendationResponse> => {
  const response = await api.post<ChatRecommendationResponse>('/recommendation', { query }, {
    timeout: 180000, // 3 minutos - el pipeline GraphRAG hace múltiples llamadas LLM
  });
  return response.data;
};

/**
 * Obtiene recomendación personalizada basada en actividad del usuario
 */
export const getActivityRecommendation = async (): Promise<ChatRecommendationResponse> => {
  const response = await api.get<ChatRecommendationResponse>('/recommendation/activity', {
    timeout: 180000,
  });
  return response.data;
};
