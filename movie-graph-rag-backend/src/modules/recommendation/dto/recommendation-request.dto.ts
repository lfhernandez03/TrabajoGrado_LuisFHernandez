import { ApiProperty } from '@nestjs/swagger';
import { IsString, MinLength } from 'class-validator';

export class RecommendationRequestDto {
  @ApiProperty({
    description: 'Consulta del usuario en lenguaje natural',
    example:
      'Busco una película de acción de menos de 2 horas para ver en pareja',
  })
  @IsString()
  @MinLength(5)
  query: string;
}
