import { Injectable, Logger } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { QueryHistory } from './schemas/history.schema';

@Injectable()
export class HistoryService {
  private readonly logger = new Logger(HistoryService.name);

  constructor(
    @InjectModel(QueryHistory.name)
    private readonly historyModel: Model<QueryHistory>,
  ) {}

  /**
   * Guarda una nueva entrada en el historial de recomendaciones.
   */
  async createEntry(data: Partial<QueryHistory>): Promise<QueryHistory> {
    try {
      const newEntry = new this.historyModel(data);
      const savedEntry = await newEntry.save();
      this.logger.log(`Historial guardado para el usuario: ${data.userId}`);
      return savedEntry;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      this.logger.error(`Error al persistir en MongoDB: ${message}`);
      throw error;
    }
  }

  /**
   * Recupera las últimas consultas de un usuario.
   */
  async findByUser(userId: string, limit = 10): Promise<QueryHistory[]> {
    return this.historyModel
      .find({ userId })
      .sort({ createdAt: -1 }) // De más reciente a más antiguo
      .limit(limit)
      .exec();
  }

  /**
   * Obtiene una entrada específica por ID (útil para auditoría de la tesis).
   */
  async findOne(id: string): Promise<QueryHistory | null> {
    return this.historyModel.findById(id).exec();
  }
}
