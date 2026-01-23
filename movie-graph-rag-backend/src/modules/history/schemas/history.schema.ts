import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { Document } from 'mongoose';

@Schema({ timestamps: true }) // Genera automáticamente createdAt y updatedAt
export class QueryHistory extends Document {
  @Prop({ required: true, index: true }) // Indexado para búsquedas rápidas por usuario
  userId: string;

  @Prop({ required: true })
  query: string;

  @Prop()
  rdfGenerated: string; // El Turtle generado por el LLM

  @Prop()
  sparqlExecuted: string; // La consulta final a GraphDB

  @Prop({ type: Object })
  contextExtracted: any; // El snapshot del contexto (social, emocional, etc.)

  @Prop({ type: Array })
  resultsFound: any[]; // Top películas recomendadas con sus scores

  @Prop()
  explanation: string; // La respuesta narrativa final

  @Prop()
  executionTimeMs: number; // Métrica de rendimiento para tu tesis

  @Prop({ default: true })
  wasSuccessful: boolean; // Útil para filtrar errores en tus estadísticas

  @Prop()
  createdAt?: Date;

  @Prop()
  updatedAt?: Date;
}

export const QueryHistorySchema = SchemaFactory.createForClass(QueryHistory);
