import { ApiProperty } from '@nestjs/swagger';

export class ConnectionExplorerDto {
  @ApiProperty({
    description: 'Título o término de búsqueda de la película de origen',
    example: 'Inception',
  })
  from: string;

  @ApiProperty({
    description: 'Título o término de búsqueda de la película de destino',
    example: 'Interstellar',
  })
  to: string;

  @ApiProperty({
    description: 'Grado máximo de separación (saltos en el grafo)',
    example: 3,
    default: 3,
    required: false,
  })
  maxDepth?: number;
}

export class ConnectionNodeDto {
  @ApiProperty({
    description: 'URI del nodo en el grafo',
    example: 'http://www.movies.org/movie/Inception',
  })
  uri: string;

  @ApiProperty({
    description: 'Etiqueta legible del nodo',
    example: 'Inception',
  })
  label: string;

  @ApiProperty({
    description: 'Tipo del nodo: movie, person, genre',
    example: 'movie',
  })
  type: 'movie' | 'person' | 'genre';
}

export class ConnectionEdgeDto {
  @ApiProperty({
    description: 'URI del nodo de origen',
    example: 'http://www.movies.org/movie/Inception',
  })
  from: string;

  @ApiProperty({
    description: 'URI del nodo de destino',
    example: 'http://www.movies.org/person/ChristopherNolan',
  })
  to: string;

  @ApiProperty({
    description: 'Etiqueta de la relación',
    example: 'dirigida por',
  })
  label: string;

  @ApiProperty({
    description: 'Propiedad RDF de la relación',
    example: 'movie:hasDirector',
  })
  property: string;
}

export class ConnectionPathStepDto {
  @ApiProperty({ description: 'Número del paso (1-based)' })
  step: number;

  @ApiProperty({ description: 'Descripción legible del paso' })
  description: string;

  @ApiProperty({ description: 'Nodo involucrado en este paso' })
  node: ConnectionNodeDto;
}

export class ConnectionExplorerResponseDto {
  @ApiProperty({
    description: 'Si se encontró una conexión entre las dos entidades',
  })
  found: boolean;

  @ApiProperty({
    description: 'Nodos del grafo en el camino',
    type: [ConnectionNodeDto],
  })
  nodes: ConnectionNodeDto[];

  @ApiProperty({
    description: 'Aristas (relaciones) del camino',
    type: [ConnectionEdgeDto],
  })
  edges: ConnectionEdgeDto[];

  @ApiProperty({
    description: 'Pasos narrativos del camino',
    type: [ConnectionPathStepDto],
  })
  pathSteps: ConnectionPathStepDto[];

  @ApiProperty({
    description: 'Distancia total (número de saltos)',
  })
  distance: number;

  @ApiProperty({
    description: 'Consulta SPARQL utilizada',
  })
  sparqlQuery: string;

  @ApiProperty({
    description: 'Tiempo de ejecución en milisegundos',
  })
  executionTimeMs: number;

  @ApiProperty({
    description: 'Título de la película de origen encontrada',
    required: false,
  })
  fromTitle?: string;

  @ApiProperty({
    description: 'Título de la película de destino encontrada',
    required: false,
  })
  toTitle?: string;
}
