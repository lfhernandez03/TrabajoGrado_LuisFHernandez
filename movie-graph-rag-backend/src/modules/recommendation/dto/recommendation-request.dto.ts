import { ApiProperty } from '@nestjs/swagger';
import { IsString, IsNotEmpty } from 'class-validator';

/**
 * DTO para la petición de recomendación
 * Solo requiere el query del usuario
 */
export class RecommendationRequestDto {
  @ApiProperty({
    description: 'Consulta del usuario en lenguaje natural',
    example: 'Estoy con mis hijos, tengo 90 minutos, quiero algo divertido',
  })
  @IsString()
  @IsNotEmpty()
  query: string;
}

/**
 * DTO para la respuesta de películas
 */
export class MovieDto {
  @ApiProperty({ description: 'Título de la película' })
  title: string;

  @ApiProperty({ description: 'Duración en minutos', required: false })
  runtime?: number;

  @ApiProperty({ description: 'Nombre del género', required: false })
  genreName?: string;

  @ApiProperty({ description: 'Año de lanzamiento', required: false })
  releaseYear?: number;

  @ApiProperty({
    description: 'Score de compatibilidad (0.0 - 1.0)',
    required: false,
  })
  compatibilityScore?: number;
}

/**
 * DTO para el contexto extraído
 */
export class ContextExtractedDto {
  @ApiProperty()
  snapshotID: string;

  @ApiProperty()
  requestTimestamp: Date;

  @ApiProperty()
  userIntent: string;

  @ApiProperty()
  hourOfDay: number;

  @ApiProperty()
  dayOfWeek: string;

  @ApiProperty({ required: false })
  socialContext?: {
    companionType: string;
    hasChildren: boolean;
    numberOfPeople?: number;
  };

  @ApiProperty({ required: false })
  emotionalContext?: {
    moodDescription: string;
    desiredEnergyLevel: string;
  };

  @ApiProperty({ required: false })
  requirementContext?: {
    availableTime?: number;
    excludedGenre?: string[];
    negativeConstraint?: string[];
  };
}

/**
 * DTO para la respuesta completa de recomendación
 */
export class RecommendationResponseDto {
  @ApiProperty({ description: 'Consulta original del usuario' })
  query: string;

  @ApiProperty({
    description: 'Contexto extraído del usuario',
    type: ContextExtractedDto,
  })
  contextExtracted: ContextExtractedDto;

  @ApiProperty({ description: 'Tripletas RDF generadas en formato Turtle' })
  rdfGenerated: string;

  @ApiProperty({ description: 'Consulta SPARQL ejecutada en GraphDB' })
  sparqlQuery: string;

  @ApiProperty({ description: 'Número de películas encontradas' })
  moviesFound: number;

  @ApiProperty({
    type: [MovieDto],
    description: 'Top 5 películas con scores de compatibilidad',
  })
  moviesWithScores: MovieDto[];

  @ApiProperty({ description: 'Respuesta narrativa personalizada del LLM' })
  explanation: string;

  @ApiProperty({ description: 'Tiempo de ejecución en milisegundos' })
  executionTimeMs: number;
}
