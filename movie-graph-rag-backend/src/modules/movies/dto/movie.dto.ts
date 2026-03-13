import { ApiProperty } from '@nestjs/swagger';

export class MovieDto {
  @ApiProperty({
    description: 'URI única de la película en el grafo',
    example: 'http://www.movies.org/movie/Inception',
  })
  uri: string;

  @ApiProperty({
    description: 'Título de la película',
    example: 'Inception',
  })
  title: string;

  @ApiProperty({
    description: 'URL del póster de la película',
    example: 'https://image.tmdb.org/t/p/w500/abc123.jpg',
    required: false,
  })
  posterUrl?: string;

  @ApiProperty({
    description: 'ID de TMDb de la película',
    example: '550',
    required: false,
  })
  tmdbId?: string;

  @ApiProperty({
    description: 'Año de lanzamiento',
    example: 2010,
    required: false,
  })
  year?: number;

  @ApiProperty({
    description: 'Duración en minutos',
    example: 129,
    required: false,
  })
  runtime?: number;

  @ApiProperty({
    description: 'Clasificación de contenido (ej. PG-13, R)',
    example: 'R',
    required: false,
  })
  certification?: string;

  @ApiProperty({
    description: 'Director de la película',
    example: 'Christopher Nolan',
    required: false,
  })
  director?: string;

  @ApiProperty({
    description: 'Géneros de la película',
    example: ['Sci-Fi', 'Thriller'],
    type: [String],
    required: false,
  })
  genres?: string[];

  @ApiProperty({
    description: 'Descripción o sinopsis',
    example:
      'Un ladrón que roba secretos corporativos mediante tecnología de sueños compartidos.',
    required: false,
  })
  description?: string;

  @ApiProperty({
    description: 'Calificación promedio',
    example: 8.8,
    required: false,
  })
  rating?: number;

  @ApiProperty({
    description: 'Razón de la recomendación (breadcrumb semántico)',
    example: 'Recomendado porque comparten el director Christopher Nolan',
    required: false,
  })
  relationReason?: string;
}

export class SearchMovieDto {
  @ApiProperty({
    description: 'Término de búsqueda (nombre, género, director, etc.)',
    example: 'Christopher Nolan',
    required: false,
  })
  q?: string;

  @ApiProperty({
    description: 'Filtrar por género',
    example: 'Sci-Fi',
    required: false,
  })
  genre?: string;

  @ApiProperty({
    description: 'Filtrar por director',
    example: 'Christopher Nolan',
    required: false,
  })
  director?: string;

  @ApiProperty({
    description: 'Año mínimo de lanzamiento',
    example: 2000,
    required: false,
  })
  yearFrom?: number;

  @ApiProperty({
    description: 'Año máximo de lanzamiento',
    example: 2020,
    required: false,
  })
  yearTo?: number;

  @ApiProperty({
    description: 'Límite de resultados',
    example: 10,
    default: 10,
    required: false,
  })
  limit?: number;
}
