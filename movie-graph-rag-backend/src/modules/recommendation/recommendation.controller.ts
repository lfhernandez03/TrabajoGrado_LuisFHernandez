import {
  Controller,
  Post,
  Body,
  Get,
  Query,
  Request,
  UseGuards,
} from '@nestjs/common';
import {
  ApiBearerAuth,
  ApiOperation,
  ApiResponse,
  ApiTags,
  ApiBody,
} from '@nestjs/swagger';
import { RecommendationService } from './recommendation.service';
import {
  RecommendationRequestDto,
  RecommendationResponseDto,
} from './dto/recommendation-request.dto';

class RecommendationQueryDto {
  query: string;
}
import { AuthGuard } from '@nestjs/passport';

@ApiTags('recommendation')
@ApiBearerAuth()
@Controller('recommendation')
export class RecommendationController {
  constructor(private readonly recService: RecommendationService) {}
  @UseGuards(AuthGuard('jwt'))
  @Get()
  async getRec(
    @Query() queryDto: RecommendationQueryDto,
    @Request() req: { user: { userId: string } },
  ) {
    // req.user contiene el userId que viene del token
    const userId = req.user.userId;
    return await this.recService.getRecommendation(queryDto.query, userId);
  }

  @UseGuards(AuthGuard('jwt'))
  @Post()
  @ApiOperation({
    summary:
      'Obtener recomendaciones personalizadas usando GraphRAG multi-ontología',
    description:
      'Recibe una consulta en lenguaje natural y retorna películas recomendadas basándose en contexto social, emocional y requisitos del usuario.',
  })
  @ApiBody({
    description:
      'Consulta en lenguaje natural para obtener recomendaciones de películas',
    examples: {
      ejemplo1: {
        summary: 'Película de acción para el fin de semana',
        value: {
          query:
            'Quiero ver una película de acción emocionante para ver con amigos este fin de semana',
        },
      },
      ejemplo2: {
        summary: 'Película romántica para pareja',
        value: {
          query: 'Recomiéndame una película romántica para ver con mi pareja',
        },
      },
      ejemplo3: {
        summary: 'Comedia familiar',
        value: {
          query: 'Busco una comedia ligera para ver con mi familia',
        },
      },
    },
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
    @Request() req: { user: { userId: string } },
  ): Promise<RecommendationResponseDto> {
    const userId = req.user.userId;
    return await this.recService.getRecommendation(requestDto.query, userId);
  }
}
