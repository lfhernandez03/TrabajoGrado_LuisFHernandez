"use client";

import { useState, useEffect, useCallback } from "react";
import { Navbar } from "@/components/organisms/Navbar";
import { HeroSection, type HeroMovie } from "@/components/organisms/HeroSection";
import { RecommendationCarousel } from "@/components/organisms/RecommendationCarousel";
import { type MovieCardMovie } from "@/components/organisms/MovieCard";
import { MovieDetailsDialog } from "@/components/home/MovieDetailsDialog";
import { Movie, searchMovies, getMovieExamples, getMoviesByCentrality, getMovieNeighborhood, type RecommendedMovie } from "@/services/movies.service";
import { getActivityRecommendation } from "@/services/chat.service";
import {
  addMyFavorite,
  FavoriteMovie,
  getMyFavorites,
  removeMyFavorite,
} from "@/services/favorites.service";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

// ── Adapters ─────────────────────────────────────────────────────────────────

function toCardMovie(movie: Movie | FavoriteMovie): MovieCardMovie {
  return {
    uri: movie.uri,
    title: movie.title,
    posterUrl: movie.posterUrl,
    year: movie.year,
    runtime: movie.runtime,
    genres: movie.genres,
    rating: movie.rating,
    director: (movie as Movie).director,
  };
}

function recToCardMovie(movie: RecommendedMovie): MovieCardMovie {
  return {
    uri: '',
    title: movie.title,
    posterUrl: movie.posterUrl ?? undefined,
    year: movie.year ?? undefined,
    runtime: movie.runtime ?? undefined,
    genres: movie.genres ?? (movie.genreName ? [movie.genreName] : undefined),
    rating: movie.averageRating ?? undefined,
    compatibilityScore: movie.compatibilityScore,
    serendipityScore: movie.serendipityScore,
  };
}

export default function Home() {
  const router = useRouter();

  // ── Hero ──────────────────────────────────────────────────────────────────
  const [heroMovie, setHeroMovie] = useState<HeroMovie | null>(null);
  const [heroLoading, setHeroLoading] = useState(true);
  const [heroFavorite, setHeroFavorite] = useState(false);

  // ── Carousels ─────────────────────────────────────────────────────────────
  const [carousel1, setCarousel1] = useState<MovieCardMovie[]>([]);
  const [carousel2, setCarousel2] = useState<MovieCardMovie[]>([]);
  const [carousel3, setCarousel3] = useState<MovieCardMovie[]>([]);
  const [carouselLoading, setCarouselLoading] = useState(true);

  // ── Favorites ─────────────────────────────────────────────────────────────
  const [favorites, setFavorites] = useState<FavoriteMovie[]>([]);

  // ── Movie details dialog ──────────────────────────────────────────────────
  const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);

  // ── Data loading ──────────────────────────────────────────────────────────

  const loadFavorites = useCallback(async () => {
    try {
      setFavorites(await getMyFavorites());
    } catch {
      // silently fail — user may not be authenticated
    }
  }, []);

  const loadHero = useCallback(async (): Promise<string | undefined> => {
    setHeroLoading(true);
    try {
      const rec = await getActivityRecommendation();
      const best = rec.moviesWithScores?.[0];
      if (best) {
        // Try to enrich with canonical poster
        try {
          const results = await searchMovies({ q: best.title, limit: 5 });
          const canonical = results.find(
            (m) => m.title.trim().toLowerCase() === best.title.trim().toLowerCase()
          );
          if (canonical) {
            setHeroMovie({
              title: canonical.title,
              posterUrl: canonical.posterUrl ?? best.posterUrl,
              genreName: best.genreName ?? canonical.genres?.[0],
              genres: canonical.genres,
              director: canonical.director,
              runtime: canonical.runtime ?? best.runtime,
              compatibilityScore: best.compatibilityScore,
              explanation: rec.explanation,
            });
            return canonical.title;
          }
        } catch { /* ignore enrichment errors */ }

        setHeroMovie({
          title: best.title,
          posterUrl: best.posterUrl,
          genreName: best.genreName,
          runtime: best.runtime,
          compatibilityScore: best.compatibilityScore,
          explanation: rec.explanation,
        });
        return best.title;
      } else {
        // Fallback to an example movie
        const examples = await getMovieExamples(1);
        if (examples[0]) {
          setHeroMovie({ title: examples[0].title, posterUrl: examples[0].posterUrl });
          return examples[0].title;
        }
      }
    } catch {
      const examples = await getMovieExamples(1).catch(() => []);
      if (examples[0]) {
        setHeroMovie({ title: examples[0].title, posterUrl: examples[0].posterUrl });
        return examples[0].title;
      }
    } finally {
      setHeroLoading(false);
    }
  }, []);

  const loadCarousels = useCallback(async (featuredTitle?: string) => {
    setCarouselLoading(true);
    try {
      const [neighborhood, centrality, serendipity] = await Promise.allSettled([
        // "Porque viste X" — neighborhood of the hero movie
        featuredTitle
          ? getMovieNeighborhood(featuredTitle, 1).then((r) => r.nodes.map((n) => ({
              uri: n.uri, title: n.title, posterUrl: n.poster_url ?? undefined,
              genres: n.genre ? [n.genre] : undefined, rating: n.rating ?? undefined,
            } as MovieCardMovie)))
          : getMovieExamples(12).then((arr) => arr.map(toCardMovie)),
        // "Basado en favoritos" — highest centrality (most connected)
        getMoviesByCentrality(undefined, 12).then((r) => r.movies.map(recToCardMovie)),
        // "Explora algo diferente" — centrality sorted by serendipity desc
        getMoviesByCentrality(undefined, 20).then((r) =>
          [...r.movies]
            .sort((a, b) => (b.serendipityScore ?? 0) - (a.serendipityScore ?? 0))
            .slice(0, 12)
            .map(recToCardMovie)
        ),
      ]);

      const fallback = () => getMovieExamples(12).then((arr) => arr.map(toCardMovie));

      setCarousel1(neighborhood.status === 'fulfilled' ? neighborhood.value : await fallback());
      setCarousel2(centrality.status === 'fulfilled' ? centrality.value : await fallback());
      setCarousel3(serendipity.status === 'fulfilled' ? serendipity.value : await fallback());
    } catch {
      toast.error("No se pudieron cargar las recomendaciones");
    } finally {
      setCarouselLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFavorites();
    loadHero().then((title) => loadCarousels(title));
  }, [loadFavorites, loadHero, loadCarousels]);

  // ── Favorites helpers ─────────────────────────────────────────────────────

  const isFavorite = useCallback(
    (uri: string) => favorites.some((f) => f.uri === uri),
    [favorites]
  );

  const handleToggleFavorite = useCallback(
    async (movie: MovieCardMovie) => {
      if (!movie.uri) return;
      try {
        const was = isFavorite(movie.uri);
        const updated = was
          ? await removeMyFavorite(movie.uri)
          : await addMyFavorite(movie as Movie);
        setFavorites(updated);
        toast.success(was ? `"${movie.title}" eliminado de favoritos` : `"${movie.title}" agregado a favoritos`);
        // Update hero fav status
        if (heroMovie && movie.title === heroMovie.title) setHeroFavorite(!was);
      } catch {
        toast.error("No se pudo actualizar favoritos");
      }
    },
    [isFavorite, heroMovie]
  );

  const handleViewDetails = useCallback((movie: MovieCardMovie) => {
    setSelectedMovie(movie as Movie);
    setShowDetailsDialog(true);
  }, []);

  const handleHeroDetails = useCallback(() => {
    if (!heroMovie) return;
    router.push(`/search?q=${encodeURIComponent(heroMovie.title)}`);
  }, [heroMovie, router]);

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-bg">
      <Navbar />

      {/* Hero */}
      <HeroSection
        featuredMovie={heroMovie}
        isLoading={heroLoading}
        isFavorite={heroFavorite}
        onToggleFavorite={() => heroMovie && handleToggleFavorite({ title: heroMovie.title })}
        onViewDetails={handleHeroDetails}
      />

      {/* Carousels */}
      <div className="max-w-7xl mx-auto px-6 pb-20 flex flex-col gap-12">
        <RecommendationCarousel
          title="Porque viste"
          subtitle={heroMovie?.title ?? "…"}
          movies={carousel1}
          isLoading={carouselLoading}
          viewAllHref="/search"
          showLiveIndicator
          isFavorite={isFavorite}
          onToggleFavorite={handleToggleFavorite}
          onViewDetails={handleViewDetails}
        />

        <RecommendationCarousel
          title="Basado en tus favoritos"
          movies={carousel2}
          isLoading={carouselLoading}
          viewAllHref="/favorites"
          isFavorite={isFavorite}
          onToggleFavorite={handleToggleFavorite}
          onViewDetails={handleViewDetails}
        />

        <RecommendationCarousel
          title="Explora algo diferente"
          subtitle="Serendipity picks"
          movies={carousel3}
          isLoading={carouselLoading}
          viewAllHref="/search"
          showLiveIndicator
          isFavorite={isFavorite}
          onToggleFavorite={handleToggleFavorite}
          onViewDetails={handleViewDetails}
        />
      </div>

      {/* Movie details dialog (preserved from original) */}
      <MovieDetailsDialog
        movie={selectedMovie}
        open={showDetailsDialog}
        onOpenChange={setShowDetailsDialog}
        onRecommendSimilar={(movie) =>
          router.push(`/search?q=${encodeURIComponent(movie.title)}`)
        }
      />
    </div>
  );
}
