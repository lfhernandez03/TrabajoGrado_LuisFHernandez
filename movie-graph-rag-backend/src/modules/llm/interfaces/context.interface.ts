/**
 * Interfaces para el contexto extraído del usuario
 * Basadas en context-ontology y bridge-ontology
 */

export interface SocialContext {
  companionType:
    | 'solo'
    | 'pareja'
    | 'familia'
    | 'familia con niños'
    | 'amigos'
    | 'compañeros de trabajo'
    | 'grupo grande';
  hasChildren: boolean;
  numberOfPeople?: number;
}

export interface EmotionalContext {
  moodDescription: string;
  desiredEnergyLevel: 'bajo' | 'medio' | 'alto';
}

export interface RequirementContext {
  availableTime?: number; // minutos
  excludedGenre?: string[];
  negativeConstraint?: string[];
  preferredLanguage?: string;
}

export interface ContextSnapshot {
  snapshotID: string;
  requestTimestamp: Date;
  userIntent: string;
  hourOfDay: number;
  dayOfWeek: string;
  socialContext?: SocialContext;
  emotionalContext?: EmotionalContext;
  requirementContext?: RequirementContext;
}

export interface ExtractedContext {
  contextSnapshot: ContextSnapshot;
  rdfTriples: string;
}

export interface MovieWithScore {
  title: string;
  runtime?: number;
  genreName?: string;
  releaseYear?: number;
  compatibilityScore?: number;
  [key: string]: any;
}
