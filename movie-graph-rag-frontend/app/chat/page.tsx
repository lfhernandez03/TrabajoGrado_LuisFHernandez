"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Navbar } from "@/components/shared/Navbar";
import { ProtectedRoute } from "@/components/shared/ProtectedRoute";
import {
  Send,
  Bot,
  User,
  Film,
  Star,
  Clock,
  Code2,
  ChevronDown,
  ChevronUp,
  Sparkles,
  ArrowLeft,
  Loader2,
  MessageSquare,
  Lightbulb,
} from "lucide-react";
import {
  sendChatMessage,
  type ChatMessage,
  type ChatRecommendationResponse,
} from "@/services/chat.service";
import { toast } from "sonner";

const SUGGESTION_PROMPTS = [
  {
    icon: "🎬",
    text: "Recomiéndame una película de acción para ver con amigos",
  },
  {
    icon: "🍿",
    text: "Quiero ver algo ligero y divertido para esta noche",
  },
  {
    icon: "💕",
    text: "Busco una película romántica para ver en pareja",
  },
  {
    icon: "👨‍👩‍👧‍👦",
    text: "Necesito una película familiar apta para niños",
  },
];

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

// ─── Message Bubble Components ──────────────────────────────────────

function UserBubble({ message }: { message: ChatMessage }) {
  return (
    <div className="flex justify-end gap-3">
      <div className="max-w-[80%]">
        <div className="bg-primary text-primary-foreground rounded-2xl rounded-br-md px-4 py-3">
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        </div>
        <p className="text-[10px] text-muted-foreground text-right mt-1 mr-1">
          {new Date(message.timestamp).toLocaleTimeString("es-ES", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>
      </div>
      <div className="shrink-0 h-8 w-8 bg-primary/20 rounded-full flex items-center justify-center">
        <User className="h-4 w-4 text-primary" />
      </div>
    </div>
  );
}

function LoadingBubble() {
  return (
    <div className="flex gap-3">
      <div className="shrink-0 h-8 w-8 bg-accent/30 rounded-full flex items-center justify-center">
        <Bot className="h-4 w-4 text-accent-foreground" />
      </div>
      <div className="max-w-[80%]">
        <div className="bg-muted rounded-2xl rounded-bl-md px-4 py-3">
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
            <span className="text-sm text-muted-foreground">
              Analizando tu consulta con el grafo de conocimiento...
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function MovieRecommendationCard({
  movie,
}: {
  movie: ChatRecommendationResponse["moviesWithScores"][0];
}) {
  const score = movie.compatibilityScore ?? 0;
  const scoreColor =
    score >= 0.8
      ? "text-green-400"
      : score >= 0.6
      ? "text-yellow-400"
      : "text-orange-400";

  return (
    <div className="bg-background/60 border border-border/50 rounded-lg p-3 flex items-center gap-3">
      <div className="shrink-0 h-10 w-10 bg-primary/10 rounded-lg flex items-center justify-center">
        <Film className="h-5 w-5 text-primary" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{movie.title}</p>
        <div className="flex items-center gap-2 mt-0.5">
          {movie.genreName && (
            <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
              {movie.genreName}
            </Badge>
          )}
          {movie.runtime && (
            <span className="text-[10px] text-muted-foreground flex items-center gap-0.5">
              <Clock className="h-3 w-3" />
              {movie.runtime} min
            </span>
          )}
          {movie.releaseDate && (
            <span className="text-[10px] text-muted-foreground">
              {new Date(movie.releaseDate).getFullYear()}
            </span>
          )}
        </div>
      </div>
      <div className="shrink-0 text-right">
        <p className={`text-sm font-bold ${scoreColor}`}>
          {(score * 100).toFixed(0)}%
        </p>
        <div className="flex items-center gap-0.5">
          <Star className="h-3 w-3 text-yellow-400 fill-yellow-400" />
          <span className="text-[10px] text-muted-foreground">match</span>
        </div>
      </div>
    </div>
  );
}

function AssistantBubble({ message }: { message: ChatMessage }) {
  const [showSparql, setShowSparql] = useState(false);
  const [showRdf, setShowRdf] = useState(false);
  const rec = message.recommendation;

  return (
    <div className="flex gap-3">
      <div className="shrink-0 h-8 w-8 bg-accent/30 rounded-full flex items-center justify-center">
        <Bot className="h-4 w-4 text-accent-foreground" />
      </div>
      <div className="max-w-[85%] space-y-3">
        {/* Explanation text */}
        <div className="bg-muted rounded-2xl rounded-bl-md px-4 py-3">
          <p className="text-sm whitespace-pre-wrap leading-relaxed">
            {message.content}
          </p>
        </div>

        {/* Movie recommendations cards */}
        {rec && rec.moviesWithScores.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground font-medium flex items-center gap-1 ml-1">
              <Sparkles className="h-3 w-3" />
              {rec.moviesFound} película{rec.moviesFound !== 1 ? "s" : ""}{" "}
              encontrada{rec.moviesFound !== 1 ? "s" : ""}
            </p>
            {rec.moviesWithScores.map((movie, idx) => (
              <MovieRecommendationCard key={idx} movie={movie} />
            ))}
          </div>
        )}

        {/* Metadata footer */}
        {rec && (
          <div className="flex flex-wrap items-center gap-2 ml-1">
            {rec.executionTimeMs && (
              <Badge variant="outline" className="text-[10px]">
                <Clock className="h-3 w-3 mr-1" />
                {(rec.executionTimeMs / 1000).toFixed(1)}s
              </Badge>
            )}

            {rec.sparqlQuery && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 text-[10px] px-2"
                onClick={() => setShowSparql(!showSparql)}
              >
                <Code2 className="h-3 w-3 mr-1" />
                SPARQL
                {showSparql ? (
                  <ChevronUp className="h-3 w-3 ml-1" />
                ) : (
                  <ChevronDown className="h-3 w-3 ml-1" />
                )}
              </Button>
            )}

            {rec.rdfGenerated && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 text-[10px] px-2"
                onClick={() => setShowRdf(!showRdf)}
              >
                <Code2 className="h-3 w-3 mr-1" />
                RDF
                {showRdf ? (
                  <ChevronUp className="h-3 w-3 ml-1" />
                ) : (
                  <ChevronDown className="h-3 w-3 ml-1" />
                )}
              </Button>
            )}
          </div>
        )}

        {/* SPARQL Query expandable */}
        {showSparql && rec?.sparqlQuery && (
          <div className="rounded-lg bg-slate-950 p-4 overflow-x-auto">
            <p className="text-[10px] text-slate-400 font-medium mb-2">
              Consulta SPARQL ejecutada:
            </p>
            <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap max-h-48 overflow-y-auto">
              {rec.sparqlQuery}
            </pre>
          </div>
        )}

        {/* RDF Triples expandable */}
        {showRdf && rec?.rdfGenerated && (
          <div className="rounded-lg bg-slate-950 p-4 overflow-x-auto">
            <p className="text-[10px] text-slate-400 font-medium mb-2">
              Tripletas RDF generadas:
            </p>
            <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap max-h-48 overflow-y-auto">
              {rec.rdfGenerated}
            </pre>
          </div>
        )}

        {/* Timestamp */}
        <p className="text-[10px] text-muted-foreground ml-1">
          {new Date(message.timestamp).toLocaleTimeString("es-ES", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>
      </div>
    </div>
  );
}

// ─── Main Chat Page ─────────────────────────────────────────────────

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom on new messages
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  const handleSend = async (text?: string) => {
    const query = (text ?? inputValue).trim();
    if (!query || isLoading) return;

    const userMessage: ChatMessage = {
      id: generateId(),
      role: "user",
      content: query,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

    setTimeout(() => inputRef.current?.focus(), 0);

    try {
      const response = await sendChatMessage(query);

      const assistantMessage: ChatMessage = {
        id: generateId(),
        role: "assistant",
        content: response.explanation,
        timestamp: new Date(),
        recommendation: response,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Error en chat:", error);
      const errorMessage: ChatMessage = {
        id: generateId(),
        role: "assistant",
        content:
          "Lo siento, hubo un error al procesar tu consulta. Por favor, intenta de nuevo.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      toast.error("Error al obtener recomendación");
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isEmpty = messages.length === 0;

  return (
    <ProtectedRoute>
      <div className="flex flex-col h-screen bg-background text-foreground">
        <Navbar />

        {/* Scrollable content area */}
        <div className="flex-1 overflow-y-auto">
          <div className="container mx-auto px-4 max-w-4xl">
            {/* Back button + Header (connections-explorer style) */}
            <div className="pt-8 pb-6">
              <Link href="/">
                <Button variant="ghost" size="sm" className="mb-4 -ml-2">
                  <ArrowLeft className="h-4 w-4 mr-1" />
                  Volver al inicio
                </Button>
              </Link>

              <div className="flex items-center gap-3">
                <div className="h-12 w-12 rounded-full bg-accent/10 flex items-center justify-center">
                  <MessageSquare className="h-6 w-6 text-accent" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold">Asistente de Recomendaciones</h1>
                  <p className="text-sm text-muted-foreground">
                    Describe lo que buscas y el sistema consultará el grafo de conocimiento con IA
                  </p>
                </div>
              </div>
            </div>

            {/* Empty state — centered vertically in the remaining space */}
            {isEmpty && !isLoading && (
              <div className="flex flex-col items-center justify-center text-center text-muted-foreground py-20">
                <MessageSquare className="h-16 w-16 mx-auto mb-4 opacity-20" />
                <p className="text-lg font-medium mb-1">
                  Escribe tu consulta abajo para empezar
                </p>
                <p className="text-sm max-w-md">
                  Puedes mencionar género, compañía, estado de ánimo, tiempo
                  disponible y más. El sistema extraerá contexto semántico y
                  consultará el grafo de conocimiento.
                </p>
                <div className="flex items-center justify-center gap-2 mt-4 text-xs">
                  <Lightbulb className="h-3 w-3" />
                  <span>Las respuestas incluyen la consulta SPARQL y las tripletas RDF generadas</span>
                </div>
              </div>
            )}

            {/* Conversation bubbles */}
            {messages.length > 0 && (
              <div className="space-y-6 pb-4">
                {messages.map((msg) =>
                  msg.role === "user" ? (
                    <UserBubble key={msg.id} message={msg} />
                  ) : (
                    <AssistantBubble key={msg.id} message={msg} />
                  )
                )}
                {isLoading && <LoadingBubble />}
                <div ref={messagesEndRef} />
              </div>
            )}

            {/* Input area — inside the same container */}
            <div className="sticky bottom-0 pt-4 pb-6 bg-linear-to-t from-background from-80% to-transparent">
              {/* Suggestion chips — only when empty */}
              {isEmpty && (
                <div className="flex flex-wrap gap-2 mb-3">
                  {SUGGESTION_PROMPTS.map((suggestion, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSend(suggestion.text)}
                      disabled={isLoading}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border/50 bg-muted/30 hover:bg-muted/60 hover:border-accent/30 transition-all text-xs text-muted-foreground hover:text-foreground disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <span>{suggestion.icon}</span>
                      <span>{suggestion.text}</span>
                    </button>
                  ))}
                </div>
              )}

              <div className="flex items-end gap-2">
                <div className="flex-1">
                  <textarea
                    ref={inputRef}
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Describe qué tipo de película buscas..."
                    disabled={isLoading}
                    rows={1}
                    className="w-full resize-none rounded-xl border border-border bg-muted/30 px-4 py-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent disabled:opacity-50 disabled:cursor-not-allowed min-h-11 max-h-30 field-sizing-content"
                  />
                </div>
                <Button
                  onClick={() => handleSend()}
                  disabled={!inputValue.trim() || isLoading}
                  size="icon"
                  className="h-11 w-11 rounded-xl shrink-0"
                >
                  {isLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
