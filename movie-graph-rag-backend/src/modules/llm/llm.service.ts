import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { ChatGroq } from '@langchain/groq';
import { ChatPromptTemplate } from '@langchain/core/prompts';
import { StringOutputParser } from '@langchain/core/output_parsers';

@Injectable()
export class LlmService {
  private readonly logger = new Logger(LlmService.name);
  private readonly model: ChatGroq;

  constructor(private configService: ConfigService) {
    this.model = new ChatGroq({
      apiKey: this.configService.get<string>('GROQ_API_KEY'),
      model: 'llama-3.3-70b-versatile',
      temperature: 0.1, // Baja para evitar alucinaciones en RDF
    });
  }

  /**
   * Paso 1: Extrae entidades y genera tripletas RDF del prompt del usuario.
   */
  async extractSemanticContext(query: string): Promise<string> {
    const prompt = ChatPromptTemplate.fromTemplate(`
      Eres un experto en Ontologías de Cine y Web Semántica.
      Tu tarea es transformar la consulta de un usuario en tripletas RDF (formato Turtle).

      CONSULTA: "{query}"

      REGLAS ESTRICTAS:
      1. Usa el prefijo "context:" para datos del usuario.
      2. Usa el prefijo "movie:" para géneros (Action, Comedy, Drama).
      3. Extrae: Géneros, Tiempo disponible y Mood.
      4. Responde ÚNICAMENTE con las tripletas en formato Turtle. No des explicaciones.
    `);

    const chain = prompt.pipe(this.model).pipe(new StringOutputParser());

    this.logger.log('Generando contexto RDF con Groq...');
    return await chain.invoke({ query });
  }

  /**
   * Genera una consulta SPARQL dinámica basada en la petición del usuario.
   */
  async generateSparqlQuery(userQuery: string): Promise<string> {
    const prompt = ChatPromptTemplate.fromTemplate(`
      Eres un experto en SPARQL y ontologías de cine.
      
      ONTOLOGÍA DISPONIBLE:
      - Namespace: PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>
      - Clases: movie:Movie, movie:Genre
      - Propiedades:
        * movie:hasTitle (DatatypeProperty - string del título)
        * movie:runtime (DatatypeProperty - integer en minutos)
        * movie:hasGenre (ObjectProperty - enlaza a Genre)
        * movie:genreName (DatatypeProperty del Genre - string como "Action", "Comedy", etc.)
        * movie:releaseYear (DatatypeProperty - integer)
        
      CONSULTA DEL USUARIO: "{query}"
      
      TAREA:
      Genera una consulta SPARQL SELECT que devuelva películas relevantes.
      
      REGLAS:
      1. Usa FILTER para filtrar por runtime si el usuario menciona duración (ej: "menos de 2 horas" = FILTER(?runtime < 120))
      2. Usa FILTER con CONTAINS o regex para buscar géneros (ej: "acción" busca CONTAINS(LCASE(?genreName), "action"))
      3. SIEMPRE selecciona: ?title ?runtime ?genreName
      4. LIMITA a máximo 5 resultados con LIMIT 5
      5. Responde SOLO con la consulta SPARQL, sin explicaciones ni markdown
      
      EJEMPLO:
      Para "películas de comedia cortas":
      PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>
      PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
      SELECT DISTINCT ?title ?runtime ?genreName WHERE {{
        ?m rdf:type movie:Movie ;
           movie:hasTitle ?title ;
           movie:runtime ?runtime ;
           movie:hasGenre ?g .
        ?g movie:genreName ?genreName .
        FILTER(CONTAINS(LCASE(?genreName), "comedy"))
        FILTER(?runtime < 100)
      }} ORDER BY ?runtime LIMIT 5
    `);

    const chain = prompt.pipe(this.model).pipe(new StringOutputParser());

    this.logger.log('Generando consulta SPARQL dinámica...');
    const sparqlQuery = await chain.invoke({ query: userQuery });

    // Limpiar posibles bloques de código markdown
    return sparqlQuery
      .replace(/```sparql\n?/g, '')
      .replace(/```\n?/g, '')
      .trim();
  }

  /**
   * Paso 2: Genera la respuesta final al usuario basándose en los datos reales del grafo.
   */
  async generateNarrativeResponse(
    query: string,
    movieResults: any[],
  ): Promise<string> {
    const movieData = JSON.stringify(movieResults);

    const prompt = ChatPromptTemplate.fromTemplate(`
      Eres un experto recomendador de cine.
      
      REGLAS ESTRICTAS:
      1. Solo puedes recomendar las películas que aparecen en estos datos: {movieData}
      2. NUNCA inventes, sugieras o menciones películas que no estén en los datos proporcionados.
      3. Si la lista está vacía, NO DEBES recomendar ninguna película.
      
      Basándote EXCLUSIVAMENTE en los resultados del Grafo de Conocimiento anteriores,
      responde a la consulta del usuario: "{query}"
      
      Justifica por qué cada película recomendada encaja con lo solicitado.
    `);

    const chain = prompt.pipe(this.model).pipe(new StringOutputParser());
    return await chain.invoke({ query, movieData });
  }
}
