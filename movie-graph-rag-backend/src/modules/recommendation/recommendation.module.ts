import { Module } from '@nestjs/common';
import { RecommendationService } from './recommendation.service';
import { RecommendationController } from './recommendation.controller';
import { LlmModule } from '../llm/llm.module';
import { GraphModule } from '../graph/graph.module';

@Module({
  imports: [LlmModule, GraphModule], // Importamos las piezas
  providers: [RecommendationService],
  controllers: [RecommendationController],
})
export class RecommendationModule {}
