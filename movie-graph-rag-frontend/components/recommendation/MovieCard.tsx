"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Movie } from "@/services/movies.service";
import { Calendar, Star, User, GitBranch } from "lucide-react";

interface MovieCardProps {
  movie: Movie;
  onViewDetails?: (movie: Movie) => void;
  onRecommendSimilar?: (movie: Movie) => void;
}

export function MovieCard({ movie, onViewDetails, onRecommendSimilar }: MovieCardProps) {
  return (
    <Card className="hover:shadow-lg transition-shadow h-full flex flex-col">
      <CardHeader>
        <div className="flex justify-between items-start gap-2">
          <CardTitle className="line-clamp-2">{movie.title}</CardTitle>
          {movie.genres && movie.genres.length > 0 && (
            <Badge className="shrink-0">{movie.genres[0]}</Badge>
          )}
        </div>
        {/* Breadcrumb Semántico */}
        {movie.relationReason && (
          <div className="flex items-center gap-1 text-xs text-primary bg-primary/10 rounded-md px-2 py-1 mt-2">
            <GitBranch className="h-3 w-3" />
            <span className="italic">{movie.relationReason}</span>
          </div>
        )}
        <CardDescription className="flex flex-col gap-1">
          {movie.director && (
            <span className="flex items-center gap-1 text-sm">
              <User className="h-3 w-3" />
              {movie.director}
            </span>
          )}
          {movie.year && (
            <span className="flex items-center gap-1 text-sm">
              <Calendar className="h-3 w-3" />
              {movie.year}
            </span>
          )}
          {movie.rating && (
            <span className="flex items-center gap-1 text-sm">
              <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
              {movie.rating.toFixed(1)}
            </span>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col justify-between">
        <p className="text-sm text-muted-foreground line-clamp-3 mb-4">
          {movie.description || "Sin descripción disponible"}
        </p>
        {movie.genres && movie.genres.length > 1 && (
          <div className="flex flex-wrap gap-1 mb-4">
            {movie.genres.slice(1).map((genre, idx) => (
              <Badge key={idx} variant="secondary" className="text-xs">
                {genre}
              </Badge>
            ))}
          </div>
        )}
        <div className="flex gap-2">
          {onViewDetails && (
            <Button 
              variant="outline" 
              size="sm" 
              className="flex-1"
              onClick={() => onViewDetails(movie)}
            >
              Ver detalles
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
