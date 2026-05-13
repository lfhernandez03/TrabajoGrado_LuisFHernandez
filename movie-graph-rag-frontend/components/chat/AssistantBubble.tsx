"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Bot, Clock, Code2, ChevronDown, ChevronUp, Sparkles, Copy, Check } from "lucide-react";
import { MovieRecommendationCard } from "./MovieRecommendationCard";
import type { ChatMessage } from "@/services/chat.service";

interface AssistantBubbleProps {
  message: ChatMessage;
}

export function AssistantBubble({ message }: AssistantBubbleProps) {
  const [showSparql, setShowSparql] = useState(false);
  const [copied, setCopied] = useState(false);

  const copySparql = () => {
    if (!rec?.sparql_query) return;
    navigator.clipboard.writeText(rec.sparql_query).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };
  const rec = message.recommendation;

  return (
    <div className="flex gap-3">
      <div className="shrink-0 h-8 w-8 bg-accent/30 rounded-full flex items-center justify-center">
        <Bot className="h-4 w-4 text-accent-foreground" />
      </div>
      <div className="max-w-[85%] space-y-3">
        {/* Explanation text */}
        <div className="bg-surface2 border border-border rounded-2xl rounded-bl-md px-4 py-3">
          <p className="text-sm text-text whitespace-pre-wrap leading-relaxed">
            {message.content}
          </p>
        </div>

        {/* Movie recommendations cards */}
        {rec && rec.movies.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground font-medium flex items-center gap-1 ml-1">
              <Sparkles className="h-3 w-3" />
              {rec.movies.length} movie{rec.movies.length !== 1 ? "s" : ""}{" "}
              found
            </p>
            {rec.movies.map((movie, idx) => (
              <MovieRecommendationCard key={idx} movie={movie} />
            ))}
          </div>
        )}

        {/* Metadata footer */}
        {rec && (
          <div className="flex flex-wrap items-center gap-2 ml-1">
            {rec.execution_ms && (
              <Badge variant="outline" className="text-[10px]">
                <Clock className="h-3 w-3 mr-1" />
                {(rec.execution_ms / 1000).toFixed(1)}s
              </Badge>
            )}
            {rec.strategy_used && (
              <Badge variant="outline" className="text-[10px]">
                {rec.strategy_used}
              </Badge>
            )}
            {rec.turn_count > 1 && (
              <Badge variant="outline" className="text-[10px]">
                Turn {rec.turn_count}
              </Badge>
            )}
            {rec.sparql_query && (
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
          </div>
        )}

        {/* SPARQL Query expandable */}
        {showSparql && rec?.sparql_query && (
          <div className="rounded-lg bg-slate-950 p-4 overflow-x-auto">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] text-slate-400 font-medium">
                Consulta SPARQL ejecutada:
              </p>
              <button
                type="button"
                onClick={copySparql}
                className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-slate-200 transition-colors"
                aria-label="Copiar SPARQL"
              >
                {copied ? (
                  <><Check className="h-3 w-3 text-green-400" /><span className="text-green-400">Copiado</span></>
                ) : (
                  <><Copy className="h-3 w-3" />Copiar</>
                )}
              </button>
            </div>
            <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap max-h-48 overflow-y-auto">
              {rec.sparql_query}
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
