"use client";

import { useState, useEffect, useCallback } from "react";
import { Navbar } from "@/components/organisms/Navbar";
import { HeroSection, type HeroMovie } from "@/components/organisms/HeroSection";
import { RecommendationHeader } from "@/components/organisms/RecommendationHeader";
import { RecommendationCarousel } from "@/components/organisms/RecommendationCarousel";
import { type MovieCardMovie } from "@/components/organisms/MovieCard";
import { MovieDetailsDialog } from "@/components/home/MovieDetailsDialog";
import { ProtectedRoute } from "@/components/shared/ProtectedRoute";
import { Movie, searchMovies, getMovieExamples, getMoviesByCentrality, getMovieNeighborhood, getTopologicalProfile, getClusterMovies, type RecommendedMovie } from "@/services/movies.service";
import { getActivityRecommendation } from "@/services/chat.service";
import {
  addMyFavorite,
  FavoriteMovie,
  getMyFavorites,
  removeMyFavorite,
} from "@/services/favorites.service";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { usePendingSet } from "@/hooks/usePendingSet";

// ── Cold start genre rotation ─────────────────────────────────────────────────
// Genres must match the ontology literals used in the backend
const _COLD_START_GENRES = [
  "Drama", "Comedy", "Action", "Thriller", "Animation",
  "Romance", "Sci-Fi", "Horror", "Adventure",
] as const;

// English display names for each ontology genre
const _GENRE_DISPLAY: Record<string, string> = {
  Drama: "Drama",
  Comedy: "Comedy",
  Action: "Action",
  Thriller: "Thriller",
  Animation: "Animation",
  Romance: "Romance",
  "Sci-Fi": "Sci-Fi",
  Horror: "Horror",
  Adventure: "Adventure",
};

/**
 * Returns 3 distinct genres for today's cold start carousels.
 * Rotates daily so the user sees different content each day.
 */
function getThreeDailyGenres(): [string, string, string] {
  const day = new Date().getDay(); // 0–6
  const n = _COLD_START_GENRES.length;
  return [
    _COLD_START_GENRES[day % n],
    _COLD_START_GENRES[(day + 3) % n],
    _COLD_START_GENRES[(day + 6) % n],
  ];
}

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
    certification: (movie as Movie).certification,
    description: (movie as Movie).description,
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
    description: movie.description ?? undefined,
  };
}

export default function Home() {
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const withPending = usePendingSet();

  // ── Hero ──────────────────────────────────────────────────────────────────
  const [heroMovie, setHeroMovie] = useState<HeroMovie | null>(null);
  const [heroLoading, setHeroLoading] = useState(true);
  const [heroFavorite, setHeroFavorite] = useState(false);
  const [heroColdStart, setHeroColdStart] = useState(false);

  // ── Carousels ─────────────────────────────────────────────────────────────
  const [carousel1, setCarousel1] = useState<MovieCardMovie[]>([]);
  const [carousel2, setCarousel2] = useState<MovieCardMovie[]>([]);
  const [carousel3, setCarousel3] = useState<MovieCardMovie[]>([]);
  const [carouselLoading, setCarouselLoading] = useState(true);
  const [carousel1Title, setCarousel1Title] = useState<string>("Because you watched");
  const [carousel1FavoriteTitle, setCarousel1FavoriteTitle] = useState<string>("…");
  const [carousel2Title, setCarousel2Title] = useState<string>("Based on your favorites");
  const [carousel2FavoriteTitle, setCarousel2FavoriteTitle] = useState<string>("");
  const [carousel3Subtitle, setCarousel3Subtitle] = useState<string>("Discover new genres based on what you haven't explored");

  // ── Favorites ─────────────────────────────────────────────────────────────
  const [favorites, setFavorites] = useState<FavoriteMovie[]>([]);

  // ── Movie details dialog ──────────────────────────────────────────────────
  const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);

  // ── Data loading ──────────────────────────────────────────────────────────

  const loadFavorites = useCallback(async () => {
    try {
      const fav = await getMyFavorites();
      setFavorites(fav);
      return fav;
    } catch {
      // silently fail — user may not be authenticated
      return [];
    }
  }, []);

  const loadHero = useCallback(async (): Promise<string | undefined> => {
    setHeroLoading(true);
    try {
      const rec = await getActivityRecommendation();
      setHeroColdStart(rec.isColdStart ?? false);
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
              uri: canonical.uri,
              title: canonical.title,
              posterUrl: canonical.posterUrl ?? best.posterUrl,
              genreName: best.genreName ?? canonical.genres?.[0],
              genres: canonical.genres,
              director: canonical.director,
              runtime: canonical.runtime ?? best.runtime,
              compatibilityScore: best.compatibilityScore,
              description: canonical.description ?? best.description,
              explanation: rec.explanation,
              contextExtracted: rec.contextExtracted ? {
                moodDescription: rec.contextExtracted.emotionalContext?.moodDescription,
                desiredEnergyLevel: rec.contextExtracted.emotionalContext?.desiredEnergyLevel,
                availableTime: rec.contextExtracted.requirementContext?.availableTime,
              } : undefined,
            });
            return canonical.title;
          }
        } catch { /* ignore enrichment errors */ }

        setHeroMovie({
          uri: best.uri,
          title: best.title,
          posterUrl: best.posterUrl,
          genreName: best.genreName,
          runtime: best.runtime,
          compatibilityScore: best.compatibilityScore,
          description: best.description,
          explanation: rec.explanation,
          contextExtracted: rec.contextExtracted ? {
            moodDescription: rec.contextExtracted.emotionalContext?.moodDescription,
            desiredEnergyLevel: rec.contextExtracted.emotionalContext?.desiredEnergyLevel,
            availableTime: rec.contextExtracted.requirementContext?.availableTime,
          } : undefined,
        });
        return best.title;
      } else {
        // Fallback to an example movie
        const examples = await getMovieExamples(1);
        if (examples[0]) {
          setHeroMovie({ 
            uri: examples[0].uri,
            title: examples[0].title, 
            posterUrl: examples[0].posterUrl,
            description: examples[0].description,
          });
          return examples[0].title;
        }
      }
    } catch {
      const examples = await getMovieExamples(1).catch(() => []);
      if (examples[0]) {
        setHeroMovie({ 
          uri: examples[0].uri,
          title: examples[0].title, 
          posterUrl: examples[0].posterUrl,
          description: examples[0].description,
        });
        return examples[0].title;
      }
    } finally {
      setHeroLoading(false);
    }
  }, []);

  const loadCarousels = useCallback(async (userFavorites: FavoriteMovie[]) => {
    setCarouselLoading(true);
    try {
      // ── Cold start: genre-rotation carousels (no favorites yet) ────────────
      if (userFavorites.length === 0) {
        const [g1, g2, g3] = getThreeDailyGenres();
        const d1 = _GENRE_DISPLAY[g1] ?? g1;
        const d2 = _GENRE_DISPLAY[g2] ?? g2;
        const d3 = _GENRE_DISPLAY[g3] ?? g3;

        setCarousel1Title("Best of");
        setCarousel1FavoriteTitle(d1);
        setCarousel2Title("Discover");
        setCarousel2FavoriteTitle(d2);
        setCarousel3Subtitle(`Start exploring the best of ${d3}`);

        const [c1, c2, c3] = await Promise.allSettled([
          getMoviesByCentrality(g1, 12).then((r) => r.movies.map(recToCardMovie)),
          getMoviesByCentrality(g2, 12).then((r) => r.movies.map(recToCardMovie)),
          getMoviesByCentrality(g3, 12).then((r) => r.movies.map(recToCardMovie)),
        ]);

        const fallback = () => getMovieExamples(12).then((arr) => arr.map(toCardMovie));
        setCarousel1(c1.status === "fulfilled" ? c1.value : await fallback());
        setCarousel2(c2.status === "fulfilled" ? c2.value : await fallback());
        setCarousel3(c3.status === "fulfilled" ? c3.value : await fallback());
        return;
      }

      // ── Normal path: favorites-based carousels ────────────────────────────
      // Select random favorites for each carousel
      const getRandomFavorite = () => userFavorites.length > 0
        ? userFavorites[Math.floor(Math.random() * userFavorites.length)]
        : null;
      
      const randomFavorite1 = getRandomFavorite();
      const randomFavorite2 = getRandomFavorite();
      
      // Update carousel 1 heading based on cold start status
      if (randomFavorite1) {
        setCarousel1Title("Because you watched");
        setCarousel1FavoriteTitle(randomFavorite1.title);
      } else {
        setCarousel1Title("Movies for you");
        setCarousel1FavoriteTitle("To get you started");
      }
      
      // Update carousel 2 heading based on favorites availability
      if (randomFavorite2) {
        setCarousel2Title("Like");
        setCarousel2FavoriteTitle(randomFavorite2.title);
      } else {
        setCarousel2Title("Based on your favorites");
        setCarousel2FavoriteTitle("");
      }
      
      // Load topological profile to find unexplored clusters
      const getUnexploredClusterId = async () => {
        try {
          const profile = await getTopologicalProfile();
          if (profile?.unexploredAdjacent && profile.unexploredAdjacent.length > 0) {
            // Pick a random unexplored cluster for discovery
            const randomCluster = profile.unexploredAdjacent[Math.floor(Math.random() * profile.unexploredAdjacent.length)];
            return randomCluster.clusterId;
          }
        } catch (err) {
          console.error("Failed to load topological profile:", err);
          // If topological profile fails, fallback to null and use serendipity score
        }
        return null;
      };
      
      const [neighborhood, centrality, serendipity] = await Promise.allSettled([
        // "Porque viste X" — neighborhood of a random favorite (backend excludes center node)
        randomFavorite1
          ? getMovieNeighborhood(randomFavorite1.title, 1).then((r) => r.nodes.map((n) => ({
              uri: n.uri, title: n.title, posterUrl: n.posterUrl ?? undefined,
              year: n.year ?? undefined,
              genres: n.genre ? [n.genre] : undefined, rating: n.rating ?? undefined,
              runtime: n.runtime ?? undefined,
              description: n.description ?? undefined,
              director: n.director ?? undefined,
            } as MovieCardMovie)))
          : getMovieExamples(12).then((arr) => arr.map(toCardMovie)),
        // "Como Y" — neighborhood of another random favorite (backend excludes center node)
        randomFavorite2
          ? getMovieNeighborhood(randomFavorite2.title, 1).then((r) => r.nodes.map((n) => ({
              uri: n.uri, title: n.title, posterUrl: n.posterUrl ?? undefined,
              year: n.year ?? undefined,
              genres: n.genre ? [n.genre] : undefined, rating: n.rating ?? undefined,
              runtime: n.runtime ?? undefined,
              description: n.description ?? undefined,
              director: n.director ?? undefined,
            } as MovieCardMovie)))
          : getMoviesByCentrality(undefined, 12).then((r) => r.movies.map(recToCardMovie)),
        // "Explore new genres" — from least-explored cluster or fallback to serendipity
        (async () => {
          const clusterId = await getUnexploredClusterId();
          if (clusterId) {
            return getClusterMovies(clusterId, 12).then(r => r.movies.map((m) => ({
              uri: "", // ClusterMovie doesn't have uri yet, might need to enhance backend
              title: m.title ?? "",
              posterUrl: m.posterUrl ?? undefined,
              genres: m.genres && m.genres.length > 0 ? m.genres : undefined,
              rating: m.rating ?? undefined,
              runtime: m.runtime ?? undefined,
              description: m.description ?? undefined,
              director: m.director ?? undefined,
            } as MovieCardMovie)));
          }
          // Fallback: use serendipity score from centrality
          return getMoviesByCentrality(undefined, 20).then((r) =>
            [...r.movies]
              .sort((a, b) => (b.serendipityScore ?? 0) - (a.serendipityScore ?? 0))
              .slice(0, 12)
              .map(recToCardMovie)
          );
        })(),
      ]);

      const fallback = () => getMovieExamples(12).then((arr) => arr.map(toCardMovie));

      setCarousel1(neighborhood.status === 'fulfilled' ? neighborhood.value : await fallback());
      setCarousel2(centrality.status === 'fulfilled' ? centrality.value : await fallback());
      setCarousel3(serendipity.status === 'fulfilled' ? serendipity.value : await fallback());
    } catch {
      toast.error("Could not load recommendations");
    } finally {
      setCarouselLoading(false);
    }
  }, []);

  // Initial load: only fetch data once we know the user is authenticated.
  // This prevents firing API calls when ProtectedRoute is about to redirect to login.
  useEffect(() => {
    if (!isAuthenticated) return;
    const initialize = async () => {
      // Hero and favorites are independent — start both in parallel.
      // Carousels need favorites but NOT hero, so they start as soon as
      // favorites resolve without waiting for the hero call to finish.
      const heroPromise = loadHero();
      const userFavorites = await loadFavorites();
      await Promise.all([heroPromise, loadCarousels(userFavorites)]);
    };
    initialize();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  // ── Favorites helpers ─────────────────────────────────────────────────────

  const isFavorite = useCallback(
    (uri: string) => favorites.some((f) => f.uri === uri),
    [favorites]
  );

  const handleToggleFavorite = useCallback(
    (movie: MovieCardMovie) => {
      if (!movie.uri) return;
      withPending(movie.uri, async () => {
        const was = isFavorite(movie.uri!);
        const updated = was
          ? await removeMyFavorite(movie.uri!)
          : await addMyFavorite(movie as Movie);
        setFavorites(updated);
        toast.success(was ? `"${movie.title}" eliminado de favoritos` : `"${movie.title}" agregado a favoritos`);
        if (heroMovie && movie.title === heroMovie.title) setHeroFavorite(!was);
      }).catch(() => toast.error("Could not update favorites"));
    },
    [withPending, isFavorite, heroMovie]
  );

  const handleViewDetails = useCallback((movie: MovieCardMovie) => {
    setSelectedMovie(movie as Movie);
    setShowDetailsDialog(true);
  }, []);

  const handleFindSimilar = useCallback((movie: MovieCardMovie) => {
    router.push(`/search?q=${encodeURIComponent(movie.title)}`);
  }, [router]);

  const handleHeroDetails = useCallback(() => {
    if (!heroMovie) return;
    withPending('hero-details', async () => {
      const results = await searchMovies({ q: heroMovie.title, limit: 5 });
      const fullMovie = results.find(
        (m) => m.title.trim().toLowerCase() === heroMovie.title.trim().toLowerCase()
      ) ?? results[0];
      if (fullMovie) {
        setSelectedMovie(fullMovie);
        setShowDetailsDialog(true);
      }
    }).catch(() => toast.error("Could not load movie details"));
  }, [withPending, heroMovie]);

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <ProtectedRoute>
    <div className="min-h-screen bg-bg">
      <Navbar />

      {/* Hero */}
      <HeroSection
        featuredMovie={heroMovie}
        isLoading={heroLoading}
        isFavorite={heroFavorite}
        isColdStart={heroColdStart}
        onToggleFavorite={() => heroMovie && handleToggleFavorite(heroMovie as MovieCardMovie)}
        onViewDetails={handleHeroDetails}
      />

      {/* Recommendation Header */}
      <RecommendationHeader movieTitle={heroMovie?.title} genres={heroMovie?.genres} />

      {/* Carousels */}
      <div className="max-w-7xl mx-auto px-6 pb-20 flex flex-col gap-12">
        <RecommendationCarousel
          title={carousel1Title}
          subtitle={carousel1FavoriteTitle}
          movies={carousel1}
          isLoading={carouselLoading}
          viewAllHref="/search"
          showLiveIndicator
          isFavorite={isFavorite}
          onToggleFavorite={handleToggleFavorite}
          onViewDetails={handleViewDetails}
          onFindSimilar={handleFindSimilar}
        />

        <RecommendationCarousel
          title={carousel2Title}
          subtitle={carousel2FavoriteTitle}
          movies={carousel2}
          isLoading={carouselLoading}
          viewAllHref="/favorites"
          isFavorite={isFavorite}
          onToggleFavorite={handleToggleFavorite}
          onViewDetails={handleViewDetails}
          onFindSimilar={handleFindSimilar}
        />

        <RecommendationCarousel
          title="Explore new genres"
          subtitle={carousel3Subtitle}
          movies={carousel3}
          isLoading={carouselLoading}
          viewAllHref="/search"
          showLiveIndicator
          isFavorite={isFavorite}
          onToggleFavorite={handleToggleFavorite}
          onViewDetails={handleViewDetails}
          onFindSimilar={handleFindSimilar}
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
    </ProtectedRoute>
  );
}
