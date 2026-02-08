"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Navbar } from "@/components/shared/Navbar";
import { ProtectedRoute } from "@/components/shared/ProtectedRoute";
import { MovieSearchInput } from "@/components/recommendation/MovieSearchInput";
import { MovieCard } from "@/components/recommendation/MovieCard";
import {
  Search,
  ArrowLeft,
  Code2,
  ChevronDown,
  ChevronUp,
  Calendar,
  Star,
  User,
  Sparkles,
  Clock,
} from "lucide-react";
import {
  Movie,
  searchMovies,
  MovieSuggestion,
} from "@/services/movies.service";
import { toast } from "sonner";
import Link from "next/link";
import { useRouter } from "next/navigation";

function SearchResultsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryParam = searchParams.get("q") || "";

  const [searchQuery, setSearchQuery] = useState(queryParam);
  const [searchResults, setSearchResults] = useState<Movie[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [showSparqlLog, setShowSparqlLog] = useState(false);
  const [lastSparqlQuery, setLastSparqlQuery] = useState<string>("");
  const [executionTime, setExecutionTime] = useState<number>(0);
  const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);

  // Execute search on mount if query param exists
  useEffect(() => {
    if (queryParam) {
      setSearchQuery(queryParam);
      executeSearch(queryParam);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryParam]);

  const generateSparqlLog = (term: string) => {
    return `PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT DISTINCT ?movie ?title ?directorName ?genreName ?rating ?description ?matchScore ?relationReason
WHERE {
  # 1. Película objetivo (Seed)
  {
    ?seed rdf:type movie:FeatureFilm ;
          movie:hasTitle ?seedTitle .
    FILTER(CONTAINS(LCASE(?seedTitle), "${term.toLowerCase()}"))
    BIND(?seed AS ?movie)
    BIND(200 AS ?baseScore)
    BIND("Coincidencia exacta con tu búsqueda" AS ?relationReason)
  }
  UNION
  # 2. Películas similares por Director
  {
    ?seed rdf:type movie:FeatureFilm ;
          movie:hasTitle ?seedTitle .
    FILTER(CONTAINS(LCASE(?seedTitle), "${term.toLowerCase()}"))
    ?seed movie:hasDirector ?dir .
    ?dir movie:personName ?sharedDirector .
    ?movie movie:hasDirector ?dir .
    FILTER(?seed != ?movie)
    BIND(80 AS ?relScore)
    BIND(CONCAT("Comparten el director ", ?sharedDirector) AS ?relationReason)
  }
  UNION
  # 3. Películas similares por Género
  {
    ?seed rdf:type movie:FeatureFilm ;
          movie:hasTitle ?seedTitle .
    FILTER(CONTAINS(LCASE(?seedTitle), "${term.toLowerCase()}"))
    ?seed movie:hasMainGenre ?g .
    ?g movie:genreName ?sharedGenre .
    ?movie movie:hasMainGenre ?g .
    FILTER(?seed != ?movie)
    BIND(40 AS ?relScore)
    BIND(CONCAT("Comparten el género ", ?sharedGenre) AS ?relationReason)
  }

  ?movie movie:hasTitle ?title .
  OPTIONAL { ?movie movie:hasDirector/movie:personName ?directorName }
  OPTIONAL { ?movie movie:hasMainGenre/movie:genreName ?genreName }
  OPTIONAL { ?movie movie:hasAverageRating ?rating }
  OPTIONAL { ?movie movie:hasPlotSummary ?description }
  BIND(COALESCE(?baseScore, 0) + COALESCE(?relScore, 0) AS ?matchScore)
}
ORDER BY DESC(?matchScore) DESC(?rating)
LIMIT 36`;
  };

  const executeSearch = async (term: string) => {
    if (!term.trim()) return;

    setLastSparqlQuery(generateSparqlLog(term));

    try {
      setIsSearching(true);
      const startTime = Date.now();
      const results = await searchMovies({ q: term, limit: 12 });
      setExecutionTime(Date.now() - startTime);
      setSearchResults(results);
      setHasSearched(true);

      if (results.length === 0) {
        toast.info("No se encontraron películas con ese criterio");
      }
    } catch (error) {
      console.error("Error buscando películas:", error);
      toast.error("Error al buscar películas");
    } finally {
      setIsSearching(false);
    }
  };

  const handleNewSearch = (term: string) => {
    setSearchQuery(term);
    router.push(`/search?q=${encodeURIComponent(term)}`);
  };

  const handleSelectSuggestion = (movie: MovieSuggestion) => {
    setSearchQuery(movie.title);
    router.push(`/search?q=${encodeURIComponent(movie.title)}`);
  };

  const handleViewDetails = (movie: Movie) => {
    setSelectedMovie(movie);
    setShowDetailsDialog(true);
  };

  const handleRecommendSimilar = (movie: Movie) => {
    setSearchQuery(movie.title);
    router.push(`/search?q=${encodeURIComponent(movie.title)}`);
  };

  // Separate seed movie (exact match) from related movies
  const seedMovie = searchResults.find(
    (m) => m.relationReason === "Coincidencia exacta con tu búsqueda"
  );
  const relatedMovies = searchResults.filter(
    (m) => m.relationReason !== "Coincidencia exacta con tu búsqueda"
  );

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-background text-foreground">
        <Navbar />

        <main className="container mx-auto px-4 py-6 max-w-6xl">
          {/* Back + Search bar */}
          <div className="mb-6">
            <Link href="/">
              <Button variant="ghost" size="sm" className="mb-3 -ml-2">
                <ArrowLeft className="h-4 w-4 mr-1" />
                Volver al inicio
              </Button>
            </Link>

            <div className="flex items-center gap-3">
              <div className="flex-1">
                <MovieSearchInput
                  value={searchQuery}
                  onChange={setSearchQuery}
                  onSelect={handleSelectSuggestion}
                  onSubmit={handleNewSearch}
                  placeholder="Buscar películas..."
                  disabled={isSearching}
                  className="bg-secondary/50 border-border"
                />
              </div>
              <Button
                onClick={() => handleNewSearch(searchQuery)}
                disabled={isSearching || !searchQuery.trim()}
                size="lg"
              >
                <Search className="h-4 w-4 mr-2" />
                Buscar
              </Button>
            </div>
          </div>

          {/* Loading state */}
          {isSearching && (
            <div className="space-y-6">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Search className="h-4 w-4 animate-pulse" />
                <span className="text-sm">
                  Buscando en el grafo de conocimiento...
                </span>
              </div>
              {/* Seed skeleton */}
              <Skeleton className="h-48 w-full rounded-lg" />
              {/* Grid skeleton */}
              <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {[...Array(6)].map((_, i) => (
                  <Skeleton key={i} className="h-52 w-full rounded-lg" />
                ))}
              </div>
            </div>
          )}

          {/* Results */}
          {hasSearched && !isSearching && (
            <div className="space-y-6">
              {/* Header */}
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div>
                  <h1 className="text-2xl font-bold">
                    Resultados para &ldquo;{queryParam}&rdquo;
                  </h1>
                  <p className="text-sm text-muted-foreground mt-0.5 flex items-center gap-3">
                    <span>{searchResults.length} película(s) encontrada(s)</span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {executionTime}ms
                    </span>
                  </p>
                </div>

                {lastSparqlQuery && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowSparqlLog(!showSparqlLog)}
                    className="flex items-center gap-2"
                  >
                    <Code2 className="h-4 w-4" />
                    {showSparqlLog ? "Ocultar" : "Ver"} SPARQL
                    {showSparqlLog ? (
                      <ChevronUp className="h-4 w-4" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                  </Button>
                )}
              </div>

              {/* SPARQL Log */}
              {showSparqlLog && lastSparqlQuery && (
                <Card className="bg-slate-950 text-slate-50">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Code2 className="h-4 w-4" />
                      Query SPARQL Ejecutada (Explainable AI)
                    </CardTitle>
                    <CardDescription className="text-slate-400">
                      Consulta semántica ejecutada sobre el grafo de conocimiento
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <pre className="text-xs overflow-x-auto p-4 bg-slate-900 rounded-md border border-slate-800">
                      <code>{lastSparqlQuery}</code>
                    </pre>
                  </CardContent>
                </Card>
              )}

              {/* Seed movie (exact match) */}
              {seedMovie && (
                <div>
                  <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                    <Search className="h-4 w-4 text-accent" />
                    Coincidencia directa
                  </h2>
                  <Card className="border-accent/30 bg-accent/5">
                    <CardContent className="p-5">
                      <div className="flex flex-col md:flex-row gap-5">
                        {/* Info */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <h3 className="text-xl font-bold">
                              {seedMovie.title}
                            </h3>
                            {seedMovie.rating && (
                              <span className="flex items-center gap-1 text-sm shrink-0">
                                <Star className="h-4 w-4 fill-accent text-accent" />
                                <span className="font-semibold text-accent">
                                  {seedMovie.rating.toFixed(1)}
                                </span>
                              </span>
                            )}
                          </div>

                          <div className="flex items-center gap-3 mb-3 text-sm text-muted-foreground">
                            {seedMovie.director && (
                              <span className="flex items-center gap-1">
                                <User className="h-3.5 w-3.5" />
                                {seedMovie.director}
                              </span>
                            )}
                            {seedMovie.year && (
                              <span className="flex items-center gap-1">
                                <Calendar className="h-3.5 w-3.5" />
                                {seedMovie.year}
                              </span>
                            )}
                          </div>

                          {seedMovie.genres && seedMovie.genres.length > 0 && (
                            <div className="flex flex-wrap gap-1.5 mb-3">
                              {seedMovie.genres.map((g, i) => (
                                <Badge
                                  key={i}
                                  variant="secondary"
                                  className="text-xs bg-accent/15 text-accent border-accent/30"
                                >
                                  {g}
                                </Badge>
                              ))}
                            </div>
                          )}

                          {seedMovie.description && (
                            <p className="text-sm text-muted-foreground leading-relaxed">
                              {seedMovie.description}
                            </p>
                          )}
                        </div>

                        {/* Actions */}
                        <div className="flex md:flex-col gap-2 shrink-0">
                          <Button
                            size="sm"
                            onClick={() => handleViewDetails(seedMovie)}
                            className="flex-1 md:flex-none"
                          >
                            Ver Detalles
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleRecommendSimilar(seedMovie)}
                            className="flex-1 md:flex-none"
                          >
                            <Sparkles className="h-3.5 w-3.5 mr-1" />
                            Similares
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}

              {/* Related movies */}
              {relatedMovies.length > 0 && (
                <div>
                  <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-accent" />
                    Películas relacionadas
                  </h2>
                  <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
                    {relatedMovies.map((movie) => (
                      <MovieCard
                        key={movie.uri}
                        movie={movie}
                        onViewDetails={handleViewDetails}
                        onRecommendSimilar={handleRecommendSimilar}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* No results */}
              {searchResults.length === 0 && (
                <div className="text-center py-16 text-muted-foreground">
                  <Search className="h-16 w-16 mx-auto mb-4 opacity-20" />
                  <p className="text-lg font-medium mb-1">
                    No se encontraron resultados
                  </p>
                  <p className="text-sm">
                    Intenta con otro título o utiliza el autocompletado para
                    encontrar la película correcta.
                  </p>
                </div>
              )}
            </div>
          )}
        </main>

        {/* Movie Details Dialog */}
        <Dialog open={showDetailsDialog} onOpenChange={setShowDetailsDialog}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            {selectedMovie && (
              <>
                <DialogHeader>
                  <DialogTitle className="text-2xl pr-6">
                    {selectedMovie.title}
                  </DialogTitle>
                  <DialogDescription>
                    Información completa de la película
                  </DialogDescription>
                </DialogHeader>

                <div className="space-y-6 mt-4">
                  {selectedMovie.genres && selectedMovie.genres.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold mb-2">Géneros</h3>
                      <div className="flex flex-wrap gap-2">
                        {selectedMovie.genres.map((genre, idx) => (
                          <Badge key={idx} variant="secondary">
                            {genre}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="grid gap-4 md:grid-cols-2">
                    {selectedMovie.director && (
                      <div>
                        <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                          <User className="h-4 w-4" />
                          Director
                        </h3>
                        <p className="text-sm text-muted-foreground">
                          {selectedMovie.director}
                        </p>
                      </div>
                    )}

                    {selectedMovie.year && (
                      <div>
                        <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                          <Calendar className="h-4 w-4" />
                          Año
                        </h3>
                        <p className="text-sm text-muted-foreground">
                          {selectedMovie.year}
                        </p>
                      </div>
                    )}

                    {selectedMovie.rating && (
                      <div>
                        <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                          <Star className="h-4 w-4" />
                          Calificación
                        </h3>
                        <div className="flex items-center gap-2">
                          <div className="flex items-center">
                            {[...Array(5)].map((_, i) => (
                              <Star
                                key={i}
                                className={`h-4 w-4 ${
                                  i < Math.floor(selectedMovie.rating!)
                                    ? "fill-yellow-400 text-yellow-400"
                                    : "text-gray-300"
                                }`}
                              />
                            ))}
                          </div>
                          <span className="text-sm font-semibold">
                            {selectedMovie.rating.toFixed(1)}
                          </span>
                        </div>
                      </div>
                    )}

                    {selectedMovie.uri && (
                      <div>
                        <h3 className="text-sm font-semibold mb-2">URI</h3>
                        <p className="text-xs text-muted-foreground font-mono break-all">
                          {selectedMovie.uri}
                        </p>
                      </div>
                    )}
                  </div>

                  {selectedMovie.description && (
                    <div>
                      <h3 className="text-sm font-semibold mb-2">Sinopsis</h3>
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        {selectedMovie.description}
                      </p>
                    </div>
                  )}

                  {selectedMovie.relationReason && (
                    <div className="bg-primary/10 rounded-lg p-4">
                      <h3 className="text-sm font-semibold mb-2">
                        Razón de Recomendación
                      </h3>
                      <p className="text-sm text-primary italic">
                        {selectedMovie.relationReason}
                      </p>
                    </div>
                  )}

                  <div className="flex gap-2 pt-4 border-t">
                    <Button
                      onClick={() => {
                        setShowDetailsDialog(false);
                        handleRecommendSimilar(selectedMovie);
                      }}
                      className="flex-1"
                    >
                      <Sparkles className="mr-2 h-4 w-4" />
                      Buscar Similares
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => setShowDetailsDialog(false)}
                      className="flex-1"
                    >
                      Cerrar
                    </Button>
                  </div>
                </div>
              </>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </ProtectedRoute>
  );
}

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-background flex items-center justify-center">
          <Search className="h-8 w-8 animate-pulse text-muted-foreground" />
        </div>
      }
    >
      <SearchResultsContent />
    </Suspense>
  );
}
