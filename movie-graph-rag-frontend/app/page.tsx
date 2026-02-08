"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Navbar } from "@/components/shared/Navbar";
import { MoviesCarousel } from "@/components/recommendation/MoviesCarousel";
import { Search, Sparkles, Code2, ChevronDown, ChevronUp, Calendar, Star, User, History, Heart, Shuffle, Smile, Network, Compass } from "lucide-react";
import { Movie, searchMovies, getMovieExamples } from "@/services/movies.service";
import { getMyHistory, HistoryEntry } from "@/services/history.service";
import { toast } from "sonner";
import { MovieCard } from "@/components/recommendation/MovieCard";
import { useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useRouter } from "next/navigation";
import { Skeleton } from "@/components/ui/skeleton";

export default function Home() {
  const { user } = useAuth();
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Movie[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [showSparqlLog, setShowSparqlLog] = useState(false);
  const [lastSparqlQuery, setLastSparqlQuery] = useState<string>("");
  const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);
  const [showHistoryDialog, setShowHistoryDialog] = useState(false);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [contextMovie, setContextMovie] = useState<Movie | null>(null);
  const [loadingContext, setLoadingContext] = useState(true);
  const [selectedGenre, setSelectedGenre] = useState<string>("");

  useEffect(() => {
    loadHistory();
    loadContextRecommendation();
  }, []);

  const loadContextRecommendation = async () => {
    try {
      setLoadingContext(true);
      const movies = await getMovieExamples(1);
      if (movies.length > 0) {
        setContextMovie(movies[0]);
      }
    } catch (error) {
      console.error("Error cargando recomendación contextual:", error);
    } finally {
      setLoadingContext(false);
    }
  };

  const loadHistory = async () => {
    try {
      setLoadingHistory(true);
      const historyData = await getMyHistory(10);
      setHistory(historyData);
    } catch (error) {
      console.error("Error cargando historial:", error);
      // No mostrar error si el usuario no está autenticado
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      toast.error("Por favor ingresa un término de búsqueda");
      return;
    }

    // Generar log de la query SPARQL para mostrar al usuario
    const sparqlQuery = `PREFIX movie: <http://www.movies.org/movie/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT DISTINCT ?movie ?title ?directorName ?genreName ?rating ?description ?matchScore ?relationReason
WHERE {
  # 1. Encontrar la película objetivo (Seed)
  {
    ?seed rdf:type movie:FeatureFilm ;
          movie:hasTitle ?seedTitle .
    FILTER(CONTAINS(LCASE(?seedTitle), "${searchQuery.toLowerCase()}"))
    BIND(?seed AS ?movie)
    BIND(200 AS ?baseScore)
    BIND("Coincidencia exacta con tu búsqueda" AS ?relationReason)
  }
  UNION
  # 2. Encontrar películas similares por Director
  {
    ?seed rdf:type movie:FeatureFilm ;
          movie:hasTitle ?seedTitle .
    FILTER(CONTAINS(LCASE(?seedTitle), "${searchQuery.toLowerCase()}"))
    
    ?seed movie:hasDirector ?dir . 
    ?dir movie:personName ?sharedDirector .
    ?movie movie:hasDirector ?dir .
    FILTER(?seed != ?movie)
    BIND(80 AS ?relScore)
    BIND(CONCAT("Recomendado porque comparten el director ", ?sharedDirector) AS ?relationReason)
  }
  UNION
  # 3. Encontrar películas similares por Género
  {
    ?seed rdf:type movie:FeatureFilm ;
          movie:hasTitle ?seedTitle .
    FILTER(CONTAINS(LCASE(?seedTitle), "${searchQuery.toLowerCase()}"))
    
    ?seed movie:hasMainGenre ?g . 
    ?g movie:genreName ?sharedGenre .
    ?movie movie:hasMainGenre ?g .
    FILTER(?seed != ?movie)
    BIND(40 AS ?relScore)
    BIND(CONCAT("Recomendado porque comparten el género ", ?sharedGenre) AS ?relationReason)
  }

  # 4. Extraer info de la película resultante
  ?movie movie:hasTitle ?title .
  OPTIONAL { ?movie movie:hasDirector/movie:personName ?directorName }
  OPTIONAL { ?movie movie:hasMainGenre/movie:genreName ?genreName }
  OPTIONAL { ?movie movie:hasAverageRating ?rating }
  OPTIONAL { ?movie movie:hasPlotSummary ?description }

  BIND(COALESCE(?baseScore, 0) + COALESCE(?relScore, 0) AS ?matchScore)
}
ORDER BY DESC(?matchScore) DESC(?rating)
LIMIT 36`;

    setLastSparqlQuery(sparqlQuery);

    try {
      setIsSearching(true);
      const results = await searchMovies({ q: searchQuery, limit: 9 });
      setSearchResults(results);
      setHasSearched(true);
      
      if (results.length === 0) {
        toast.info("No se encontraron películas con ese criterio");
      }
      
      // Recargar historial después de la búsqueda
      loadHistory();
    } catch (error) {
      console.error("Error buscando películas:", error);
      toast.error("Error al buscar películas");
    } finally {
      setIsSearching(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const handleViewDetails = (movie: Movie) => {
    setSelectedMovie(movie);
    setShowDetailsDialog(true);
  };

  const handleRecommendSimilar = async (movie: Movie) => {
    // Usar el título de la película para buscar similares
    setSearchQuery(movie.title);
    
    try {
      setIsSearching(true);
      const results = await searchMovies({ q: movie.title, limit: 12 });
      
      // Filtrar la película actual de los resultados
      const similarMovies = results.filter(m => m.uri !== movie.uri);
      
      setSearchResults(similarMovies);
      setHasSearched(true);
      
      if (similarMovies.length === 0) {
        toast.info(`No se encontraron películas similares a "${movie.title}"`);
      } else {
        toast.success(`Encontradas ${similarMovies.length} películas similares a "${movie.title}"`);
      }
      
      // Scroll suave a los resultados
      window.scrollTo({ top: 0, behavior: 'smooth' });
      
      // Recargar historial después de la búsqueda
      loadHistory();
    } catch (error) {
      console.error("Error buscando películas similares:", error);
      toast.error("Error al buscar películas similares");
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      {/* Search Bar + Favorites + History — directly below navbar */}
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <Input
              placeholder="Buscar películas..."
              className="w-full pr-10 bg-secondary/50 border-border"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isSearching}
            />
            <button
              onClick={handleSearch}
              disabled={isSearching}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-primary transition-colors"
            >
              <Search className="h-5 w-5" />
            </button>
          </div>

          {/* Favorites button */}
          <Button
            variant="ghost"
            size="icon"
            className="shrink-0 text-muted-foreground hover:text-primary"
            title="Favoritos"
          >
            <Heart className="h-5 w-5" />
          </Button>

          {/* History button */}
          <Button
            variant="ghost"
            size="icon"
            className="shrink-0 text-muted-foreground hover:text-primary"
            onClick={() => setShowHistoryDialog(true)}
            title="Historial"
          >
            <History className="h-5 w-5" />
          </Button>
        </div>
      </div>

      <main className="container mx-auto px-4 pb-8">

        {/* Search Results */}
        {hasSearched && (
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

            {/* SPARQL Log Section */}
            {showSparqlLog && lastSparqlQuery && (
              <Card className="mb-4 bg-slate-950 text-slate-50">
                <CardHeader>
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Code2 className="h-4 w-4" />
                    Query SPARQL Ejecutada (Explainable AI)
                  </CardTitle>
                  <CardDescription className="text-slate-400">
                    Esta es la consulta semántica que se ejecutó sobre el grafo de conocimiento
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
                    onViewDetails={handleViewDetails}
                    onRecommendSimilar={handleRecommendSimilar}
                  />
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No se encontraron resultados para &ldquo;{searchQuery}&rdquo;
              </div>
            )}
          </div>
        )}

        {/* ===== SECTION 1: Context Recommendation ===== */}
        {!hasSearched && (
          <section className="mb-10 ">
            <div className="mb-4">
              <h2 className="text-2xl font-semibold">
                ¡Hola, {user?.name?.split(" ")[0] || "Cinéfilo"}!
              </h2>
              <p className="text-muted-foreground text-sm mt-1">
                Basado en tu actividad, te recomendamos
              </p>
            </div>

            <div className="grid gap-6 md:grid-cols-[1fr_auto] items-center">
              {/* Context Movie Card */}
              <div>
                {loadingContext ? (
                  <Card className="bg-card border-border p-5 space-y-3">
                    <Skeleton className="h-5 w-3/4" />
                    <Skeleton className="h-4 w-1/2" />
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-5/6" />
                    <div className="flex gap-2 pt-2">
                      <Skeleton className="h-9 flex-1" />
                      <Skeleton className="h-9 flex-1" />
                    </div>
                  </Card>
                ) : contextMovie ? (
                  <MovieCard
                    movie={contextMovie}
                    onViewDetails={handleViewDetails}
                    onRecommendSimilar={handleRecommendSimilar}
                  />
                ) : null}
              </div>

              {/* Explanation text */}
              <div className="hidden md:flex flex-col gap-2 w-72 text-sm text-muted-foreground leading-relaxed">
                <p>
                  Te recomendamos esta película porque en tus últimas búsquedas
                  mostraste interés en el género <span className="text-accent font-medium">Sci-Fi</span> y
                  en películas dirigidas por <span className="text-accent font-medium">Christopher Nolan</span>.
                </p>
                <p className="mt-1">
                  Nuestro sistema de grafos de conocimiento encontró una alta
                  compatibilidad semántica con tu perfil de preferencias.
                </p>
              </div>
            </div>
          </section>
        )}

        {/* ===== SECTION 2: Intelligent Discovery ===== */}
        {!hasSearched && (
          <section className="mb-10">
            <div className="mb-6">
              <h2 className="text-2xl font-semibold text-center">
                Descubrimiento Inteligente
              </h2>
              <p className="text-muted-foreground text-sm mt-1 text-center">
                Explora películas de formas únicas usando el poder del grafo de conocimiento
              </p>
            </div>

            {/* Feature cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <Card
                className="bg-card border-border hover:border-accent/60 transition-all cursor-pointer group"
                onClick={() => router.push("/connections")}
              >
                <CardContent className="p-4 flex flex-col items-center text-center gap-2">
                  <div className="h-12 w-12 rounded-full bg-accent/10 flex items-center justify-center group-hover:bg-accent/20 transition-colors">
                    <Network className="h-6 w-6 text-accent" />
                  </div>
                  <h3 className="font-semibold text-base">Explorador de Conexiones</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Descubre el camino semántico entre dos películas o directores en el grafo
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-card border-border hover:border-accent/60 transition-all cursor-pointer group">
                <CardContent className="p-4 flex flex-col items-center text-center gap-2">
                  <div className="h-12 w-12 rounded-full bg-accent/10 flex items-center justify-center group-hover:bg-accent/20 transition-colors">
                    <Compass className="h-6 w-6 text-accent" />
                  </div>
                  <h3 className="font-semibold text-base">Viaje Cinematográfico</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Recorre una secuencia curada de 5-7 películas conectadas temáticamente
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-card border-border hover:border-accent/60 transition-all cursor-pointer group">
                <CardContent className="p-4 flex flex-col items-center text-center gap-2">
                  <div className="h-12 w-12 rounded-full bg-accent/10 flex items-center justify-center group-hover:bg-accent/20 transition-colors">
                    <Shuffle className="h-6 w-6 text-accent" />
                  </div>
                  <h3 className="font-semibold text-base">Rueda Aleatoria</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Navegación multihop por el grafo para descubrir algo completamente nuevo
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-card border-border hover:border-accent/60 transition-all cursor-pointer group">
                <CardContent className="p-4 flex flex-col items-center text-center gap-2">
                  <div className="h-12 w-12 rounded-full bg-accent/10 flex items-center justify-center group-hover:bg-accent/20 transition-colors">
                    <Smile className="h-6 w-6 text-accent" />
                  </div>
                  <h3 className="font-semibold text-base">Selector Emocional</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Recomendaciones basadas en tu estado de ánimo y preferencias del momento
                  </p>
                </CardContent>
              </Card>
            </div>
          </section>
        )}

        {/* ===== SECTION 3: Browse by Genre + Carousel ===== */}
        {!hasSearched && (
          <section className="mb-10">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-semibold">Películas Destacadas</h2>
                <p className="text-muted-foreground text-sm mt-1">
                  Explora nuestro catálogo de películas
                </p>
              </div>

              {/* Genre filter dropdown */}
              <select
                value={selectedGenre}
                onChange={(e) => setSelectedGenre(e.target.value)}
                className="bg-secondary/50 border border-border text-foreground text-sm rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-accent"
              >
                <option value="">Género</option>
                <option value="Action">Acción</option>
                <option value="Comedy">Comedia</option>
                <option value="Drama">Drama</option>
                <option value="Horror">Terror</option>
                <option value="Sci-Fi">Ciencia Ficción</option>
                <option value="Romance">Romance</option>
                <option value="Thriller">Thriller</option>
              </select>
            </div>

            <MoviesCarousel
              itemsPerPage={3}
              onViewDetails={handleViewDetails}
              onRecommendSimilar={handleRecommendSimilar}
            />
          </section>
        )}
      </main>

      {/* Dialog de Detalles de Película */}
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
                {/* Géneros */}
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

                {/* Información Principal */}
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

                {/* Descripción */}
                {selectedMovie.description && (
                  <div>
                    <h3 className="text-sm font-semibold mb-2">Sinopsis</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      {selectedMovie.description}
                    </p>
                  </div>
                )}

                {/* Razón de Relación */}
                {selectedMovie.relationReason && (
                  <div className="bg-primary/10 rounded-lg p-4">
                    <h3 className="text-sm font-semibold mb-2">Razón de Recomendación</h3>
                    <p className="text-sm text-primary italic">
                      {selectedMovie.relationReason}
                    </p>
                  </div>
                )}

                {/* Acciones */}
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

      {/* Floating Chatbot Button */}
      <div className="fixed bottom-6 right-6 z-50 flex items-end gap-3">
        <div className="bg-card border border-accent/40 text-foreground text-sm rounded-2xl rounded-br-none px-4 py-3 shadow-lg max-w-[200px]">
          <p className="font-medium text-accent">¿Necesitas ayuda?</p>
          <p className="text-muted-foreground text-xs mt-0.5">
            Pregúntame sobre películas, géneros o recomendaciones.
          </p>
        </div>
        <button
          className="h-14 w-14 shrink-0 rounded-full bg-accent text-accent-foreground shadow-lg hover:bg-accent/90 transition-all hover:scale-105 flex items-center justify-center"
          title="Asistente IA"
        >
          <Sparkles className="h-6 w-6" />
        </button>
      </div>

      {/* Dialog de Historial */}
      <Dialog open={showHistoryDialog} onOpenChange={setShowHistoryDialog}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <History className="h-5 w-5" />
              Historial de Búsquedas
            </DialogTitle>
            <DialogDescription>
              Tus últimas {history.length} consultas realizadas
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 mt-4">
            {loadingHistory ? (
              <div className="text-center py-8 text-muted-foreground">
                Cargando historial...
              </div>
            ) : history.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No hay búsquedas en el historial aún
              </div>
            ) : (
              history.map((entry) => (
                <Card key={entry._id} className="hover:shadow-md transition-shadow">
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <CardTitle className="text-base flex items-center gap-2">
                          <Search className="h-4 w-4" />
                          {entry.query}
                        </CardTitle>
                        <CardDescription className="flex items-center gap-4 mt-2">
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {new Date(entry.createdAt).toLocaleString('es-ES', {
                              dateStyle: 'short',
                              timeStyle: 'short',
                            })}
                          </span>
                          {entry.executionTimeMs && (
                            <span className="text-xs">
                              ⏱️ {entry.executionTimeMs}ms
                            </span>
                          )}
                          <Badge variant={entry.wasSuccessful ? "default" : "destructive"}>
                            {entry.wasSuccessful ? "Exitosa" : "Error"}
                          </Badge>
                        </CardDescription>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setSearchQuery(entry.query);
                          setShowHistoryDialog(false);
                          handleSearch();
                        }}
                      >
                        Repetir
                      </Button>
                    </div>
                  </CardHeader>
                  {entry.resultsFound && entry.resultsFound.length > 0 && (
                    <CardContent>
                      <p className="text-sm text-muted-foreground">
                        {entry.resultsFound.length} película(s) encontrada(s)
                      </p>
                      {entry.sparqlExecuted && (
                        <details className="mt-2">
                          <summary className="text-xs cursor-pointer text-muted-foreground hover:text-foreground">
                            Ver Query SPARQL
                          </summary>
                          <pre className="text-xs mt-2 p-2 bg-slate-950 text-slate-50 rounded overflow-x-auto">
                            <code>{entry.sparqlExecuted}</code>
                          </pre>
                        </details>
                      )}
                    </CardContent>
                  )}
                </Card>
              ))
            )}
          </div>

          <div className="flex gap-2 pt-4 border-t mt-4">
            <Button
              variant="outline"
              onClick={() => {
                loadHistory();
                toast.success("Historial actualizado");
              }}
              className="flex-1"
            >
              Actualizar
            </Button>
            <Button
              variant="outline"
              onClick={() => setShowHistoryDialog(false)}
              className="flex-1"
            >
              Cerrar
            </Button>
          </div>
        </DialogContent>
      </Dialog>


    </div>
  );
}
