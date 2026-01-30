import { NestFactory } from '@nestjs/core';
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';
import { AppModule } from './app.module';
import { Logger } from '@nestjs/common';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  const logger = new Logger('Bootstrap');

  // Habilitar CORS
  app.enableCors({
    origin: ['http://localhost:3001', 'http://localhost:3000'],
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization'],
  });

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

  const port = process.env.PORT || 3000;
  await app.listen(port);
  logger.log(`Aplicación corriendo en: http://localhost:${port}`);
  logger.log(`Documentación Swagger en: http://localhost:${port}/api`);
}
bootstrap();
