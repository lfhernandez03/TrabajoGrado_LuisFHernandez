import { Module } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';
import { HistoryService } from './history.service';
import { HistoryController } from './history.controller';
import { QueryHistory, QueryHistorySchema } from './schemas/history.schema';

@Module({
  imports: [
    MongooseModule.forFeature([
      { name: QueryHistory.name, schema: QueryHistorySchema },
    ]),
  ],
  controllers: [HistoryController],
  providers: [HistoryService],
  exports: [HistoryService],
})
export class HistoryModule {}
