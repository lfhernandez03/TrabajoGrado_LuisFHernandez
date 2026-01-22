import { Controller, Get, Query } from '@nestjs/common';
import { ApiOperation, ApiResponse, ApiTags } from '@nestjs/swagger';
import { RecommendationService } from './recommendation.service';
import { RecommendationRequestDto } from './dto/recommendation-request.dto';

@ApiTags('recommendation')
@Controller('recommendation')
export class RecommendationController {
  constructor(private readonly recService: RecommendationService) {}

  @Get()
  @ApiOperation({ summary: 'Obtener recomendaciones usando el flujo GraphRAG' })
  @ApiResponse({
    status: 200,
    description: 'Recomendación generada exitosamente.',
  })
  @ApiResponse({ status: 500, description: 'Error interno en GraphDB o LLM.' })
  async getRec(@Query() queryDto: RecommendationRequestDto) {
    return await this.recService.getRecommendation(queryDto.query);
  }
}
