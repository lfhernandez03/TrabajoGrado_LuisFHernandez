"use client";

import { useState, useEffect, useCallback } from "react";
import { Navbar } from "@/components/shared/Navbar";
import {
  SearchBar,
  SearchResults,
  ContextRecommendation,
  DiscoverySection,
  FeaturedMoviesSection,
  MovieDetailsDialog,
  HistoryDialog,
  FloatingChatButton,
} from "@/components/home";
import { Movie, searchMovies, getMovieExamples } from "@/services/movies.service";
import { getActivityRecommendation } from "@/services/chat.service";
import { getMyHistory, HistoryEntry } from "@/services/history.service";
import {
  addMyFavorite,
  FavoriteMovie,
  getMyFavorites,
  removeMyFavorite,
} from "@/services/favorites.service";
import { buildDisplaySparqlQuery } from "@/lib/sparql";
import { toast } from "sonner";
import { useAuth } from "@/hooks/useAuth";
import { useRouter } from "next/navigation";

export default function Home() {
  const { user } = useAuth();
  const router = useRouter();

  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Movie[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [lastSparqlQuery, setLastSparqlQuery] = useState("");

  // Movie details dialog
  const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);

  // History dialog
  const [showHistoryDialog, setShowHistoryDialog] = useState(false);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const [favorites, setFavorites] = useState<FavoriteMovie[]>([]);

  // Context recommendation
  const [contextMovie, setContextMovie] = useState<Movie | null>(null);
  const [loadingContext, setLoadingContext] = useState(true);

  const loadHistory = useCallback(async () => {
    try {
      setLoadingHistory(true);
      setHistory(await getMyHistory(10));
    } catch (error) {
      console.error("Error cargando historial:", error);
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  const loadContextRecommendation = useCallback(async () => {
    try {
      setLoadingContext(true);
      const recommendation = await getActivityRecommendation();

      const bestMovie = recommendation.moviesWithScores?.[0];
      if (bestMovie) {
        const canonicalResults = await searchMovies({ q: bestMovie.title, limit: 8 });
        const normalizedBestTitle = bestMovie.title.trim().toLowerCase();
        const canonicalMovie = canonicalResults.find(
          (movie) => movie.title.trim().toLowerCase() === normalizedBestTitle,
        );

        if (canonicalMovie) {
          setContextMovie({
            ...canonicalMovie,
            posterUrl: canonicalMovie.posterUrl || bestMovie.posterUrl,
            runtime: canonicalMovie.runtime ?? bestMovie.runtime,
            rating: canonicalMovie.rating ?? bestMovie.averageRating,
            relationReason:
              typeof bestMovie.compatibilityScore === "number"
                ? `Compatibilidad estimada: ${Math.round(bestMovie.compatibilityScore * 100)}%`
                : canonicalMovie.relationReason,
          });
          return;
        }

        setContextMovie({
          uri:
            bestMovie.uri ||
            `context:${bestMovie.title.toLowerCase().replace(/\s+/g, "-")}`,
          title: bestMovie.title,
          posterUrl: bestMovie.posterUrl,
          runtime: bestMovie.runtime,
          year: bestMovie.releaseDate ? Number(bestMovie.releaseDate) || undefined : undefined,
          genres: bestMovie.genreName ? [bestMovie.genreName] : [],
          rating: bestMovie.averageRating,
          description: bestMovie.description,
          relationReason:
            typeof bestMovie.compatibilityScore === "number"
              ? `Compatibilidad estimada: ${Math.round(bestMovie.compatibilityScore * 100)}%`
              : undefined,
        });
        return;
      }

      const movies = await getMovieExamples(3);
      const nonDemoMovie = movies.find(
        (movie) => movie.title.trim().toLowerCase() !== "demo movie"
      );
      if (nonDemoMovie) {
        setContextMovie(nonDemoMovie);
      } else if (movies.length > 0) {
        setContextMovie(movies[0]);
      } else {
        setContextMovie(null);
      }
    } catch (error) {
      console.error("Error cargando recomendación contextual:", error);
      try {
        const movies = await getMovieExamples(1);
        setContextMovie(movies[0] || null);
      } catch {
        setContextMovie(null);
      }
    } finally {
      setLoadingContext(false);
    }
  }, []);

  const loadFavorites = useCallback(async () => {
    try {
      const list = await getMyFavorites();
      setFavorites(list);
    } catch (error) {
      console.error("Error cargando favoritos:", error);
    }
  }, []);

  const isFavorite = useCallback(
    (movieUri: string) => favorites.some((favorite) => favorite.uri === movieUri),
    [favorites],
  );

  const handleToggleFavorite = useCallback(
    async (movie: Movie) => {
      try {
        const wasFavorite = isFavorite(movie.uri);
        const updatedFavorites = wasFavorite
          ? await removeMyFavorite(movie.uri)
          : await addMyFavorite(movie);

        setFavorites(updatedFavorites);

        if (wasFavorite) {
          toast.success(`"${movie.title}" se eliminó de favoritos`);
        } else {
          toast.success(`"${movie.title}" se agregó a favoritos`);
        }
      } catch (error) {
        console.error("Error actualizando favorito:", error);
        toast.error("No se pudo actualizar favoritos");
      }
    },
    [isFavorite],
  );

  useEffect(() => {
    loadHistory();
    loadContextRecommendation();
    loadFavorites();
  }, [loadHistory, loadContextRecommendation, loadFavorites]);

  const performSearch = useCallback(
    async (query: string, limit = 9) => {
      if (!query.trim()) {
        toast.error("Por favor ingresa un término de búsqueda");
        return;
      }

      setLastSparqlQuery(buildDisplaySparqlQuery(query));
      setIsSearching(true);

      try {
        const results = await searchMovies({ q: query, limit });
        setSearchResults(results);
        setHasSearched(true);

        if (results.length === 0) {
          toast.info("No se encontraron películas con ese criterio");
        }

        loadHistory();
      } catch (error) {
        console.error("Error buscando películas:", error);
        toast.error("Error al buscar películas");
      } finally {
        setIsSearching(false);
      }
    },
    [loadHistory],
  );

  const handleSearch = () => performSearch(searchQuery);

  const handleViewDetails = (movie: Movie) => {
    setSelectedMovie(movie);
    setShowDetailsDialog(true);
  };

  const handleRecommendSimilar = async (movie: Movie) => {
    setSearchQuery(movie.title);
    setIsSearching(true);

    try {
      const results = await searchMovies({ q: movie.title, limit: 12 });
      const similar = results.filter((m) => m.uri !== movie.uri);

      setSearchResults(similar);
      setHasSearched(true);

      if (similar.length === 0) {
        toast.info(`No se encontraron películas similares a "${movie.title}"`);
      } else {
        toast.success(`Encontradas ${similar.length} películas similares a "${movie.title}"`);
      }

      window.scrollTo({ top: 0, behavior: "smooth" });
      loadHistory();
    } catch (error) {
      console.error("Error buscando películas similares:", error);
      toast.error("Error al buscar películas similares");
    } finally {
      setIsSearching(false);
    }
  };

  const handleRepeatSearch = (query: string) => {
    setSearchQuery(query);
    performSearch(query);
  };

  function navigateToSearch(title: string): void {
    setSearchQuery(title);
    performSearch(title);
  }

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <SearchBar
        searchQuery={searchQuery}
        onSearchQueryChange={setSearchQuery}
        onSearch={handleSearch}
        onNavigateFavorites={() => router.push("/favorites")}
        onOpenHistory={() => setShowHistoryDialog(true)}
        onNavigateChat={() => router.push("/chat")}
        isSearching={isSearching}
      />

      <main className="container mx-auto px-4 pb-8">
        {hasSearched && (
          <SearchResults
            searchQuery={searchQuery}
            searchResults={searchResults}
            lastSparqlQuery={lastSparqlQuery}
            onViewDetails={handleViewDetails}
            onRecommendSimilar={handleRecommendSimilar}
            isFavorite={isFavorite}
            onToggleFavorite={handleToggleFavorite}
          />
        )}

        {!hasSearched && (
          <>
            <ContextRecommendation
              userName={user?.name}
              contextMovie={contextMovie}
              isLoading={loadingContext}
              onViewDetails={handleViewDetails}
              onRecommendSimilar={handleRecommendSimilar}
              isFavorite={isFavorite}
              onToggleFavorite={handleToggleFavorite}
            />
            <DiscoverySection />
            <FeaturedMoviesSection
              onViewDetails={handleViewDetails}
              onRecommendSimilar={(movie: Movie) => navigateToSearch(movie.title)}
              isFavorite={isFavorite}
              onToggleFavorite={handleToggleFavorite}
            />
          </>
        )}
      </main>

      <MovieDetailsDialog
        movie={selectedMovie}
        open={showDetailsDialog}
        onOpenChange={setShowDetailsDialog}
        onRecommendSimilar={handleRecommendSimilar}
      />

      <HistoryDialog
        open={showHistoryDialog}
        onOpenChange={setShowHistoryDialog}
        history={history}
        isLoading={loadingHistory}
        onRepeatSearch={handleRepeatSearch}
        onRefresh={loadHistory}
      />

      <FloatingChatButton />
    </div>
  );
}
