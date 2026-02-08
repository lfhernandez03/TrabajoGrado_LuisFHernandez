"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Network,
  ArrowRight,
  Search,
  Film,
  User,
  Tag,
  Code2,
  ChevronDown,
  ChevronUp,
  X,
  Clock,
  Route,
} from "lucide-react";
import {
  findConnections,
  ConnectionExplorerResponse,
  ConnectionNode,
} from "@/services/movies.service";
import { toast } from "sonner";

interface ConnectionExplorerProps {
  open: boolean;
  onClose: () => void;
}

export function ConnectionExplorer({ open, onClose }: ConnectionExplorerProps) {
  const [fromQuery, setFromQuery] = useState("");
  const [toQuery, setToQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [result, setResult] = useState<ConnectionExplorerResponse | null>(null);
  const [showSparql, setShowSparql] = useState(false);

  const handleExplore = async () => {
    if (!fromQuery.trim() || !toQuery.trim()) {
      toast.error("Ingresa ambas películas para explorar la conexión");
      return;
    }

    try {
      setIsSearching(true);
      setResult(null);
      const data = await findConnections({
        from: fromQuery,
        to: toQuery,
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

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleExplore();
    }
  };

  const handleReset = () => {
    setFromQuery("");
    setToQuery("");
    setResult(null);
    setShowSparql(false);
  };

  const getNodeIcon = (type: ConnectionNode["type"]) => {
    switch (type) {
      case "movie":
        return <Film className="h-4 w-4" />;
      case "person":
        return <User className="h-4 w-4" />;
      case "genre":
        return <Tag className="h-4 w-4" />;
    }
  };

  const getNodeColor = (type: ConnectionNode["type"]) => {
    switch (type) {
      case "movie":
        return "bg-blue-500/20 text-blue-400 border-blue-500/40";
      case "person":
        return "bg-amber-500/20 text-amber-400 border-amber-500/40";
      case "genre":
        return "bg-emerald-500/20 text-emerald-400 border-emerald-500/40";
    }
  };

  const getEdgeColor = (type: ConnectionNode["type"]) => {
    switch (type) {
      case "movie":
        return "border-blue-500/50";
      case "person":
        return "border-amber-500/50";
      case "genre":
        return "border-emerald-500/50";
    }
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Network className="h-5 w-5 text-accent" />
            Explorador de Conexiones
          </DialogTitle>
          <DialogDescription>
            Descubre el camino semántico entre dos películas en el grafo de
            conocimiento
          </DialogDescription>
        </DialogHeader>

        {/* Search Inputs */}
        <div className="flex flex-col sm:flex-row items-center gap-3 mt-2">
          <div className="relative flex-1 w-full">
            <Input
              placeholder="Película de origen..."
              value={fromQuery}
              onChange={(e) => setFromQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isSearching}
              className="pr-8"
            />
            <Film className="absolute right-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          </div>

          <div className="shrink-0">
            <ArrowRight className="h-5 w-5 text-accent" />
          </div>

          <div className="relative flex-1 w-full">
            <Input
              placeholder="Película de destino..."
              value={toQuery}
              onChange={(e) => setToQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isSearching}
              className="pr-8"
            />
            <Film className="absolute right-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-2">
          <Button
            onClick={handleExplore}
            disabled={isSearching || !fromQuery.trim() || !toQuery.trim()}
            className="flex-1"
          >
            {isSearching ? (
              <>
                <Search className="h-4 w-4 mr-2 animate-spin" />
                Explorando grafo...
              </>
            ) : (
              <>
                <Route className="h-4 w-4 mr-2" />
                Encontrar Conexión
              </>
            )}
          </Button>
          {result && (
            <Button variant="outline" size="icon" onClick={handleReset}>
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* Loading skeleton */}
        {isSearching && (
          <div className="space-y-4 mt-4">
            <Skeleton className="h-16 w-full" />
            <div className="flex items-center gap-4 justify-center">
              <Skeleton className="h-12 w-24 rounded-full" />
              <Skeleton className="h-1 w-12" />
              <Skeleton className="h-12 w-24 rounded-full" />
              <Skeleton className="h-1 w-12" />
              <Skeleton className="h-12 w-24 rounded-full" />
            </div>
            <Skeleton className="h-32 w-full" />
          </div>
        )}

        {/* Results */}
        {result && !isSearching && (
          <div className="space-y-5 mt-2">
            {/* Header con resumen */}
            <Card
              className={`border ${
                result.found
                  ? "border-accent/40 bg-accent/5"
                  : "border-destructive/40 bg-destructive/5"
              }`}
            >
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className={`h-10 w-10 rounded-full flex items-center justify-center ${
                        result.found ? "bg-accent/20" : "bg-destructive/20"
                      }`}
                    >
                      <Network
                        className={`h-5 w-5 ${
                          result.found
                            ? "text-accent"
                            : "text-destructive"
                        }`}
                      />
                    </div>
                    <div>
                      <p className="font-semibold text-sm">
                        {result.found
                          ? `Conexión encontrada entre "${result.fromTitle}" y "${result.toTitle}"`
                          : `No se encontró conexión entre "${result.fromTitle || fromQuery}" y "${result.toTitle || toQuery}"`}
                      </p>
                      {result.found && (
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {result.distance === 0
                            ? "Es la misma película"
                            : result.distance === 1
                            ? "Conexión directa (1 salto)"
                            : `${result.distance} grados de separación`}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    {result.executionTimeMs}ms
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Visualización del camino */}
            {result.found && result.pathSteps.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                  <Route className="h-4 w-4 text-accent" />
                  Camino de Conexión
                </h4>

                {/* Path visual - vertical stepper */}
                <div className="relative pl-6">
                  {result.pathSteps.map((step, index) => (
                    <div key={step.step} className="relative pb-6 last:pb-0">
                      {/* Vertical line */}
                      {index < result.pathSteps.length - 1 && (
                        <div
                          className={`absolute -left-4 top-8 w-0.5 h-[calc(100%-8px)] ${getEdgeColor(step.node.type)} border-l-2 border-dashed`}
                        />
                      )}

                      {/* Node */}
                      <div className="flex items-start gap-3">
                        {/* Circle icon */}
                        <div
                          className={`absolute -left-6 top-1 h-7 w-7 rounded-full border-2 flex items-center justify-center shrink-0 ${getNodeColor(step.node.type)}`}
                        >
                          {getNodeIcon(step.node.type)}
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
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
                            <p className="text-xs text-muted-foreground mt-0.5">
                              {step.description}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Edges detail */}
            {result.found && result.edges.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                  <Network className="h-4 w-4 text-accent" />
                  Relaciones del Grafo
                </h4>
                <div className="grid gap-2">
                  {result.edges.map((edge, index) => {
                    const fromNode = result.nodes.find(
                      (n) => n.uri === edge.from
                    );
                    const toNode = result.nodes.find((n) => n.uri === edge.to);

                    return (
                      <div
                        key={index}
                        className="flex items-center gap-2 text-xs bg-secondary/30 rounded-lg px-3 py-2"
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
              </div>
            )}

            {/* SPARQL Query */}
            <div>
              <button
                onClick={() => setShowSparql(!showSparql)}
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                <Code2 className="h-4 w-4" />
                <span>Consulta SPARQL</span>
                {showSparql ? (
                  <ChevronUp className="h-3 w-3" />
                ) : (
                  <ChevronDown className="h-3 w-3" />
                )}
              </button>

              {showSparql && (
                <Card className="mt-2 bg-slate-950 text-slate-50">
                  <CardContent className="p-4">
                    <pre className="text-xs overflow-x-auto whitespace-pre-wrap font-mono leading-relaxed">
                      {result.sparqlQuery}
                    </pre>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        )}

        {/* Not found extra help */}
        {result && !result.found && !isSearching && (
          <div className="text-center py-4 text-sm text-muted-foreground">
            <p>
              Intenta con películas más conocidas o verifica que los títulos sean
              correctos.
            </p>
            <p className="mt-1 text-xs">
              El explorador busca conexiones por director, actor y género
              compartido (hasta 2 saltos).
            </p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
