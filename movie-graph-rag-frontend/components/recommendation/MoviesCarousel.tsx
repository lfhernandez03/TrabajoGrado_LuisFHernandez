"use client";

import { useEffect, useState } from "react";
import { Movie, getMovieExamples } from "@/services/movies.service";
import { MovieCard } from "./MovieCard";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

interface MoviesCarouselProps {
  itemsPerPage?: number;
  onViewDetails?: (movie: Movie) => void;
  onRecommendSimilar?: (movie: Movie) => void;
  isFavorite?: (movieUri: string) => boolean;
  onToggleFavorite?: (movie: Movie) => void;
}

export function MoviesCarousel({ 
  itemsPerPage = 3,
  onViewDetails,
  onRecommendSimilar,
  isFavorite,
  onToggleFavorite,
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
      const data = await getMovieExamples(9);
      const filtered = data.filter(
        (movie) => movie.title.trim().toLowerCase() !== "demo movie"
      );
      setMovies(filtered.length > 0 ? filtered : data);
    } catch (error) {
      console.error("Error loading movies:", error);
      toast.error("Error loading example movies");
    } finally {
      setLoading(false);
    }
  };

  const totalPages = Math.ceil(movies.length / itemsPerPage);
  const startIdx = currentPage * itemsPerPage;
  const endIdx = startIdx + itemsPerPage;
  const currentMovies = movies.slice(startIdx, endIdx);

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
        No movies available at this time
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Movies */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 mb-6">
        {currentMovies.map((movie) => (
          <MovieCard
            key={movie.uri}
            movie={movie}
            onViewDetails={onViewDetails}
            onRecommendSimilar={onRecommendSimilar}
            isFavorite={isFavorite?.(movie.uri)}
            onToggleFavorite={onToggleFavorite}
          />
        ))}
      </div>

      {/* Carousel dot indicators */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          {Array.from({ length: totalPages }).map((_, idx) => (
            <button
              key={idx}
              onClick={() => setCurrentPage(idx)}
              className={`h-2.5 rounded-full transition-all ${
                idx === currentPage
                  ? "w-2.5 bg-primary"
                  : "w-2.5 bg-muted-foreground/30 hover:bg-muted-foreground/50"
              }`}
              aria-label={`Go to page ${idx + 1}`}
            />
          ))}
        </div>
      )}
    </div>
  );
}
