import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { ChatGroq } from '@langchain/groq';
import { ChatPromptTemplate } from '@langchain/core/prompts';
import { StringOutputParser } from '@langchain/core/output_parsers';
import {
  ExtractedContext,
  ContextSnapshot,
  MovieWithScore,
  SocialContext,
  EmotionalContext,
} from './interfaces/context.interface';

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
   * Paso 1: Extrae contexto completo usando las 3 ontologías (movie, context, bridge).
   */
  async extractSemanticContext(query: string): Promise<ExtractedContext> {
    const now = new Date();
    const hourOfDay = now.getHours();
    const dayOfWeek = now.toLocaleDateString('es-ES', { weekday: 'long' });

    const prompt = ChatPromptTemplate.fromTemplate(`
      Eres un experto en Ontologías de Cine y Web Semántica.
      Extrae el CONTEXTO COMPLETO del usuario en formato RDF Turtle.

      CONSULTA: "{query}"
      HORA ACTUAL: {hourOfDay}:00 hrs
      DÍA: {dayOfWeek}

      ONTOLOGÍAS DISPONIBLES:
      1. PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>
      2. PREFIX context: <http://www.semanticweb.org/movierecommendation/ontologies/2025/context-ontology#>
      3. PREFIX bridge: <http://www.semanticweb.org/movierecommendation/ontologies/2025/bridge-ontology#>

      EXTRAER:
      
      1. CONTEXTO SOCIAL (SocialContext):
         - companionType: "solo" | "pareja" | "familia" | "familia con niños" | "amigos" | "compañeros de trabajo" | "grupo grande"
         - hasChildren: true/false (CRÍTICO: true si menciona niños, hijos, pequeños)
         - numberOfPeople: número si lo menciona
      
      2. CONTEXTO EMOCIONAL (EmotionalContext):
         - moodDescription: ej. "relajado", "estresado", "nostálgico", "alegre"
         - desiredEnergyLevel: "bajo" | "medio" | "alto"
           * bajo: contenido tranquilo, relajante ("quiero relajarme", "algo suave")
           * medio: equilibrado ("algo ligero pero entretenido")
           * alto: intenso, emocionante ("épico", "emocionante", "lleno de acción")
      
      3. REQUISITOS (RequirementContext):
         - availableTime: minutos disponibles (extraer de "tengo X horas", "algo corto")
         - excludedGenre: lista de géneros a evitar ("no terror", "nada violento")
         - negativeConstraint: otras restricciones ("no animadas", "sin subtítulos")
      
      4. INFORMACIÓN TEMPORAL (ContextSnapshot):
         - hourOfDay: {hourOfDay}
         - dayOfWeek: "{dayOfWeek}"
         - userIntent: resumen breve de la intención del usuario

      VOCABULARIO CONTROLADO OBLIGATORIO:
      - companionType: usar EXACTAMENTE uno de los valores listados
      - desiredEnergyLevel: usar EXACTAMENTE "bajo", "medio" o "alto"
      - Géneros: Action, Adventure, Animation, Comedy, Crime, Documentary, Drama, Family, Fantasy, Horror, Mystery, Romance, Sci-Fi, Thriller, War, Western

      FORMATO DE SALIDA:
      Responde ÚNICAMENTE con las tripletas RDF en formato Turtle.
      Usa :snapshot1, :social1, :emotion1, :req1 como identificadores.
      NO incluyas explicaciones, solo el código Turtle.

      EJEMPLO:
      @prefix context: <http://www.semanticweb.org/movierecommendation/ontologies/2025/context-ontology#> .
      @prefix movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#> .
      @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

      :snapshot1 a context:ContextSnapshot ;
        context:hourOfDay {hourOfDay} ;
        context:dayOfWeek "{dayOfWeek}" ;
        context:userIntent "buscar película de acción" ;
        context:withCompanion :social1 ;
        context:feelsMood :emotion1 ;
        context:hasRequirement :req1 .

      :social1 a context:SocialContext ;
        context:companionType "solo" ;
        context:hasChildren false .

      :emotion1 a context:EmotionalContext ;
        context:moodDescription "emocionado" ;
        context:desiredEnergyLevel "alto" .

      :req1 a context:RequirementContext ;
        context:availableTime 120 .
    `);

    const chain = prompt.pipe(this.model).pipe(new StringOutputParser());

    this.logger.log('Extrayendo contexto completo con LLM...');
    const rdfTriples = await chain.invoke({ query, hourOfDay, dayOfWeek });

    // Parsear el RDF para extraer el contexto estructurado
    const contextSnapshot = this.parseContextFromRDF(
      rdfTriples,
      query,
      hourOfDay,
      dayOfWeek,
    );

    return {
      contextSnapshot,
      rdfTriples: rdfTriples
        .replace(/```turtle\n?/g, '')
        .replace(/```\n?/g, '')
        .trim(),
    };
  }

  /**
   * Parsea el RDF generado para extraer el contexto estructurado.
   */
  private parseContextFromRDF(
    rdfTriples: string,
    query: string,
    hourOfDay: number,
    dayOfWeek: string,
  ): ContextSnapshot {
    const snapshot: ContextSnapshot = {
      snapshotID: `snapshot_${Date.now()}`,
      requestTimestamp: new Date(),
      userIntent: query,
      hourOfDay,
      dayOfWeek,
    };

    // Extraer contexto social
    const companionTypeMatch = rdfTriples.match(
      /context:companionType\s+"([^"]+)"/,
    );
    const hasChildrenMatch = rdfTriples.match(/context:hasChildren\s+(\w+)/);
    const numberOfPeopleMatch = rdfTriples.match(
      /context:numberOfPeople\s+(\d+)/,
    );

    if (companionTypeMatch || hasChildrenMatch) {
      const companionType = companionTypeMatch?.[1] || 'solo';
      snapshot.socialContext = {
        companionType: companionType as SocialContext['companionType'],
        hasChildren: hasChildrenMatch?.[1] === 'true',
        numberOfPeople: numberOfPeopleMatch
          ? parseInt(numberOfPeopleMatch[1])
          : undefined,
      };
    }

    // Extraer contexto emocional
    const moodMatch = rdfTriples.match(/context:moodDescription\s+"([^"]+)"/);
    const energyMatch = rdfTriples.match(
      /context:desiredEnergyLevel\s+"([^"]+)"/,
    );

    if (moodMatch || energyMatch) {
      const energyLevel = energyMatch?.[1] || 'medio';
      snapshot.emotionalContext = {
        moodDescription: moodMatch?.[1] || 'neutral',
        desiredEnergyLevel:
          energyLevel as EmotionalContext['desiredEnergyLevel'],
      };
    }

    // Extraer requisitos
    const availableTimeMatch = rdfTriples.match(
      /context:availableTime\s+(\d+)/,
    );
    const excludedGenreMatches = rdfTriples.match(
      /context:excludedGenre\s+"([^"]+)"/g,
    );

    if (availableTimeMatch || excludedGenreMatches) {
      snapshot.requirementContext = {
        availableTime: availableTimeMatch
          ? parseInt(availableTimeMatch[1])
          : undefined,
        excludedGenre: excludedGenreMatches
          ? excludedGenreMatches.map((m) => m.match(/"([^"]+)"/)?.[1] || '')
          : undefined,
      };
    }

    return snapshot;
  }

  /**
   * Genera una consulta SPARQL multi-ontología usando movie, context y bridge.
   */
  async generateSparqlQuery(
    userQuery: string,
    context: ContextSnapshot,
  ): Promise<string> {
    const contextInfo = JSON.stringify(
      {
        social: context.socialContext,
        emotional: context.emotionalContext,
        requirements: context.requirementContext,
        temporal: {
          hourOfDay: context.hourOfDay,
          dayOfWeek: context.dayOfWeek,
        },
      },
      null,
      2,
    );

    const prompt = ChatPromptTemplate.fromTemplate(`
      Eres un experto en SPARQL y ontologías semánticas para recomendación de películas.
      
      ONTOLOGÍAS DISPONIBLES:
      PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>
      PREFIX context: <http://www.semanticweb.org/movierecommendation/ontologies/2025/context-ontology#>
      PREFIX bridge: <http://www.semanticweb.org/movierecommendation/ontologies/2025/bridge-ontology#>
      PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
      PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
      
      CLASES Y PROPIEDADES:
      
      movie:Movie
        - movie:hasTitle (string)
        - movie:runtime (integer, minutos)
        - movie:hasGenre → movie:Genre
        - movie:releaseYear (integer)
        - movie:averageRating (decimal)
      
      movie:Genre
        - movie:genreName (string: Action, Comedy, Drama, etc.)
      
      context:ContextSnapshot, context:SocialContext, context:EmotionalContext, context:RequirementContext
        - context:companionType (string)
        - context:hasChildren (boolean)
        - context:moodDescription (string)
        - context:desiredEnergyLevel ("bajo"|"medio"|"alto")
        - context:availableTime (integer, minutos)
        - context:excludedGenre (string)
        - context:hourOfDay (integer 0-23)
      
      CONSULTA USUARIO: "{query}"
      
      CONTEXTO EXTRAÍDO:
      {contextInfo}
      
      TAREA:
      Genera una consulta SPARQL SELECT que:
      1. Busque películas (movie:Movie)
      2. Aplique filtros basados en el CONTEXTO:
         - Si availableTime existe: FILTER(?runtime <= {availableTime})
         - Si hasChildren = true: EXCLUIR Horror, Thriller, War (contenido familiar)
         - Si excludedGenre existe: FILTER(NOT CONTAINS(?genreName, "Horror"))
         - Si desiredEnergyLevel = "bajo": preferir Drama, Romance, Documentary
         - Si desiredEnergyLevel = "alto": preferir Action, Adventure, Sci-Fi, Thriller
         - Si desiredEnergyLevel = "medio": preferir Comedy, Mystery, Fantasy
      3. Retorne: ?title ?runtime ?genreName ?releaseYear ?averageRating
      4. Ordene por relevancia (usa averageRating si existe)
      5. LIMITE a 10 resultados (LIMIT 10)
      
      REGLAS CRÍTICAS:
      - Si hasChildren = true, SIEMPRE excluir: Horror, Thriller, Crime, War
      - Si availableTime existe, SIEMPRE aplicar FILTER(?runtime <= availableTime)
      - Usa OPTIONAL para propiedades que pueden no existir
      - Usa FILTER con CONTAINS para búsqueda flexible de géneros
      - NO inventes propiedades que no existen en las ontologías
      
      EJEMPLO (usuario con niños, 90 minutos, quiere algo divertido):
      PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>
      PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
      
      SELECT DISTINCT ?title ?runtime ?genreName ?releaseYear ?averageRating WHERE {{
        ?m rdf:type movie:Movie ;
           movie:hasTitle ?title ;
           movie:runtime ?runtime ;
           movie:hasGenre ?g .
        ?g movie:genreName ?genreName .
        
        OPTIONAL {{ ?m movie:releaseYear ?releaseYear }}
        OPTIONAL {{ ?m movie:averageRating ?averageRating }}
        
        # FILTROS DE CONTEXTO
        FILTER(?runtime <= 90)
        FILTER(?genreName IN ("Animation", "Comedy", "Family", "Adventure"))
        FILTER(?genreName NOT IN ("Horror", "Thriller", "Crime", "War"))
      }}
      ORDER BY DESC(?averageRating) ?runtime
      LIMIT 10
      
      Responde SOLO con la consulta SPARQL, sin explicaciones, sin markdown.
    `);

    const chain = prompt.pipe(this.model).pipe(new StringOutputParser());

    this.logger.log('Generando consulta SPARQL multi-ontología...');
    const sparqlQuery = await chain.invoke({
      query: userQuery,
      contextInfo,
      availableTime: context.requirementContext?.availableTime || 180,
    });

    // Limpiar bloques de código markdown
    return sparqlQuery
      .replace(/```sparql\n?/g, '')
      .replace(/```\n?/g, '')
      .trim();
  }

  /**
   * Calcula un score de compatibilidad entre una película y el contexto del usuario.
   */
  /* eslint-disable @typescript-eslint/no-unsafe-assignment */
  /* eslint-disable @typescript-eslint/no-unsafe-member-access */
  async calculateCompatibilityScore(
    movie: any,
    context: ContextSnapshot,
  ): Promise<number> {
    const movieInfo = JSON.stringify({
      title: movie.title,
      runtime: movie.runtime,
      genreName: movie.genreName,
      releaseYear: movie.releaseYear,
      averageRating: movie.averageRating,
    });

    const contextInfo = JSON.stringify({
      social: context.socialContext,
      emotional: context.emotionalContext,
      requirements: context.requirementContext,
      temporal: {
        hourOfDay: context.hourOfDay,
        dayOfWeek: context.dayOfWeek,
      },
    });

    const prompt = ChatPromptTemplate.fromTemplate(`
      Calcula un score de compatibilidad (0.0 a 1.0) entre esta película y el contexto del usuario.
      
      PELÍCULA:
      {movieInfo}
      
      CONTEXTO USUARIO:
      {contextInfo}
      
      CRITERIOS DE EVALUACIÓN:
      
      1. ALINEACIÓN EMOCIONAL (40%):
         - ¿El género y tono de la película coinciden con el mood?
         - ¿El nivel de energía de la película se ajusta al desiredEnergyLevel?
         - Ejemplos:
           * desiredEnergyLevel="alto" + Action/Thriller = score alto
           * desiredEnergyLevel="bajo" + Drama/Documentary = score alto
           * desiredEnergyLevel="medio" + Comedy/Mystery = score alto
      
      2. NIVEL DE ENERGÍA (30%):
         - ¿La intensidad de la película es apropiada?
         - Action/Thriller/Adventure = energía alta
         - Drama/Romance/Documentary = energía baja
         - Comedy/Mystery/Fantasy = energía media
      
      3. CONTEXTO SOCIAL (20%):
         - ¿Es apropiada para la compañía?
         - familia con niños: Animation, Family, Comedy (evitar Horror, Thriller)
         - pareja: Romance, Drama
         - solo: cualquier género
         - amigos: Comedy, Action, Sci-Fi
      
      4. LOGÍSTICA (10%):
         - ¿Cumple con el tiempo disponible?
         - Si runtime > availableTime: penalizar
         - ¿Cumple con restricciones de género?
      
      CÁLCULO:
      - Suma ponderada de los 4 criterios
      - Retorna un decimal entre 0.0 y 1.0
      - Sé generoso pero objetivo
      
      RESPONDE SOLO CON EL NÚMERO DECIMAL (ejemplo: 0.87)
      NO incluyas explicaciones, solo el número.
    `);

    const chain = prompt.pipe(this.model).pipe(new StringOutputParser());
    const scoreStr = await chain.invoke({ movieInfo, contextInfo });

    // Parsear el score, manejar errores
    const score = parseFloat(scoreStr.trim());
    return isNaN(score) ? 0.5 : Math.max(0, Math.min(1, score));
  }
  /* eslint-enable @typescript-eslint/no-unsafe-assignment */
  /* eslint-enable @typescript-eslint/no-unsafe-member-access */

  /**
   * Calcula scores para múltiples películas en paralelo.
   */
  /* eslint-disable @typescript-eslint/no-unsafe-member-access */
  /* eslint-disable @typescript-eslint/no-unsafe-return */
  async calculateCompatibilityScores(
    movies: any[],
    context: ContextSnapshot,
  ): Promise<MovieWithScore[]> {
    this.logger.log(
      `Calculando compatibility scores para ${movies.length} películas...`,
    );

    const moviesWithScores = await Promise.all(
      movies.map(async (movie) => {
        const score = await this.calculateCompatibilityScore(movie, context);
        return {
          ...movie,
          compatibilityScore: score,
        };
      }),
    );

    // Ordenar por score descendente
    return moviesWithScores.sort(
      (a, b) => (b.compatibilityScore || 0) - (a.compatibilityScore || 0),
    );
  }
  /* eslint-enable @typescript-eslint/no-unsafe-member-access */
  /* eslint-enable @typescript-eslint/no-unsafe-return */

  /**
   * Genera la respuesta final contextualizada explicando por qué cada película es recomendada.
   */
  async generateNarrativeResponse(
    query: string,
    movieResults: MovieWithScore[],
    context: ContextSnapshot,
  ): Promise<string> {
    const movieData = JSON.stringify(
      movieResults.slice(0, 5).map((m) => ({
        title: m.title,
        runtime: m.runtime,
        genreName: m.genreName,
        releaseYear: m.releaseYear,
        compatibilityScore: m.compatibilityScore,
      })),
    );

    const contextInfo = JSON.stringify(
      {
        social: context.socialContext,
        emotional: context.emotionalContext,
        requirements: context.requirementContext,
        temporal: {
          hourOfDay: context.hourOfDay,
          dayOfWeek: context.dayOfWeek,
        },
      },
      null,
      2,
    );

    const prompt = ChatPromptTemplate.fromTemplate(`
      Eres un recomendador de cine directo y conciso.
      
      CONTEXTO DEL USUARIO:
      {contextInfo}
      
      PELÍCULAS RECOMENDADAS:
      {movieData}
      
      CONSULTA: "{query}"
      
      INSTRUCCIONES:
      1. Recomienda SOLO las 2-3 mejores películas
      2. Para cada película, explica en 1-2 oraciones:
         - Por qué se ajusta a su contexto (compañía, mood, tiempo)
         - Un aspecto destacado que la hace ideal
      3. SÉ BREVE Y DIRECTO - máximo 3-4 párrafos cortos
      4. Evita repeticiones y redundancias
      5. NO menciones "compatibilityScore"
      
      ESTILO:
      - Conversacional pero conciso
      - Directo al grano
      - Sin introducciones largas
      - Sin conclusiones repetitivas
      
      REGLAS:
      - SOLO películas de la lista proporcionada
      - NUNCA inventes títulos
      - Si no hay resultados, explica brevemente por qué
      
      Genera una recomendación clara y útil en máximo 150 palabras.
    `);

    const chain = prompt.pipe(this.model).pipe(new StringOutputParser());
    return await chain.invoke({ query, movieData, contextInfo });
  }
}
