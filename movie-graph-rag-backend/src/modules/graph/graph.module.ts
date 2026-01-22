import { Module } from '@nestjs/common';
import { GraphService } from './graph.service';
import { ConfigModule } from '@nestjs/config';

@Module({
  imports: [ConfigModule],
  providers: [GraphService],
  exports: [GraphService],
})
export class GraphModule {}
