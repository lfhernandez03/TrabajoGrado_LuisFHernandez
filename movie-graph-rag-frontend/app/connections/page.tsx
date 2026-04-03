"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Navbar } from "@/components/organisms/Navbar";
import { ProtectedRoute } from "@/components/shared/ProtectedRoute";
import { MovieSearchInput } from "@/components/recommendation/MovieSearchInput";
import {
  Network,
  ArrowRight,
  Film,
  Code2,
  ChevronDown,
  ChevronUp,
  Clock,
  Route,
  ArrowLeft,
  RotateCcw,
} from "lucide-react";
import {
  findConnections,
  ConnectionExplorerResponse,
  MovieSuggestion,
} from "@/services/movies.service";
import { getNodeIcon, getNodeColor, getEdgeColor } from "@/lib/graph-styles";
import { toast } from "sonner";
import Link from "next/link";

export default function ConnectionsPage() {
  const [fromQuery, setFromQuery] = useState("");
  const [toQuery, setToQuery] = useState("");
  const [fromSelected, setFromSelected] = useState<MovieSuggestion | null>(null);
  const [toSelected, setToSelected] = useState<MovieSuggestion | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [result, setResult] = useState<ConnectionExplorerResponse | null>(null);
  const [showSparql, setShowSparql] = useState(false);

  const handleExplore = async () => {
    if (!fromSelected || !toSelected) {
      toast.error("Selecciona ambas películas del buscador");
      return;
    }

    try {
      setIsSearching(true);
      setResult(null);
      const data = await findConnections({
        from: fromSelected.title,
        to: toSelected.title,
        maxDepth: 3,
      });
      setResult(data);

      if (!data.found) {
        toast.info("No se encontró una conexión directa entre estas películas");
      }
    } catch (error) {
      console.error("Error explorando conexiones:", error);
      toast.error("Error al buscar conexiones");
    } finally {
      setIsSearching(false);
    }
  };

  const handleReset = () => {
    setFromQuery("");
    setToQuery("");
    setFromSelected(null);
    setToSelected(null);
    setResult(null);
    setShowSparql(false);
  };

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-bg text-text">
        <Navbar />

        <main className="container mx-auto px-4 py-8 max-w-4xl">
          {/* Back button + Header */}
          <div className="mb-8">
            <Link href="/">
              <Button variant="ghost" size="sm" className="mb-4 -ml-2">
                <ArrowLeft className="h-4 w-4 mr-1" />
                Volver al inicio
              </Button>
            </Link>

            <div className="flex items-center gap-3 mb-2">
              <div className="h-12 w-12 rounded-full bg-accent/10 flex items-center justify-center">
                <Network className="h-6 w-6 text-accent" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">Explorador de Conexiones</h1>
                <p className="text-sm text-muted-foreground">
                  Descubre el camino semántico entre dos películas en el grafo de conocimiento
                </p>
              </div>
            </div>
          </div>

          {/* Search Section */}
          <Card className="mb-8 border-border">
            <CardContent className="p-6">
              <div className="flex flex-col gap-4">
                {/* Movie inputs */}
                <div className="flex flex-col sm:flex-row items-center gap-3">
                  <div className="flex-1 w-full">
                    <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                      Película de origen
                    </label>
                    <MovieSearchInput
                      value={fromQuery}
                      onChange={(val) => {
                        setFromQuery(val);
                        if (fromSelected && val !== fromSelected.title) {
                          setFromSelected(null);
                        }
                      }}
                      onSelect={(movie) => {
                        setFromSelected(movie);
                        setFromQuery(movie.title);
                      }}
                      placeholder="Ej: Inception, The Matrix..."
                      disabled={isSearching}
                    />
                    {fromSelected && (
                      <p className="text-[11px] text-accent mt-1 flex items-center gap-1">
                        <Film className="h-3 w-3" />
                        {fromSelected.title}
                        {fromSelected.director && (
                          <span className="text-muted-foreground">
                            — {fromSelected.director}
                          </span>
                        )}
                      </p>
                    )}
                  </div>

                  <div className="shrink-0 pt-5 hidden sm:block">
                    <ArrowRight className="h-5 w-5 text-accent" />
                  </div>

                  <div className="flex-1 w-full">
                    <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                      Película de destino
                    </label>
                    <MovieSearchInput
                      value={toQuery}
                      onChange={(val) => {
                        setToQuery(val);
                        if (toSelected && val !== toSelected.title) {
                          setToSelected(null);
                        }
                      }}
                      onSelect={(movie) => {
                        setToSelected(movie);
                        setToQuery(movie.title);
                      }}
                      placeholder="Ej: Interstellar, Blade Runner..."
                      disabled={isSearching}
                    />
                    {toSelected && (
                      <p className="text-[11px] text-accent mt-1 flex items-center gap-1">
                        <Film className="h-3 w-3" />
                        {toSelected.title}
                        {toSelected.director && (
                          <span className="text-muted-foreground">
                            — {toSelected.director}
                          </span>
                        )}
                      </p>
                    )}
                  </div>
                </div>

                {/* Action buttons */}
                <div className="flex gap-2">
                  <Button
                    onClick={handleExplore}
                    disabled={isSearching || !fromSelected || !toSelected}
                    className="flex-1"
                    size="lg"
                  >
                    {isSearching ? (
                      <>
                        <Route className="h-4 w-4 mr-2 animate-pulse" />
                        Explorando grafo...
                      </>
                    ) : (
                      <>
                        <Route className="h-4 w-4 mr-2" />
                        Encontrar Conexión
                      </>
                    )}
                  </Button>
                  {(fromSelected || toSelected || result) && (
                    <Button
                      variant="outline"
                      size="lg"
                      onClick={handleReset}
                    >
                      <RotateCcw className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Loading skeleton */}
          {isSearching && (
            <div className="space-y-4">
              <Skeleton className="h-20 w-full rounded-lg" />
              <div className="flex items-center gap-4 justify-center py-4">
                <Skeleton className="h-12 w-28 rounded-full" />
                <Skeleton className="h-1 w-16" />
                <Skeleton className="h-12 w-28 rounded-full" />
                <Skeleton className="h-1 w-16" />
                <Skeleton className="h-12 w-28 rounded-full" />
              </div>
              <Skeleton className="h-40 w-full rounded-lg" />
            </div>
          )}

          {/* Results */}
          {result && !isSearching && (
            <div className="space-y-6">
              {/* Summary card */}
              <Card
                className={`border ${
                  result.found
                    ? "border-accent/40 bg-accent/5"
                    : "border-destructive/40 bg-destructive/5"
                }`}
              >
                <CardContent className="p-5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className={`h-11 w-11 rounded-full flex items-center justify-center ${
                          result.found ? "bg-accent/20" : "bg-destructive/20"
                        }`}
                      >
                        <Network
                          className={`h-5 w-5 ${
                            result.found ? "text-accent" : "text-destructive"
                          }`}
                        />
                      </div>
                      <div>
                        <p className="font-semibold">
                          {result.found
                            ? `Conexión encontrada`
                            : `No se encontró conexión`}
                        </p>
                        <p className="text-sm text-muted-foreground mt-0.5">
                          {result.found
                            ? result.distance === 0
                              ? "Es la misma película"
                              : result.distance === 1
                              ? `"${result.fromTitle}" y "${result.toTitle}" tienen una conexión directa (1 salto)`
                              : `"${result.fromTitle}" y "${result.toTitle}" están a ${result.distance} grados de separación`
                            : `"${result.fromTitle || fromQuery}" y "${result.toTitle || toQuery}" no comparten conexiones conocidas`}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-muted-foreground shrink-0 ml-4">
                      <Clock className="h-3 w-3" />
                      {result.executionTimeMs}ms
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Path visualization */}
              {result.found && result.pathSteps.length > 0 && (
                <Card className="border-border">
                  <CardContent className="p-6">
                    <h3 className="text-base font-semibold mb-5 flex items-center gap-2">
                      <Route className="h-4 w-4 text-accent" />
                      Camino de Conexión
                    </h3>

                    {/* Vertical stepper */}
                    <div className="relative pl-8">
                      {result.pathSteps.map((step, index) => (
                        <div key={step.step} className="relative pb-8 last:pb-0">
                          {/* Vertical connector line */}
                          {index < result.pathSteps.length - 1 && (
                            <div
                              className={`absolute -left-4 top-9 w-0.5 h-[calc(100%-12px)] ${getEdgeColor(step.node.type)} border-l-2 border-dashed`}
                            />
                          )}

                          {/* Node circle */}
                          <div className="flex items-start gap-4">
                            <div
                              className={`absolute -left-6 top-1 h-8 w-8 rounded-full border-2 flex items-center justify-center shrink-0 ${getNodeColor(step.node.type)}`}
                            >
                              {getNodeIcon(step.node.type)}
                            </div>

                            {/* Content */}
                            <div className="flex-1 min-w-0 ml-2">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="font-semibold text-sm">
                                  {step.node.label}
                                </span>
                                <Badge
                                  variant="outline"
                                  className={`text-[10px] px-1.5 py-0 ${getNodeColor(step.node.type)}`}
                                >
                                  {step.node.type === "movie"
                                    ? "Película"
                                    : step.node.type === "person"
                                    ? "Persona"
                                    : "Género"}
                                </Badge>
                              </div>
                              {index > 0 && (
                                <p className="text-xs text-muted-foreground mt-1">
                                  {step.description}
                                </p>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Edges / Relations detail */}
              {result.found && result.edges.length > 0 && (
                <Card className="border-border">
                  <CardContent className="p-6">
                    <h3 className="text-base font-semibold mb-4 flex items-center gap-2">
                      <Network className="h-4 w-4 text-accent" />
                      Relaciones del Grafo
                    </h3>
                    <div className="grid gap-2">
                      {result.edges.map((edge, index) => {
                        const fromNode = result.nodes.find(
                          (n) => n.uri === edge.from
                        );
                        const toNode = result.nodes.find(
                          (n) => n.uri === edge.to
                        );

                        return (
                          <div
                            key={index}
                            className="flex items-center gap-2 text-xs bg-secondary/30 rounded-lg px-3 py-2.5"
                          >
                            <Badge
                              variant="outline"
                              className={`text-[10px] shrink-0 ${getNodeColor(fromNode?.type || "movie")}`}
                            >
                              {fromNode?.label || "?"}
                            </Badge>
                            <span className="text-muted-foreground whitespace-nowrap">
                              —{edge.label}→
                            </span>
                            <Badge
                              variant="outline"
                              className={`text-[10px] shrink-0 ${getNodeColor(toNode?.type || "movie")}`}
                            >
                              {toNode?.label || "?"}
                            </Badge>
                            <span className="ml-auto text-[10px] text-muted-foreground font-mono">
                              {edge.property}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* SPARQL query toggle */}
              <Card className="border-border">
                <CardContent className="p-4">
                  <button
                    onClick={() => setShowSparql(!showSparql)}
                    className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors w-full"
                  >
                    <Code2 className="h-4 w-4" />
                    <span>Consulta SPARQL utilizada</span>
                    {showSparql ? (
                      <ChevronUp className="h-3 w-3 ml-auto" />
                    ) : (
                      <ChevronDown className="h-3 w-3 ml-auto" />
                    )}
                  </button>

                  {showSparql && (
                    <div className="mt-3 bg-slate-950 text-slate-50 rounded-lg p-4 overflow-x-auto">
                      <pre className="text-xs whitespace-pre-wrap font-mono leading-relaxed">
                        {result.sparqlQuery}
                      </pre>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Not found help */}
              {!result.found && (
                <div className="text-center py-6 text-sm text-muted-foreground">
                  <p>
                    Intenta con películas diferentes o verifica que los títulos
                    sean correctos.
                  </p>
                  <p className="mt-1 text-xs">
                    El explorador busca conexiones por director, actor y género
                    compartido (hasta 2 saltos en el grafo).
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Empty state */}
          {!result && !isSearching && (
            <div className="text-center py-16 text-muted-foreground">
              <Network className="h-16 w-16 mx-auto mb-4 opacity-20" />
              <p className="text-lg font-medium mb-1">
                Selecciona dos películas para explorar su conexión
              </p>
              <p className="text-sm">
                Usa los buscadores de arriba para encontrar las películas y
                descubrir cómo están conectadas a través del grafo de
                conocimiento.
              </p>
            </div>
          )}
        </main>
      </div>
    </ProtectedRoute>
  );
}
