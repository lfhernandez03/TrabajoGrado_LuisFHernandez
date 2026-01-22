/* eslint-disable @typescript-eslint/no-unsafe-member-access */
import { Injectable, Logger } from '@nestjs/common';
import { LlmService } from '../llm/llm.service';
import { GraphService } from '../graph/graph.service';

@Injectable()
export class RecommendationService {
  private readonly logger = new Logger(RecommendationService.name);

  constructor(
    private readonly llmService: LlmService,
    private readonly graphService: GraphService,
  ) {}

  async getRecommendation(userQuery: string) {
    const startTime = Date.now();
    try {
      this.logger.log(
        `Iniciando flujo GraphRAG Multi-Ontología para: "${userQuery}"`,
      );

      // PASO 1: Extracción Semántica Enriquecida (LLM -> RDF + Contexto Estructurado)
      this.logger.log('PASO 1: Extrayendo contexto completo del usuario...');
      const extractedContext =
        await this.llmService.extractSemanticContext(userQuery);

      this.logger.log(
        `Contexto extraído: Social=${extractedContext.contextSnapshot.socialContext?.companionType}, ` +
          `Mood=${extractedContext.contextSnapshot.emotionalContext?.moodDescription}, ` +
          `Energía=${extractedContext.contextSnapshot.emotionalContext?.desiredEnergyLevel}, ` +
          `Tiempo=${extractedContext.contextSnapshot.requirementContext?.availableTime}min`,
      );

      // PASO 2: Generación de Consulta SPARQL Multi-Ontología
      this.logger.log('PASO 2: Generando consulta SPARQL multi-ontología...');
      const sparqlQuery = await this.llmService.generateSparqlQuery(
        userQuery,
        extractedContext.contextSnapshot,
      );

      this.logger.log(`Consulta SPARQL generada:\n${sparqlQuery}`);

      // PASO 3: Retrieval (Ejecutar SPARQL contra GraphDB)
      this.logger.log('PASO 3: Ejecutando consulta contra GraphDB...');
      const movies = await this.graphService.executeQuery(sparqlQuery);

      this.logger.log(`Películas encontradas: ${movies.length}`);

      if (movies.length === 0) {
        const executionTimeMs = Date.now() - startTime;
        return {
          query: userQuery,
          contextExtracted: extractedContext.contextSnapshot,
          rdfGenerated: extractedContext.rdfTriples,
          sparqlQuery,
          moviesFound: 0,
          moviesWithScores: [],
          explanation:
            'Lo siento, no encontré películas en el grafo de conocimiento que cumplan con todos tus criterios. ' +
            'Esto puede deberse a restricciones muy específicas (tiempo disponible, géneros excluidos, etc.). ' +
            'Te sugiero: 1) Aumentar el tiempo disponible, 2) Ser más flexible con los géneros, o 3) Ajustar el contexto.',
          executionTimeMs,
        };
      }

      // PASO 4: Cálculo de Compatibility Scores
      this.logger.log('PASO 4: Calculando compatibility scores...');
      const moviesWithScores =
        await this.llmService.calculateCompatibilityScores(
          movies,
          extractedContext.contextSnapshot,
        );

      this.logger.log(
        `Top 3 películas: ${moviesWithScores
          .slice(0, 3)
          .map((m) => `${m.title} (${m.compatibilityScore?.toFixed(2)})`)
          .join(', ')}`,
      );

      // PASO 5: Generación Narrativa Contextualizada
      this.logger.log('PASO 5: Generando respuesta narrativa personalizada...');
      const finalResponse = await this.llmService.generateNarrativeResponse(
        userQuery,
        moviesWithScores,
        extractedContext.contextSnapshot,
      );

      const executionTimeMs = Date.now() - startTime;

      return {
        query: userQuery,
        contextExtracted: extractedContext.contextSnapshot,
        rdfGenerated: extractedContext.rdfTriples,
        sparqlQuery,
        moviesFound: movies.length,
        moviesWithScores: moviesWithScores.slice(0, 5), // Top 5
        explanation: finalResponse,
        executionTimeMs,
      };
    } catch (error) {
      this.logger.error(`Fallo en el orquestador: ${error.message}`);
      throw error;
    }
  }
}
