import { Controller, Post, Body } from '@nestjs/common';
import { ApiOperation, ApiResponse, ApiTags } from '@nestjs/swagger';
import { RecommendationService } from './recommendation.service';
import {
  RecommendationRequestDto,
  RecommendationResponseDto,
} from './dto/recommendation-request.dto';

@ApiTags('recommendation')
@Controller('recommendation')
export class RecommendationController {
  constructor(private readonly recService: RecommendationService) {}

  @Post()
  @ApiOperation({
    summary:
      'Obtener recomendaciones personalizadas usando GraphRAG multi-ontología',
    description:
      'Recibe una consulta en lenguaje natural y retorna películas recomendadas basándose en contexto social, emocional y requisitos del usuario.',
  })
  @ApiResponse({
    status: 200,
    description: 'Recomendación generada exitosamente.',
    type: RecommendationResponseDto,
  })
  @ApiResponse({ status: 400, description: 'Petición inválida.' })
  @ApiResponse({ status: 500, description: 'Error interno en GraphDB o LLM.' })
  async getRecommendation(
    @Body() requestDto: RecommendationRequestDto,
  ): Promise<RecommendationResponseDto> {
    return await this.recService.getRecommendation(requestDto.query);
  }
}
