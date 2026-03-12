"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Bot, Clock, Code2, ChevronDown, ChevronUp, Sparkles } from "lucide-react";
import { MovieRecommendationCard } from "./MovieRecommendationCard";
import type { ChatMessage } from "@/services/chat.service";

interface AssistantBubbleProps {
  message: ChatMessage;
}

export function AssistantBubble({ message }: AssistantBubbleProps) {
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
