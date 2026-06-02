"use client";

import Image from "next/image";
import { useState } from "react";
import { Movie } from "@/services/movies.service";
import { Sparkles, Star, Heart, Film } from "lucide-react";
import { cn } from "@/lib/utils";

interface MovieCardProps {
  movie: Movie;
  onViewDetails?: (movie: Movie) => void;
  onRecommendSimilar?: (movie: Movie) => void;
  isFavorite?: boolean;
  onToggleFavorite?: (movie: Movie) => void;
}

export function MovieCard({
  movie,
  onViewDetails,
  onRecommendSimilar,
  isFavorite = false,
  onToggleFavorite,
}: MovieCardProps) {
  const [imageError, setImageError] = useState(false);

  const normalizedPosterUrl = movie.posterUrl?.startsWith("/")
    ? `https://image.tmdb.org/t/p/w500${movie.posterUrl}`
    : movie.posterUrl;
  const hasPoster = Boolean(normalizedPosterUrl && !imageError);

  const formattedRuntime = movie.runtime
    ? `${Math.floor(movie.runtime / 60)}h ${movie.runtime % 60}m`
    : null;

  const hasRating = typeof movie.rating === "number";
  const primaryGenre = movie.genres?.[0];
  const descriptionText =
    movie.description ||
    movie.relationReason ||
    "Personalized recommendation based on your recent activity.";

  return (
    <div
      onClick={() => onViewDetails?.(movie)}
      className={cn(
        "group relative overflow-hidden rounded-xl",
        "border border-white/10",
        "transition-all duration-300",
        "hover:scale-[1.015] hover:-translate-y-0.5",
        "hover:border-white/20 hover:shadow-2xl hover:shadow-black/60",
        onViewDetails && "cursor-pointer"
      )}
    >
      {/* Background: dark base + blurred poster on top */}
      <div className="absolute inset-0 bg-surface pointer-events-none" />
      {hasPoster && (
        <div className="absolute inset-0 pointer-events-none">
          <Image
            src={normalizedPosterUrl as string}
            alt=""
            aria-hidden="true"
            fill
            sizes="100vw"
            className="object-cover scale-110 blur-xl opacity-30"
          />
        </div>
      )}

      {/* ── Card content — glass panel ── */}
      <div className="relative flex gap-4 min-h-52 p-4 bg-bg/30 backdrop-blur-[1px]">

        {/* LEFT: Poster thumbnail */}
        <div className="relative w-32 shrink-0 rounded-lg shadow-xl overflow-hidden ring-1 ring-white/10">
          {hasPoster ? (
            <Image
              src={normalizedPosterUrl as string}
              alt={`Poster of ${movie.title}`}
              fill
              sizes="128px"
              className="object-cover"
              onError={() => setImageError(true)}
            />
          ) : (
            <div className="h-full min-h-52 flex items-center justify-center bg-surface2">
              <Film className="h-10 w-10 text-muted/40" />
            </div>
          )}
        </div>

        {/* RIGHT: Info */}
        <div className="flex-1 min-w-0 flex flex-col justify-between">

          {/* Title row + action buttons */}
          <div className="flex items-start justify-between gap-3 mb-2">
            <h3 className="font-semibold text-lg leading-snug line-clamp-2 text-text pr-1">
              {movie.title}
            </h3>

            <div className="shrink-0 flex items-center gap-1.5">
              {onRecommendSimilar && (
                <ActionButton
                  onClick={() => onRecommendSimilar(movie)}
                  aria-label={`View similar movies to ${movie.title}`}
                  colorClass="hover:bg-teal/15 hover:text-teal hover:border-teal/40"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                </ActionButton>
              )}
              <ActionButton
                onClick={() => onToggleFavorite?.(movie)}
                aria-label={
                  isFavorite
                    ? `Remove ${movie.title} from favorites`
                    : `Mark ${movie.title} as favorite`
                }
                colorClass={
                  isFavorite
                    ? "bg-accent2/15 text-accent2 border-accent2/40"
                    : "hover:bg-accent2/15 hover:text-accent2 hover:border-accent2/40"
                }
              >
                <Heart className={cn("h-3.5 w-3.5", isFavorite && "fill-current")} />
              </ActionButton>
            </div>
          </div>

          {/* Year · Runtime */}
          <p className="text-xs text-muted mb-2">
            {movie.year ?? "—"}
            {formattedRuntime && <span> · {formattedRuntime}</span>}
          </p>

          {/* Rating · Certification · Genre */}
          <div className="flex items-center gap-1.5 mb-3 flex-wrap">
            {hasRating && (
              <>
                <Star className="h-3.5 w-3.5 text-accent fill-accent shrink-0" />
                <span className="text-sm font-semibold text-text">
                  {movie.rating!.toFixed(1)}
                </span>
                <span className="text-xs text-muted">Rating</span>
              </>
            )}
            {movie.certification && (
              <>
                <span className="text-muted/50">·</span>
                <span className="text-xs text-muted">{movie.certification}</span>
              </>
            )}
            {primaryGenre && (
              <>
                <span className="text-muted/50">·</span>
                <span className="text-xs text-muted">{primaryGenre}</span>
              </>
            )}
          </div>

          {/* Description */}
          <p className="text-sm leading-relaxed text-muted/85 line-clamp-3">
            {descriptionText}
          </p>

          {/* Director */}
          {movie.director && (
            <p className="mt-3 text-xs text-muted/60">
              Dir. <span className="text-muted">{movie.director}</span>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Small circular icon button ──────────────────────────────────────────────

interface ActionButtonProps {
  onClick: () => void;
  "aria-label": string;
  colorClass: string;
  children: React.ReactNode;
}

function ActionButton({ onClick, "aria-label": ariaLabel, colorClass, children }: ActionButtonProps) {
  return (
    <button
      type="button"
      aria-label={ariaLabel}
      onClick={(e) => { e.stopPropagation(); onClick(); }}
      className={cn(
        "inline-flex h-8 w-8 items-center justify-center rounded-full",
        "bg-bg/50 backdrop-blur-sm border border-white/10",
        "text-muted transition-all duration-200",
        colorClass
      )}
    >
      {children}
    </button>
  );
}
