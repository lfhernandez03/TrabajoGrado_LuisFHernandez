"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Heart } from "lucide-react";
import { Navbar } from "@/components/organisms/Navbar";
import { MovieGrid } from "@/components/organisms/MovieGrid";
import { type MovieCardMovie } from "@/components/organisms/MovieCard";
import { ProtectedRoute } from "@/components/shared/ProtectedRoute";
import { MovieDetailsDialog } from "@/components/home/MovieDetailsDialog";
import { FavoriteMovie, getMyFavorites, removeMyFavorite } from "@/services/favorites.service";
import { Movie } from "@/services/movies.service";
import { toast } from "sonner";

function toCardMovie(m: FavoriteMovie): MovieCardMovie {
  return {
    uri: m.uri,
    title: m.title,
    posterUrl: m.posterUrl,
    year: m.year,
    runtime: m.runtime,
    genres: m.genres,
    rating: m.rating,
    certification: m.certification,
    description: m.description,
  };
}

export default function FavoritesPage() {
  const router = useRouter();
  const [favorites, setFavorites] = useState<FavoriteMovie[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  const load = useCallback(async () => {
    try {
      setIsLoading(true);
      setFavorites(await getMyFavorites());
    } catch {
      toast.error("No se pudieron cargar los favoritos");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleRemove = useCallback(async (movie: MovieCardMovie) => {
    if (!movie.uri) return;
    try {
      setFavorites(await removeMyFavorite(movie.uri));
      toast.success(`"${movie.title}" eliminado de favoritos`);
    } catch {
      toast.error("No se pudo eliminar el favorito");
    }
  }, []);

  const handleViewDetails = useCallback((movie: MovieCardMovie) => {
    setSelectedMovie(movie as Movie);
    setShowDetails(true);
  }, []);

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-bg">
        <Navbar />

        <main className="max-w-7xl mx-auto px-6 py-10">

          {/* Header */}
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-full bg-accent/10 flex items-center justify-center">
              <Heart className="w-5 h-5 text-accent" />
            </div>
            <div>
              <h1 className="font-display text-4xl text-text">Mis Favoritos</h1>
              {!isLoading && (
                <p className="text-sm text-muted">
                  {favorites.length} película{favorites.length !== 1 ? "s" : ""} guardada{favorites.length !== 1 ? "s" : ""}
                </p>
              )}
            </div>
          </div>

          {/* Grid */}
          <MovieGrid
            movies={favorites.map(toCardMovie)}
            isLoading={isLoading}
            isFavorite={() => true}
            onToggleFavorite={handleRemove}
            onViewDetails={handleViewDetails}
            emptyMessage="Aún no tienes películas favoritas. Explora el catálogo y guarda las que más te gusten."
          />
        </main>

        <MovieDetailsDialog
          movie={selectedMovie}
          open={showDetails}
          onOpenChange={setShowDetails}
          onRecommendSimilar={(m) =>
            router.push(`/search?q=${encodeURIComponent(m.title)}`)
          }
        />
      </div>
    </ProtectedRoute>
  );
}
