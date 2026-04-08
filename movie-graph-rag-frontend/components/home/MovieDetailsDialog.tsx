"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Calendar, Star, User, Sparkles, Clock, ShieldCheck } from "lucide-react";
import { Movie } from "@/services/movies.service";

interface MovieDetailsDialogProps {
  movie: Movie | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRecommendSimilar: (movie: Movie) => void;
}

function formatRuntime(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function RatingBar({ rating }: { rating: number }) {
  const pct = Math.min(Math.max(rating / 10, 0), 1) * 100;
  const color =
    rating >= 7.5 ? "bg-teal" :
    rating >= 6.0 ? "bg-accent2" :
    "bg-muted";

  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-1.5 bg-surface2 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-sm font-bold tabular-nums">{rating.toFixed(1)}</span>
      <span className="text-xs text-muted">/10</span>
    </div>
  );
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
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl md:text-2xl pr-6 leading-tight">
            {movie.title}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-5 mt-2">
          {/* Genres */}
          {movie.genres && movie.genres.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {movie.genres.map((genre, idx) => (
                <Badge key={idx} variant="teal" className="text-xs">
                  {genre}
                </Badge>
              ))}
            </div>
          )}

          {/* Metadata row */}
          <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted">
            {movie.year && (
              <span className="flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5" />
                {movie.year}
              </span>
            )}
            {movie.runtime && (
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" />
                {formatRuntime(movie.runtime)}
              </span>
            )}
            {movie.certification && (
              <span className="flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5" />
                {movie.certification}
              </span>
            )}
            <span className="flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 shrink-0" />
              <span className={movie.director ? "font-medium text-text" : "italic text-muted/50"}>
                {movie.director ?? "Director no disponible"}
              </span>
            </span>
          </div>

          {/* Rating — always shown, placeholder when missing */}
          <div>
            <p className="text-xs font-bold text-muted tracking-widest mb-1.5 flex items-center gap-1.5">
              <Star className="w-3.5 h-3.5" />
              CALIFICACIÓN IMDB
            </p>
            {movie.rating != null ? (
              <RatingBar rating={movie.rating} />
            ) : (
              <p className="text-sm text-muted/50 italic">No disponible</p>
            )}
          </div>

          {/* Description + actions */}
        <div className="space-y-4 border-t border-border pt-4">
          {movie.description && (
            <div>
              <h3 className="text-xs font-bold text-muted tracking-widest mb-2">SINOPSIS</h3>
              <p className="text-sm text-muted leading-relaxed">
                {movie.description}
              </p>
            </div>
          )}

          {movie.relationReason && (
            <div className="rounded-lg border border-teal/20 bg-teal/5 px-4 py-3">
              <h3 className="text-xs font-bold text-teal tracking-widest mb-1.5">
                POR QUÉ SE RECOMIENDA
              </h3>
              <p className="text-sm text-muted italic">{movie.relationReason}</p>
            </div>
          )}

          <div className="flex gap-2">
            <Button
              variant="primary"
              onClick={() => { onOpenChange(false); onRecommendSimilar(movie); }}
              className="flex-1"
            >
              <Sparkles className="mr-2 h-4 w-4" />
              Buscar Similares
            </Button>
            <Button
              variant="ghost"
              onClick={() => onOpenChange(false)}
              className="flex-1"
            >
              Cerrar
            </Button>
          </div>
        </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
