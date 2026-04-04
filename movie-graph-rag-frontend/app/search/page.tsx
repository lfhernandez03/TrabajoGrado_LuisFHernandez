"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Search, Code2, ChevronDown, ChevronUp, Clock } from "lucide-react";
import { Navbar } from "@/components/organisms/Navbar";
import { MovieGrid } from "@/components/organisms/MovieGrid";
import { type MovieCardMovie } from "@/components/organisms/MovieCard";
import { Button } from "@/components/ui/button";
import { ProtectedRoute } from "@/components/shared/ProtectedRoute";
import { MovieSearchInput } from "@/components/recommendation/MovieSearchInput";
import { Movie, searchMovies, MovieSuggestion } from "@/services/movies.service";
import { addMyFavorite, FavoriteMovie, getMyFavorites, removeMyFavorite } from "@/services/favorites.service";
import { toast } from "sonner";
import { buildDisplaySparqlQuery } from "@/lib/sparql";

function toCardMovie(m: Movie): MovieCardMovie {
  return {
    uri: m.uri,
    title: m.title,
    posterUrl: m.posterUrl,
    year: m.year,
    runtime: m.runtime,
    genres: m.genres,
    rating: m.rating,
    director: m.director,
    description: m.description,
  };
}

function ExploreContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryParam = searchParams.get("q") ?? "";

  const [query, setQuery] = useState(queryParam);
  const [results, setResults] = useState<Movie[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [executionTime, setExecutionTime] = useState(0);
  const [lastSparql, setLastSparql] = useState("");
  const [showSparql, setShowSparql] = useState(false);
  const [favorites, setFavorites] = useState<FavoriteMovie[]>([]);

  const loadFavorites = useCallback(async () => {
    try { setFavorites(await getMyFavorites()); } catch { /* not auth */ }
  }, []);

  useEffect(() => {
    loadFavorites();
    if (queryParam) executeSearch(queryParam);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryParam]);

  const isFavorite = (uri: string) => favorites.some((f) => f.uri === uri);

  const handleToggleFavorite = async (movie: MovieCardMovie) => {
    if (!movie.uri) return;
    try {
      const was = isFavorite(movie.uri);
      const updated = was
        ? await removeMyFavorite(movie.uri)
        : await addMyFavorite(movie as Movie);
      setFavorites(updated);
      toast.success(was ? `"${movie.title}" eliminado de favoritos` : `"${movie.title}" agregado a favoritos`);
    } catch { toast.error("No se pudo actualizar favoritos"); }
  };

  const executeSearch = async (term: string) => {
    if (!term.trim()) return;
    setLastSparql(buildDisplaySparqlQuery(term));
    setIsSearching(true);
    try {
      const t0 = Date.now();
      const data = await searchMovies({ q: term, limit: 30 });
      setExecutionTime(Date.now() - t0);
      setResults(data);
      setHasSearched(true);
      if (data.length === 0) toast.info("No se encontraron películas");
    } catch { toast.error("Error al buscar películas"); }
    finally { setIsSearching(false); }
  };

  const handleSearch = () => {
    router.push(`/search?q=${encodeURIComponent(query.trim())}`);
  };

  const handleSelect = (movie: MovieSuggestion) => {
    router.push(`/search?q=${encodeURIComponent(movie.title)}`);
  };

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-bg">
        <Navbar />

        <main className="max-w-7xl mx-auto px-6 py-8">

          {/* Search bar */}
          <div className="flex gap-3 mb-8">
            <div className="flex-1">
              <MovieSearchInput
                value={query}
                onChange={setQuery}
                onSelect={handleSelect}
                onSubmit={handleSearch}
                placeholder="Buscar películas por título, director, género…"
                disabled={isSearching}
              />
            </div>
            <Button
              variant="primary"
              onClick={handleSearch}
              disabled={isSearching || !query.trim()}
            >
              <Search className="w-4 h-4 mr-1.5" />
              Buscar
            </Button>
          </div>

          {/* Results header */}
          {hasSearched && (
            <div className="flex items-center justify-between mb-6 flex-wrap gap-2">
            <div>
                <h1 className="font-display text-3xl text-text">
                  {queryParam && `"${queryParam}"`}
                </h1>
                <p className="text-sm text-muted flex items-center gap-3 mt-1">
                  <span>{results.length} resultado{results.length !== 1 ? "s" : ""}</span>
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />{executionTime}ms
                  </span>
                </p>
              </div>

              {lastSparql && (
                <button
                  type="button"
                  onClick={() => setShowSparql((v) => !v)}
                  className="flex items-center gap-1.5 text-xs text-muted hover:text-accent transition-colors"
                >
                  <Code2 className="w-3.5 h-3.5" />
                  {showSparql ? "Ocultar" : "Ver"} SPARQL
                  {showSparql ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                </button>
              )}
            </div>
          )}

          {/* SPARQL viewer */}
          {showSparql && lastSparql && (
            <div className="mb-6 rounded-lg bg-surface border border-border2 overflow-hidden">
              <div className="px-4 py-2 border-b border-border flex items-center gap-2">
                <Code2 className="w-4 h-4 text-teal" />
                <span className="text-xs font-medium text-teal">SPARQL Query — Explainable AI</span>
              </div>
              <pre className="text-xs text-muted p-4 overflow-x-auto leading-relaxed">
                <code>{lastSparql}</code>
              </pre>
            </div>
          )}

          {/* Main grid */}
          <div className="w-full">
            <MovieGrid
              movies={results.map(toCardMovie)}
              isLoading={isSearching}
              isFavorite={isFavorite}
              onToggleFavorite={handleToggleFavorite}
              emptyMessage={
                hasSearched
                  ? "No se encontraron películas con esos criterios."
                  : "Usa el buscador para encontrar películas."
              }
            />

            {/* Empty initial state */}
            {!hasSearched && !isSearching && (
              <div className="flex flex-col items-center justify-center py-32 text-center">
                <Search className="w-14 h-14 text-muted/20 mb-4" />
                <p className="text-muted text-sm max-w-xs">
                  Busca por título, director o género para explorar el catálogo.
                </p>
              </div>
            )}
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-bg flex items-center justify-center">
          <Search className="w-8 h-8 text-muted animate-pulse" />
        </div>
      }
    >
      <ExploreContent />
    </Suspense>
  );
}
