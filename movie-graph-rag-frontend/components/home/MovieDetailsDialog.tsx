"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Calendar, Star, User, Sparkles } from "lucide-react";
import { Movie } from "@/services/movies.service";

interface MovieDetailsDialogProps {
  movie: Movie | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRecommendSimilar: (movie: Movie) => void;
}

export function MovieDetailsDialog({
  movie,
  open,
  onOpenChange,
  onRecommendSimilar,
}: MovieDetailsDialogProps) {
  if (!movie) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl pr-6">{movie.title}</DialogTitle>
          <DialogDescription>
            Información completa de la película
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 mt-4">
          {movie.genres && movie.genres.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold mb-2">Géneros</h3>
              <div className="flex flex-wrap gap-2">
                {movie.genres.map((genre, idx) => (
                  <Badge key={idx} variant="secondary">
                    {genre}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            {movie.director && (
              <div>
                <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                  <User className="h-4 w-4" />
                  Director
                </h3>
                <p className="text-sm text-muted-foreground">
                  {movie.director}
                </p>
              </div>
            )}

            {movie.year && (
              <div>
                <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  Año
                </h3>
                <p className="text-sm text-muted-foreground">{movie.year}</p>
              </div>
            )}

            {movie.rating && (
              <div>
                <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                  <Star className="h-4 w-4" />
                  Calificación
                </h3>
                <div className="flex items-center gap-2">
                  <div className="flex items-center">
                    {[...Array(5)].map((_, i) => (
                      <Star
                        key={i}
                        className={`h-4 w-4 ${
                          i < Math.floor(movie.rating!)
                            ? "fill-yellow-400 text-yellow-400"
                            : "text-gray-300"
                        }`}
                      />
                    ))}
                  </div>
                  <span className="text-sm font-semibold">
                    {movie.rating.toFixed(1)}
                  </span>
                </div>
              </div>
            )}

            {movie.uri && (
              <div>
                <h3 className="text-sm font-semibold mb-2">URI</h3>
                <p className="text-xs text-muted-foreground font-mono break-all">
                  {movie.uri}
                </p>
              </div>
            )}
          </div>

          {movie.description && (
            <div>
              <h3 className="text-sm font-semibold mb-2">Sinopsis</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {movie.description}
              </p>
            </div>
          )}

          {movie.relationReason && (
            <div className="bg-primary/10 rounded-lg p-4">
              <h3 className="text-sm font-semibold mb-2">
                Razón de Recomendación
              </h3>
              <p className="text-sm text-primary italic">
                {movie.relationReason}
              </p>
            </div>
          )}

          <div className="flex gap-2 pt-4 border-t">
            <Button
              onClick={() => {
                onOpenChange(false);
                onRecommendSimilar(movie);
              }}
              className="flex-1"
            >
              <Sparkles className="mr-2 h-4 w-4" />
              Buscar Similares
            </Button>
            <Button
              variant="outline"
              onClick={() => onOpenChange(false)}
              className="flex-1"
            >
              Cerrar
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
