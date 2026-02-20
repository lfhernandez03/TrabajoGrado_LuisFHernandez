import api from '@/lib/api';

export interface HistoryEntry {
  _id: string;
  userId: string;
  query: string;
  rdfGenerated?: string;
  sparqlExecuted?: string;
  contextExtracted?: Record<string, unknown>;
  resultsFound?: Record<string, unknown>[];
  explanation?: string;
  executionTimeMs?: number;
  wasSuccessful: boolean;
  createdAt: Date;
  updatedAt: Date;
}

/**
 * Obtiene el historial de consultas del usuario autenticado
 */
export const getMyHistory = async (limit?: number): Promise<HistoryEntry[]> => {
  const response = await api.get<HistoryEntry[]>('/history/me', {
    params: limit ? { limit } : undefined,
  });
  return response.data;
};


