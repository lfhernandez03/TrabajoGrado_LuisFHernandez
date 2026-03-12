"use client";

import { MoviesCarousel } from "@/components/recommendation/MoviesCarousel";
import { Movie } from "@/services/movies.service";

interface FeaturedMoviesSectionProps {
  onViewDetails: (movie: Movie) => void;
  onRecommendSimilar: (movie: Movie) => void;
}

export function FeaturedMoviesSection({
  onViewDetails,
  onRecommendSimilar,
}: FeaturedMoviesSectionProps) {
  return (
    <section className="mb-10">
      <div className="mb-6">
        <h2 className="text-2xl font-semibold">Películas Destacadas</h2>
        <p className="text-muted-foreground text-sm mt-1">
          Explora nuestro catálogo de películas
        </p>
      </div>

      <MoviesCarousel
        itemsPerPage={3}
        onViewDetails={onViewDetails}
        onRecommendSimilar={onRecommendSimilar}
      />
    </section>
  );
}
