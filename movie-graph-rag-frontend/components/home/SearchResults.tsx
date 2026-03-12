"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MovieCard } from "@/components/recommendation/MovieCard";
import { Code2, ChevronDown, ChevronUp } from "lucide-react";
import { Movie } from "@/services/movies.service";
import { useState } from "react";

interface SearchResultsProps {
  searchQuery: string;
  searchResults: Movie[];
  lastSparqlQuery: string;
  onViewDetails: (movie: Movie) => void;
  onRecommendSimilar: (movie: Movie) => void;
}

export function SearchResults({
  searchQuery,
  searchResults,
  lastSparqlQuery,
  onViewDetails,
  onRecommendSimilar,
}: SearchResultsProps) {
  const [showSparqlLog, setShowSparqlLog] = useState(false);

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-semibold">
          Resultados de búsqueda
          {searchResults.length > 0 && ` (${searchResults.length})`}
        </h2>
        {lastSparqlQuery && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowSparqlLog(!showSparqlLog)}
            className="flex items-center gap-2"
          >
            <Code2 className="h-4 w-4" />
            {showSparqlLog ? "Ocultar" : "Ver"} Query SPARQL
            {showSparqlLog ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>
        )}
      </div>

      {showSparqlLog && lastSparqlQuery && (
        <Card className="mb-4 bg-slate-950 text-slate-50">
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Code2 className="h-4 w-4" />
              Query SPARQL Ejecutada (Explainable AI)
            </CardTitle>
            <CardDescription className="text-slate-400">
              Esta es la consulta semántica que se ejecutó sobre el grafo de
              conocimiento
            </CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="text-xs overflow-x-auto p-4 bg-slate-900 rounded-md border border-slate-800">
              <code>{lastSparqlQuery}</code>
            </pre>
          </CardContent>
        </Card>
      )}

      {searchResults.length > 0 ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {searchResults.map((movie) => (
            <MovieCard
              key={movie.uri}
              movie={movie}
              onViewDetails={onViewDetails}
              onRecommendSimilar={onRecommendSimilar}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-muted-foreground">
          No se encontraron resultados para &ldquo;{searchQuery}&rdquo;
        </div>
      )}
    </div>
  );
}
