"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/shared/Navbar";
import { ProtectedRoute } from "@/components/shared/ProtectedRoute";
import { Button } from "@/components/ui/button";
import { MovieCard } from "@/components/recommendation/MovieCard";
import { MovieDetailsDialog } from "@/components/home/MovieDetailsDialog";
import { FavoriteMovie, getMyFavorites, removeMyFavorite } from "@/services/favorites.service";
import { Movie } from "@/services/movies.service";
import { ArrowLeft, Heart } from "lucide-react";
import { toast } from "sonner";

export default function FavoritesPage() {
  const router = useRouter();
  const [favorites, setFavorites] = useState<FavoriteMovie[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);

  const loadFavorites = useCallback(async () => {
    try {
      setIsLoading(true);
      const list = await getMyFavorites();
      setFavorites(list);
    } catch (error) {
      console.error("Error cargando favoritos:", error);
      toast.error("No se pudieron cargar los favoritos");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleRemoveFavorite = useCallback(async (movie: Movie) => {
    try {
      const updatedFavorites = await removeMyFavorite(movie.uri);
      setFavorites(updatedFavorites);
      toast.success(`"${movie.title}" se eliminó de favoritos`);
    } catch (error) {
      console.error("Error eliminando favorito:", error);
      toast.error("No se pudo eliminar de favoritos");
    }
  }, []);

  const handleRecommendSimilar = useCallback(
    (movie: Movie) => {
      router.push(`/search?q=${encodeURIComponent(movie.title)}`);
    },
    [router],
  );

  const handleViewDetails = useCallback((movie: Movie) => {
    setSelectedMovie(movie);
    setShowDetailsDialog(true);
  }, []);

  useEffect(() => {
    loadFavorites();
  }, [loadFavorites]);

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-background">
        <Navbar />

        <main className="container mx-auto px-4 py-6">
          <div className="mb-6">
            <Link href="/">
              <Button variant="ghost" size="sm" className="mb-3 -ml-2">
                <ArrowLeft className="h-4 w-4 mr-1" />
                Volver al inicio
              </Button>
            </Link>

            <div className="flex items-center gap-3">
              <Heart className="h-6 w-6 text-accent" />
              <div>
                <h1 className="text-2xl font-bold">Mis Favoritos</h1>
                <p className="text-sm text-muted-foreground">
                  {favorites.length} película(s) guardada(s)
                </p>
              </div>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {isLoading ? (
              <div className="text-center py-8 text-muted-foreground md:col-span-2 xl:col-span-3">
                Cargando favoritos...
              </div>
            ) : favorites.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground md:col-span-2 xl:col-span-3">
                Aún no tienes películas favoritas
              </div>
            ) : (
              favorites.map((movie) => (
                <MovieCard
                  key={movie.uri}
                  movie={movie}
                  onViewDetails={handleViewDetails}
                  onRecommendSimilar={handleRecommendSimilar}
                  isFavorite={true}
                  onToggleFavorite={handleRemoveFavorite}
                />
              ))
            )}
          </div>
        </main>

        <MovieDetailsDialog
          movie={selectedMovie}
          open={showDetailsDialog}
          onOpenChange={setShowDetailsDialog}
          onRecommendSimilar={handleRecommendSimilar}
        />
      </div>
    </ProtectedRoute>
  );
}