import api from '@/lib/api';

export interface HistoryEntry {
  _id: string;
  userId: string;
  query: string;
  rdfGenerated?: string;
  sparqlExecuted?: string;
  contextExtracted?: any;
  resultsFound?: any[];
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

/**
 * Obtiene el detalle de una consulta específica del historial
 */
export const getHistoryDetail = async (id: string): Promise<HistoryEntry | null> => {
  const response = await api.get<HistoryEntry>(`/history/${id}`);
  return response.data;
};
