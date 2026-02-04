"use client";

import { useEffect, useState } from "react";
import { Movie, getMovieExamples } from "@/services/movies.service";
import { MovieCard } from "./MovieCard";
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { toast } from "sonner";

interface MoviesCarouselProps {
  itemsPerPage?: number;
  onViewDetails?: (movie: Movie) => void;
  onRecommendSimilar?: (movie: Movie) => void;
}

export function MoviesCarousel({ 
  itemsPerPage = 3,
  onViewDetails,
  onRecommendSimilar 
}: MoviesCarouselProps) {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [currentPage, setCurrentPage] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMovies();
  }, []);

  const loadMovies = async () => {
    try {
      setLoading(true);
      const data = await getMovieExamples(9); // Cargar 9 películas para 3 páginas
      setMovies(data);
    } catch (error) {
      console.error("Error cargando películas:", error);
      toast.error("Error al cargar las películas de ejemplo");
    } finally {
      setLoading(false);
    }
  };

  const totalPages = Math.ceil(movies.length / itemsPerPage);
  const startIdx = currentPage * itemsPerPage;
  const endIdx = startIdx + itemsPerPage;
  const currentMovies = movies.slice(startIdx, endIdx);

  const goToNext = () => {
    setCurrentPage((prev) => (prev + 1) % totalPages);
  };

  const goToPrevious = () => {
    setCurrentPage((prev) => (prev - 1 + totalPages) % totalPages);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (movies.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No hay películas disponibles en este momento
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Películas */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 mb-6">
        {currentMovies.map((movie) => (
          <MovieCard
            key={movie.uri}
            movie={movie}
            onViewDetails={onViewDetails}
            onRecommendSimilar={onRecommendSimilar}
          />
        ))}
      </div>

      {/* Controles del carrusel */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4">
          <Button
            variant="outline"
            size="icon"
            onClick={goToPrevious}
            aria-label="Página anterior"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          
          <div className="flex gap-2">
            {Array.from({ length: totalPages }).map((_, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentPage(idx)}
                className={`h-2 rounded-full transition-all ${
                  idx === currentPage
                    ? "w-8 bg-primary"
                    : "w-2 bg-muted-foreground/30 hover:bg-muted-foreground/50"
                }`}
                aria-label={`Ir a página ${idx + 1}`}
              />
            ))}
          </div>

          <Button
            variant="outline"
            size="icon"
            onClick={goToNext}
            aria-label="Página siguiente"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
