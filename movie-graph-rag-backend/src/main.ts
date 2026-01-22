import { NestFactory } from '@nestjs/core';
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';
import { AppModule } from './app.module';
import { Logger } from '@nestjs/common';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  const logger = new Logger('Bootstrap');

  // Configuración de la documentación Swagger
  const config = new DocumentBuilder()
    .setTitle('CineSemantico GraphRAG API')
    .setDescription(
      'Motor de recomendaciones basado en Ontologías y LLMs (Tesis)',
    )
    .setVersion('1.0')
    .addTag('recommendation', 'Endpoints para el motor de recomendaciones')
    .build();

  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('api', app, document);

  await app.listen(3000);
  logger.log(`Aplicación corriendo en: http://localhost:3000`);
  logger.log(`Documentación Swagger en: http://localhost:3000/api`);
}
bootstrap();
