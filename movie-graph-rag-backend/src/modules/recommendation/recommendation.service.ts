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
    try {
      this.logger.log(`Iniciando flujo GraphRAG para: "${userQuery}"`);

      // PASO 1: Extracción Semántica (LLM -> RDF)
      const rdfTriples =
        await this.llmService.extractSemanticContext(userQuery);

      // PASO 2: Generación de Consulta SPARQL Dinámica
      const sparqlQuery = await this.llmService.generateSparqlQuery(userQuery);

      this.logger.log(`Consulta SPARQL generada:\n${sparqlQuery}`);

      // PASO 3: Retrieval (Ejecutar SPARQL contra GraphDB)
      const movies = await this.graphService.executeQuery(sparqlQuery);

      this.logger.log(`Películas encontradas: ${movies.length}`);

      // PASO 4: Generación Narrativa (Resultados -> LLM -> Usuario)
      const finalResponse =
        movies.length > 0
          ? await this.llmService.generateNarrativeResponse(userQuery, movies)
          : 'Lo siento, no encontré películas en el grafo de conocimiento que cumplan con tus criterios. Por favor, intenta ajustar tu búsqueda (por ejemplo, cambia el género, la duración máxima, o el contexto).';

      return {
        query: userQuery,
        rdfGenerated: rdfTriples,
        sparqlQuery,
        moviesFound: movies,
        explanation: finalResponse,
      };
    } catch (error) {
      this.logger.error(`Fallo en el orquestador: ${error.message}`);
      throw error;
    }
  }
}
