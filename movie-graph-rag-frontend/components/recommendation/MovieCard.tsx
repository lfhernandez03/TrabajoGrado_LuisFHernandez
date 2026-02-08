"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Movie } from "@/services/movies.service";
import { Star, Heart } from "lucide-react";

interface MovieCardProps {
  movie: Movie;
  onViewDetails?: (movie: Movie) => void;
  onRecommendSimilar?: (movie: Movie) => void;
}

export function MovieCard({ movie, onViewDetails, onRecommendSimilar }: MovieCardProps) {
  return (
    <Card className="bg-card border-border hover:border-accent/60 transition-all h-full flex flex-col overflow-hidden">
      <CardContent className="flex-1 flex flex-col p-5">
        {/* Header: Title + Favorite */}
        <div className="flex justify-between items-start gap-2 mb-3">
          <h3 className="font-semibold text-base leading-tight line-clamp-2">
            {movie.title}
          </h3>
          <button className="shrink-0 text-muted-foreground hover:text-accent transition-colors">
            <Heart className="h-4 w-4" />
          </button>
        </div>

        {/* Rating + Genre inline */}
        <div className="flex items-center gap-2 mb-3">
          {movie.rating && (
            <span className="flex items-center gap-1 text-sm">
              <Star className="h-3.5 w-3.5 fill-accent text-accent" />
              <span className="font-medium text-accent">{movie.rating.toFixed(1)}</span>
            </span>
          )}
          {movie.genres && movie.genres.length > 0 && (
            <Badge variant="secondary" className="text-xs font-medium bg-accent/15 text-accent border-accent/30">
              {movie.genres[0]}
            </Badge>
          )}
        </div>

        {/* Description */}
        <p className="text-sm text-muted-foreground line-clamp-2 mb-4 flex-1">
          {movie.description || "Descripcion de la película"}
        </p>

        {/* Action buttons */}
        <div className="flex gap-2">
          {onViewDetails && (
            <Button
              size="sm"
              className="flex-1"
              onClick={() => onViewDetails(movie)}
            >
              Ver Detalles
            </Button>
          )}
          {onRecommendSimilar && (
            <Button
              size="sm"
              className="flex-1"
              onClick={() => onRecommendSimilar(movie)}
            >
              Similares
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
