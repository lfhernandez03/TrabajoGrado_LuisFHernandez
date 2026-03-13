"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Movie } from "@/services/movies.service";
import { CircleAlert, Sparkles, Star, Heart, Film } from "lucide-react";

interface MovieCardProps {
  movie: Movie;
  onViewDetails?: (movie: Movie) => void;
  onRecommendSimilar?: (movie: Movie) => void;
}

export function MovieCard({
  movie,
  onViewDetails,
  onRecommendSimilar,
}: MovieCardProps) {
  const [imageError, setImageError] = useState(false);
  const normalizedPosterUrl = movie.posterUrl?.startsWith("/")
    ? `https://image.tmdb.org/t/p/w500${movie.posterUrl}`
    : movie.posterUrl;
  const hasPoster = Boolean(normalizedPosterUrl && !imageError);
  const formattedRuntime = movie.runtime
    ? `${Math.floor(movie.runtime / 60)}h ${movie.runtime % 60}m`
    : "—";
  const classification = movie.certification || "NR";

  return (
    <Card className="relative overflow-hidden rounded-xl border-border bg-card hover:border-accent/60 transition-all">
      <CardContent className="relative p-0">
        {hasPoster ? (
          <div className="absolute inset-0 pointer-events-none">
            <img
              src={normalizedPosterUrl}
              alt=""
              aria-hidden="true"
              className="h-full w-full object-cover blur-3xl scale-125 opacity-25"
            />
          </div>
        ) : (
          <div className="absolute inset-0 bg-linear-to-br from-muted/50 via-background to-muted/30 pointer-events-none" />
        )}

        <div className="relative flex gap-4 min-h-52 p-4">
          <div className="w-36 shrink-0 rounded-xl shadow-lg overflow-hidden">
            {hasPoster ? (
              <img
                src={normalizedPosterUrl}
                alt={`Póster de ${movie.title}`}
                className="h-full w-full object-cover"
                loading="lazy"
                onError={() => setImageError(true)}
              />
            ) : (
              <Film className="h-10 w-10 text-muted-foreground/60" />
            )}
          </div>

          <div className="flex-1 min-w-0 flex flex-col justify-between">
            <div>
              <div className="flex items-start justify-between gap-3 mb-3">
                <h3 className="font-semibold text-xl leading-tight line-clamp-2 pr-2">
                  {movie.title}
                </h3>

                <div className="shrink-0 flex items-center gap-2 text-muted-foreground">
                  {onViewDetails && (
                    <button
                      type="button"
                      aria-label={`Ver detalles de ${movie.title}`}
                      className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-background/45 backdrop-blur-md hover:text-foreground hover:bg-background/65 transition-colors"
                      onClick={() => onViewDetails(movie)}
                    >
                      <CircleAlert className="h-4 w-4" />
                    </button>
                  )}
                  {onRecommendSimilar && (
                    <button
                      type="button"
                      aria-label={`Ver similares de ${movie.title}`}
                      className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-background/45 backdrop-blur-md hover:text-accent hover:bg-background/65 transition-colors"
                      onClick={() => onRecommendSimilar(movie)}
                    >
                      <Sparkles className="h-4 w-4" />
                    </button>
                  )}
                  <button
                    type="button"
                    aria-label={`Marcar ${movie.title} como favorito`}
                    className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-background/45 backdrop-blur-md hover:text-accent hover:bg-background/65 transition-colors"
                  >
                    <Heart className="h-4 w-4" />
                  </button>
                </div>
              </div>

              <div className="text-sm text-muted-foreground mb-3">
                <span>{movie.year ?? "—"}</span>
                {movie.runtime ? <span>{` · ${formattedRuntime}`}</span> : null}
              </div>

              <div className="flex items-center gap-2 mb-4 text-sm text-foreground">
                <Star className="h-4 w-4 text-accent" />
                {movie.rating && (
                  <span className="font-medium">
                    {movie.rating.toFixed(1)}
                  </span>
                )}
                <span className="text-muted-foreground">Calificación</span>
                <span className="text-muted-foreground">·</span>
                <span className="text-muted-foreground">{classification}</span>
                {movie.genres && movie.genres.length > 0 && (
                  <>
                    <span className="text-muted-foreground">·</span>
                    <span className="text-muted-foreground">
                      {movie.genres[0]}
                    </span>
                  </>
                )}
              </div>

              <p className="text-base leading-6 text-muted-foreground line-clamp-4">
                {movie.description || "Descripción de la película"}
              </p>
            </div>

            {movie.director && (
              <p className="mt-4 text-xs text-muted-foreground">
                Dirigida por <span className="text-foreground">{movie.director}</span>
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
