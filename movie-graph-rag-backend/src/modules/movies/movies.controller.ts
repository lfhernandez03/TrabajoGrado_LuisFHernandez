import { Controller, Get, Query, UseGuards, Request } from '@nestjs/common';
import {
  ApiOperation,
  ApiQuery,
  ApiResponse,
  ApiTags,
  ApiBearerAuth,
} from '@nestjs/swagger';
import { AuthGuard } from '@nestjs/passport';
import { MoviesService } from './movies.service';
import { MovieDto, SearchMovieDto } from './dto/movie.dto';

@ApiTags('movies')
@Controller('movies')
export class MoviesController {
  constructor(private readonly moviesService: MoviesService) {}

  @Get('examples')
  @ApiOperation({
    summary: 'Obtener películas de ejemplo',
    description:
      'Retorna un conjunto de películas de ejemplo para mostrar en la página principal (por defecto 3)',
  })
  @ApiQuery({
    name: 'limit',
    required: false,
    type: Number,
    description: 'Número de películas a retornar',
    example: 3,
  })
  @ApiResponse({
    status: 200,
    description: 'Lista de películas de ejemplo',
    type: [MovieDto],
  })
  async getExamples(@Query('limit') limit?: string): Promise<MovieDto[]> {
    const limitNum = limit ? parseInt(limit) : 3;
    return this.moviesService.getExamples(limitNum);
  }

  @Get('search')
  @UseGuards(AuthGuard('jwt'))
  @ApiBearerAuth()
  @ApiOperation({
    summary: 'Buscar películas',
    description:
      'Permite buscar películas por nombre, género, director, año, etc.',
  })
  @ApiQuery({
    name: 'q',
    required: false,
    type: String,
    description: 'Término de búsqueda general',
    example: 'Inception',
  })
  @ApiQuery({
    name: 'genre',
    required: false,
    type: String,
    description: 'Filtrar por género',
    example: 'Sci-Fi',
  })
  @ApiQuery({
    name: 'director',
    required: false,
    type: String,
    description: 'Filtrar por director',
    example: 'Christopher Nolan',
  })
  @ApiQuery({
    name: 'yearFrom',
    required: false,
    type: Number,
    description: 'Año mínimo',
    example: 2000,
  })
  @ApiQuery({
    name: 'yearTo',
    required: false,
    type: Number,
    description: 'Año máximo',
    example: 2020,
  })
  @ApiQuery({
    name: 'limit',
    required: false,
    type: Number,
    description: 'Límite de resultados',
    example: 10,
  })
  @ApiResponse({
    status: 200,
    description: 'Lista de películas encontradas',
    type: [MovieDto],
  })
  async search(
    @Query() searchDto: SearchMovieDto,
    @Request() req: { user: { userId: string } },
  ): Promise<MovieDto[]> {
    const userId = req.user.userId;
    return this.moviesService.searchMovies(searchDto, userId);
  }
}
