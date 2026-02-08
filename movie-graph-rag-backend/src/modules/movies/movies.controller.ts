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
import {
  ConnectionExplorerDto,
  ConnectionExplorerResponseDto,
} from './dto/connection-explorer.dto';

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

  @Get('autocomplete')
  @UseGuards(AuthGuard('jwt'))
  @ApiBearerAuth()
  @ApiOperation({
    summary: 'Autocompletar títulos de películas',
    description:
      'Busca películas por coincidencia parcial del título para usar en campos de autocompletado.',
  })
  @ApiQuery({
    name: 'q',
    required: true,
    type: String,
    description: 'Término de búsqueda parcial',
    example: 'incep',
  })
  @ApiQuery({
    name: 'limit',
    required: false,
    type: Number,
    description: 'Límite de sugerencias',
    example: 8,
  })
  @ApiResponse({
    status: 200,
    description: 'Lista de sugerencias de películas',
  })
  async autocomplete(
    @Query('q') q: string,
    @Query('limit') limit?: string,
  ) {
    const limitNum = limit ? parseInt(limit) : 8;
    return this.moviesService.autocomplete(q, limitNum);
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

  @Get('connections')
  @UseGuards(AuthGuard('jwt'))
  @ApiBearerAuth()
  @ApiOperation({
    summary: 'Explorador de Conexiones entre películas',
    description:
      'Encuentra el camino semántico entre dos películas en el grafo de conocimiento, explorando relaciones compartidas (director, género, actor).',
  })
  @ApiQuery({
    name: 'from',
    required: true,
    type: String,
    description: 'Película de origen',
    example: 'Inception',
  })
  @ApiQuery({
    name: 'to',
    required: true,
    type: String,
    description: 'Película de destino',
    example: 'Interstellar',
  })
  @ApiQuery({
    name: 'maxDepth',
    required: false,
    type: Number,
    description: 'Grado máximo de separación',
    example: 3,
  })
  @ApiResponse({
    status: 200,
    description: 'Camino de conexión encontrado',
    type: ConnectionExplorerResponseDto,
  })
  async findConnections(
    @Query() connectionDto: ConnectionExplorerDto,
    @Request() req: { user: { userId: string } },
  ): Promise<ConnectionExplorerResponseDto> {
    const userId = req.user.userId;
    return this.moviesService.findConnections(connectionDto, userId);
  }
}
