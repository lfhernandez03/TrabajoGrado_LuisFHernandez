"use client";

import { useState, useEffect, useCallback, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Search, SearchX, Code2, ChevronDown, ChevronUp, Clock, Film, User, Tag } from "lucide-react";
import { Navbar } from "@/components/organisms/Navbar";
import { MovieGrid } from "@/components/organisms/MovieGrid";
import { type MovieCardMovie } from "@/components/organisms/MovieCard";
import { Button } from "@/components/ui/button";
import { ProtectedRoute } from "@/components/shared/ProtectedRoute";
import { MovieSearchInput } from "@/components/recommendation/MovieSearchInput";
import { MovieDetailsDialog } from "@/components/home/MovieDetailsDialog";
import { Movie, searchMovies, MovieSuggestion, getMovieNeighborhood } from "@/services/movies.service";
import { addMyFavorite, FavoriteMovie, getMyFavorites, removeMyFavorite } from "@/services/favorites.service";
import { toast } from "sonner";
import { buildDisplaySparqlQuery, type SearchMode } from "@/lib/sparql";
import { cn } from "@/lib/utils";

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

const SEARCH_MODES: { value: SearchMode; label: string; icon: React.ElementType; placeholder: string }[] = [
  { value: 'title',    label: 'Title',   icon: Film, placeholder: 'Search movies by title…' },
  { value: 'director', label: 'Director', icon: User, placeholder: 'Search by director name…' },
  { value: 'genre',    label: 'Genre',   icon: Tag,  placeholder: 'Search by genre (Drama, Action, Comedy…)' },
];

function ExploreContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryParam = searchParams.get("q") ?? "";
  const modeParam = (searchParams.get("mode") ?? "title") as SearchMode;
  const pendingFavs = useRef(new Set<string>());

  const [query, setQuery] = useState(queryParam);
  const [mode, setMode] = useState<SearchMode>(modeParam);
  const [results, setResults] = useState<Movie[]>([]);
  const [directResultCount, setDirectResultCount] = useState(0);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [executionTime, setExecutionTime] = useState(0);
  const [lastSparql, setLastSparql] = useState("");
  const [showSparql, setShowSparql] = useState(false);
  const [favorites, setFavorites] = useState<FavoriteMovie[]>([]);
  const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);

  const loadFavorites = useCallback(async () => {
    try { setFavorites(await getMyFavorites()); } catch { /* not auth */ }
  }, []);

  const executeSearch = useCallback(async (term: string, searchMode: SearchMode) => {
    if (!term.trim()) return;
    setLastSparql(buildDisplaySparqlQuery(term, searchMode));
    setIsSearching(true);
    try {
      const t0 = Date.now();

      // Route the query to the correct API parameter based on mode
      const params =
        searchMode === 'director' ? { director: term, limit: 30 } :
        searchMode === 'genre'    ? { genre: term, limit: 30 } :
                                    { q: term, limit: 30 };

      const data = await searchMovies(params);
      setDirectResultCount(data.length);

      // For title mode, enrich with similar movies from the graph
      let allResults = [...data];
      if (searchMode === 'title' && data.length > 0) {
        try {
          const neighborhood = await getMovieNeighborhood(data[0].title, 1);
          const resultUris = new Set(data.map((m) => m.uri));
          const similarMovies = neighborhood.nodes
            .filter((n) => !resultUris.has(n.uri))
            .map((n) => ({
              uri: n.uri,
              title: n.title,
              posterUrl: n.posterUrl ?? undefined,
              year: n.year ?? undefined,
              runtime: n.runtime ?? undefined,
              genres: n.genre ? [n.genre] : undefined,
              rating: n.rating ?? undefined,
              description: n.description ?? undefined,
              director: n.director ?? undefined,
            } as Movie))
            .slice(0, 12);
          allResults = [...data, ...similarMovies];
        } catch {
          // Continue with direct results if similarity fails
        }
      }

      setExecutionTime(Date.now() - t0);
      setResults(allResults);
      setHasSearched(true);
      if (allResults.length === 0) toast.info("No movies found");
    } catch {
      toast.error("Error searching movies");
    } finally {
      setIsSearching(false);
    }
  }, []);

  useEffect(() => {
    loadFavorites();
    if (queryParam) executeSearch(queryParam, modeParam);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryParam, modeParam]);

  const isFavorite = (uri: string) => favorites.some((f) => f.uri === uri);

  const handleToggleFavorite = async (movie: MovieCardMovie) => {
    if (!movie.uri || pendingFavs.current.has(movie.uri)) return;
    pendingFavs.current.add(movie.uri);
    try {
      const was = isFavorite(movie.uri);
      const updated = was
        ? await removeMyFavorite(movie.uri)
        : await addMyFavorite(movie as Movie);
      setFavorites(updated);
      toast.success(was ? `"${movie.title}" removed from favorites` : `"${movie.title}" added to favorites`);
    } catch {
      toast.error("Could not update favorites");
    } finally {
      pendingFavs.current.delete(movie.uri);
    }
  };

  const handleSearch = () => {
    if (!query.trim()) return;
    router.push(`/search?q=${encodeURIComponent(query.trim())}&mode=${mode}`);
  };

  const handleSelect = (movie: MovieSuggestion) => {
    router.push(`/search?q=${encodeURIComponent(movie.title)}&mode=title`);
  };

  const handleModeChange = (newMode: SearchMode) => {
    setMode(newMode);
    // Clear results when switching mode so stale data isn't shown
    setResults([]);
    setHasSearched(false);
  };

  const handleViewDetails = (movie: MovieCardMovie) => {
    setSelectedMovie(movie as Movie);
    setShowDetailsDialog(true);
  };

  const handleFindSimilar = (movie: MovieCardMovie) => {
    router.push(`/search?q=${encodeURIComponent(movie.title)}&mode=title`);
  };

  const currentModeConfig = SEARCH_MODES.find((m) => m.value === mode) ?? SEARCH_MODES[0];
  const modeLabel =
    mode === 'director' ? 'director' :
    mode === 'genre'    ? 'genre' :
                          'title';

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-bg">
        <Navbar />

        <main className="max-w-7xl mx-auto px-6 py-8">

          {/* Search mode toggle */}
          <div className="flex items-center gap-1 mb-3 w-fit p-1 rounded-lg bg-surface border border-border">
            {SEARCH_MODES.map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                type="button"
                onClick={() => handleModeChange(value)}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all",
                  mode === value
                    ? "bg-teal text-bg shadow-sm"
                    : "text-muted hover:text-text hover:bg-surface2"
                )}
              >
                <Icon className="w-3 h-3" />
                {label}
              </button>
            ))}
          </div>

          {/* Search bar */}
          <div className="flex gap-3 mb-8">
            <div className="flex-1">
              <MovieSearchInput
                value={query}
                onChange={setQuery}
                onSelect={handleSelect}
                onSubmit={handleSearch}
                placeholder={currentModeConfig.placeholder}
                disabled={isSearching}
                mode={mode}
              />
            </div>
            <Button
              variant="primary"
              onClick={handleSearch}
              disabled={isSearching || !query.trim()}
            >
              <Search className="w-4 h-4 mr-1.5" />
              Search
            </Button>
          </div>

          {/* Results header */}
          {hasSearched && (
            <div className="flex items-center justify-between mb-6 flex-wrap gap-2">
              <div>
                <h1 className="font-display text-3xl text-text">
                  {queryParam && (
                    <>
                      <span className="text-muted text-lg font-normal capitalize">{modeLabel}: </span>
                      &ldquo;{queryParam}&rdquo;
                    </>
                  )}
                </h1>
                <p className="text-sm text-muted flex items-center gap-3 mt-1">
                  <span>
                    {directResultCount} result{directResultCount !== 1 ? "s" : ""}
                    {results.length > directResultCount && ` + ${results.length - directResultCount} similar`}
                  </span>
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
                  {showSparql ? "Hide" : "Show"} SPARQL
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
          <MovieGrid
            movies={results.map(toCardMovie)}
            isLoading={isSearching}
            isFavorite={isFavorite}
            onToggleFavorite={handleToggleFavorite}
            onViewDetails={handleViewDetails}
            onFindSimilar={handleFindSimilar}
            emptyMessage={
              hasSearched
                ? `No movies found with that ${modeLabel}.`
                : currentModeConfig.placeholder
            }
            emptyIcon={hasSearched ? SearchX : currentModeConfig.icon}
          />
        </main>

        {/* Movie details dialog */}
        <MovieDetailsDialog
          movie={selectedMovie}
          open={showDetailsDialog}
          onOpenChange={setShowDetailsDialog}
          onRecommendSimilar={(movie) =>
            router.push(`/search?q=${encodeURIComponent(movie.title)}&mode=title`)
          }
        />
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
