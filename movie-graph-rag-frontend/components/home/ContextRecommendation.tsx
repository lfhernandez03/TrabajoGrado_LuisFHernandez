"use client";

import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { MovieCard } from "@/components/recommendation/MovieCard";
import { Movie } from "@/services/movies.service";

interface ContextRecommendationProps {
  userName?: string;
  contextMovie: Movie | null;
  isLoading: boolean;
  onViewDetails: (movie: Movie) => void;
  onRecommendSimilar: (movie: Movie) => void;
  isFavorite: (movieUri: string) => boolean;
  onToggleFavorite: (movie: Movie) => void;
}

export function ContextRecommendation({
  userName,
  contextMovie,
  isLoading,
  onViewDetails,
  onRecommendSimilar,
  isFavorite,
  onToggleFavorite,
}: ContextRecommendationProps) {
  return (
    <section className="mb-10">
      <div className="mb-4">
        <h2 className="text-2xl font-semibold">
          ¡Hola, {userName?.split(" ")[0] || "Cinéfilo"}!
        </h2>
        <p className="text-muted-foreground text-sm mt-1">
          Basado en tu actividad, te recomendamos
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-[1fr_auto] items-center">
        <div>
          {isLoading ? (
            <Card className="bg-card border-border p-5 space-y-3">
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
              <div className="flex gap-2 pt-2">
                <Skeleton className="h-9 flex-1" />
                <Skeleton className="h-9 flex-1" />
              </div>
            </Card>
          ) : contextMovie ? (
            <MovieCard
              movie={contextMovie}
              onViewDetails={onViewDetails}
              onRecommendSimilar={onRecommendSimilar}
              isFavorite={isFavorite(contextMovie.uri)}
              onToggleFavorite={onToggleFavorite}
            />
          ) : null}
        </div>

        <div className="hidden md:flex flex-col gap-2 w-72 text-sm text-muted-foreground leading-relaxed">
          <p>
            Nuestro sistema de grafos de conocimiento seleccionó esta película
            con alta compatibilidad semántica con tu perfil de preferencias.
          </p>
        </div>
      </div>
    </section>
  );
}
