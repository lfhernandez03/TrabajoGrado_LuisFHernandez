import { ApiProperty } from '@nestjs/swagger';
import {
  IsArray,
  IsNotEmpty,
  IsNumber,
  IsOptional,
  IsString,
} from 'class-validator';

export class FavoriteMovieDto {
  @ApiProperty({
    description: 'URI única de la película en el grafo',
    example:
      'http://www.semanticweb.org/movierecommendation/data/movie/movie_1_Toy_Story',
  })
  @IsString()
  @IsNotEmpty()
  uri!: string;

  @ApiProperty({
    description: 'Título de la película',
    example: 'Toy Story',
  })
  @IsString()
  @IsNotEmpty()
  title!: string;

  @ApiProperty({ description: 'URL del póster', required: false })
  @IsOptional()
  @IsString()
  posterUrl?: string;

  @ApiProperty({ description: 'Año de lanzamiento', required: false })
  @IsOptional()
  @IsNumber()
  year?: number;

  @ApiProperty({ description: 'Duración en minutos', required: false })
  @IsOptional()
  @IsNumber()
  runtime?: number;

  @ApiProperty({ description: 'Clasificación (PG, R, etc.)', required: false })
  @IsOptional()
  @IsString()
  certification?: string;

  @ApiProperty({ description: 'Director', required: false })
  @IsOptional()
  @IsString()
  director?: string;

  @ApiProperty({ description: 'Géneros', type: [String], required: false })
  @IsOptional()
  @IsArray()
  @IsString({ each: true })
  genres?: string[];

  @ApiProperty({ description: 'Descripción/sinopsis', required: false })
  @IsOptional()
  @IsString()
  description?: string;

  @ApiProperty({ description: 'Rating promedio', required: false })
  @IsOptional()
  @IsNumber()
  rating?: number;

  @ApiProperty({
    description: 'Razón de recomendación si existe',
    required: false,
  })
  @IsOptional()
  @IsString()
  relationReason?: string;
}

export class RemoveFavoriteDto {
  @ApiProperty({
    description: 'URI única de la película a eliminar de favoritos',
    example:
      'http://www.semanticweb.org/movierecommendation/data/movie/movie_1_Toy_Story',
  })
  @IsString()
  @IsNotEmpty()
  uri!: string;
}

export class FavoriteMovieResponseDto {
  @ApiProperty({ description: 'URI única de la película en el grafo' })
  uri!: string;

  @ApiProperty({ description: 'Título de la película' })
  title!: string;

  @ApiProperty({ description: 'URL del póster', required: false })
  posterUrl?: string;

  @ApiProperty({ description: 'Año de lanzamiento', required: false })
  year?: number;

  @ApiProperty({ description: 'Duración en minutos', required: false })
  runtime?: number;

  @ApiProperty({ description: 'Clasificación', required: false })
  certification?: string;

  @ApiProperty({ description: 'Director', required: false })
  director?: string;

  @ApiProperty({ description: 'Géneros', type: [String], required: false })
  genres?: string[];

  @ApiProperty({ description: 'Descripción/sinopsis', required: false })
  description?: string;

  @ApiProperty({ description: 'Rating promedio', required: false })
  rating?: number;

  @ApiProperty({ description: 'Razón de relación', required: false })
  relationReason?: string;

  @ApiProperty({
    description: 'Fecha de agregado a favoritos',
    required: false,
  })
  addedAt?: Date;
}

export class FavoritesResponseDto {
  @ApiProperty({
    description: 'Listado de películas favoritas con datos completos para card',
    type: [FavoriteMovieResponseDto],
  })
  favorites!: FavoriteMovieResponseDto[];
}
