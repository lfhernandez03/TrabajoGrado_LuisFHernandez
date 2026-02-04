import { Module } from '@nestjs/common';
import { MoviesController } from './movies.controller';
import { MoviesService } from './movies.service';
import { GraphModule } from '../graph/graph.module';
import { HistoryModule } from '../history/history.module';

@Module({
  imports: [GraphModule, HistoryModule],
  controllers: [MoviesController],
  providers: [MoviesService],
  exports: [MoviesService],
})
export class MoviesModule {}
