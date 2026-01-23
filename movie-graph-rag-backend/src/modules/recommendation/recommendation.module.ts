import { Module } from '@nestjs/common';
import { RecommendationService } from './recommendation.service';
import { RecommendationController } from './recommendation.controller';
import { LlmModule } from '../llm/llm.module';
import { GraphModule } from '../graph/graph.module';
import { HistoryModule } from '../history/history.module';

@Module({
  imports: [HistoryModule, LlmModule, GraphModule],
  providers: [RecommendationService],
  controllers: [RecommendationController],
})
export class RecommendationModule {}
