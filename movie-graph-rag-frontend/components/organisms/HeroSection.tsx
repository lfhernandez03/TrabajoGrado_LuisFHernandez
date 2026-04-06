"use client";

import { useState } from "react";
import Image from "next/image";
import { Film, Heart, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScoreBar } from "@/components/atoms/ScoreBar";
import { SkeletonPoster, SkeletonBox } from "@/components/atoms/Loader";
import { cn } from "@/lib/utils";


// Generate dynamic metrics from context
function generateMetrics(movie: HeroMovie | null | undefined) {
  const metrics = [];

  // Compatibilidad: from compatibilityScore
  if (movie?.compatibilityScore !== undefined) {
    metrics.push({
      label: "Compatibilidad",
      value: Math.min(Math.max(movie.compatibilityScore, 0), 1),
    });
  } else {
    metrics.push({ label: "Compatibilidad", value: 0.85 });
  }

  // Estado de ánimo: from contextExtracted.moodDescription
  if (movie?.contextExtracted?.moodDescription) {
    // Presence of mood description = high confidence
    metrics.push({ label: "Estado de ánimo", value: 0.85 });
  } else {
    metrics.push({ label: "Estado de ánimo", value: 0.60 });
  }

  // Momento del día: from contextExtracted.availableTime
  if (movie?.contextExtracted?.availableTime) {
    // Presence of time context = high confidence
    metrics.push({ label: "Momento del día", value: 0.88 });
  } else {
    metrics.push({ label: "Momento del día", value: 0.70 });
  }

  return metrics;
}

export interface HeroMovie {
  uri?: string;
  title: string;
  posterUrl?: string | null;
  genreName?: string | null;
  genres?: string[];
  director?: string | null;
  runtime?: number | null;
  compatibilityScore?: number;
  explanation?: string;
  description?: string;
  contextExtracted?: {
    moodDescription?: string;
    desiredEnergyLevel?: string;
    availableTime?: number;
  };
}

export interface HeroSectionProps {
  featuredMovie?: HeroMovie | null;
  isLoading?: boolean;
  isFavorite?: boolean;
  onToggleFavorite?: () => void;
  onViewDetails?: () => void;
  className?: string;
}

export function HeroSection({
  featuredMovie,
  isLoading = false,
  isFavorite = false,
  onToggleFavorite,
  onViewDetails,
  className,
}: HeroSectionProps) {
  const genre = featuredMovie?.genres?.[0] ?? featuredMovie?.genreName;
  const runtime = featuredMovie?.runtime
    ? `${Math.floor(featuredMovie.runtime / 60)}h ${featuredMovie.runtime % 60}m`
    : null;

  const posterUrl = featuredMovie?.posterUrl?.startsWith("/")
    ? `https://image.tmdb.org/t/p/w500${featuredMovie.posterUrl}`
    : featuredMovie?.posterUrl;

  return (
    <section className={cn("py-12 md:py-16", className)}>
      <div className="px-6 md:px-12 lg:px-20">
        <div className="max-w-7xl mx-auto">
          {/* Hero: Tu película de esta noche */}
          <div className="space-y-8 w-full">
            {/* Header: Badge + Title */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 w-fit px-3 py-1.5 rounded-full border border-teal/40 bg-teal/5">
                <span className="w-1.5 h-1.5 rounded-full bg-teal animate-pulse" />
                <span className="text-xs font-semibold text-teal tracking-wide">
                  RECOMENDACIÓN DEL MOMENTO
                </span>
              </div>

              <h1 className="font-display tracking-tight text-6xl md:text-7xl lg:text-8xl font-extrabold leading-tight">
                <span className="block text-text">TU PELÍCULA</span>
                <span className="block bg-linear-to-r from-accent2 via-accent2/80 to-accent2/60 bg-clip-text text-transparent">
                  DE ESTA NOCHE
                </span>
              </h1>

              <p className="text-sm md:text-base text-muted max-w-2xl leading-relaxed">
                El grafo conoce tu historial — <span className="font-bold" style={{ color: 'var(--color-purple)' }}>{featuredMovie?.genres?.slice(0, 3).join(", ") || "películas de calidad"}</span>. Eligió esto para ti ahora mismo.
              </p>
            </div>

            {/* Main Content: Horizontal Card + Explanation Sidebar */}
            <div className="flex flex-col lg:flex-row gap-8 items-start">
              {/* LEFT: Horizontal Movie Card */}
              <div className="flex-1 min-w-0">
                {isLoading ? (
                  <HorizontalCardSkeleton />
                ) : featuredMovie ? (
                  <HorizontalMovieCard
                    movie={featuredMovie}
                    posterUrl={posterUrl ?? null}
                    genre={genre ?? null}
                    runtime={runtime}
                    isFavorite={isFavorite}
                    onToggleFavorite={onToggleFavorite}
                    onViewDetails={onViewDetails}
                  />
                ) : null}
              </div>

              {/* RIGHT: Explanation Sidebar */}
              <div className="shrink-0 w-full lg:w-64 flex flex-col gap-4 pt-0 lg:pt-4">
                <div className="space-y-2">
                  <h3 className="text-xs font-bold text-teal tracking-widest">
                    POR QUÉ EL GRAFO
                  </h3>
                  <h3 className="text-xs font-bold text-teal tracking-widest">
                    ELIGIÓ ESTO
                  </h3>
                </div>
                <p className="text-xs text-muted leading-relaxed">
                  {featuredMovie?.explanation ||
                    "Basado en tu historial de neo-noir psicológico (Memento, Prestige) y preferencia por worldbuilding ciencia ficción (Blade Runner 1982, Alien). El contexto temporal sugiere una experiencia larga e inmersiva."}
                </p>
              </div>
            </div>

            {/* Recommendation Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4 border-t border-border">
              {generateMetrics(featuredMovie).map((metric) => (
                <div key={metric.label} className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-semibold text-muted">
                      {metric.label}
                    </span>
                    <span className="text-xs font-mono text-muted">
                      {(metric.value * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="h-1 bg-surface2 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-linear-to-r from-teal to-teal/70 rounded-full"
                      style={{ width: `${metric.value * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// ── Horizontal Movie Card ────────────────────────────────────────────────────────────
// New layout: Poster on left, content on right

interface HorizontalMovieCardProps {
  movie: HeroMovie;
  posterUrl: string | null;
  genre: string | null;
  runtime: string | null;
  isFavorite: boolean;
  onToggleFavorite?: () => void;
  onViewDetails?: () => void;
}

function HorizontalMovieCard({
  movie,
  posterUrl,
  genre,
  runtime,
  isFavorite,
  onToggleFavorite,
  onViewDetails,
}: HorizontalMovieCardProps) {
  const [imgError, setImgError] = useState(false);
  const hasPoster = Boolean(posterUrl && !imgError);

  return (
    <div className="flex gap-6 rounded-xl overflow-hidden bg-surface border border-border2 p-6">
      {/* LEFT: Poster */}
      <div className="shrink-0 w-32 md:w-40">
        <div className="relative aspect-2/3 bg-surface2 rounded-lg overflow-hidden">
          {hasPoster ? (
            <Image
              src={posterUrl as string}
              alt={`Póster de ${movie.title}`}
              fill
              priority
              sizes="200px"
              className="object-cover"
              onError={() => setImgError(true)}
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center bg-linear-to-br from-surface2 to-surface">
              <Film className="w-10 h-10 text-muted/30" />
            </div>
          )}
        </div>
      </div>

      {/* RIGHT: Content */}
      <div className="flex-1 space-y-4 flex flex-col justify-between">
        {/* Badge */}
        <div className="flex items-center gap-1.5 w-fit px-2.5 py-1 rounded-full bg-teal/10 border border-teal/40">
          <span className="w-1 h-1 rounded-full bg-teal animate-pulse" />
          <span className="text-[10px] font-bold text-teal tracking-wide">
            ELEGIDA PARA TI - ESTA NOCHE
          </span>
        </div>

        {/* Title */}
        <h2 className="font-display text-2xl md:text-3xl font-bold text-text leading-tight">
          {movie.title}
        </h2>

        {/* Metadata */}
        <div className="flex gap-2 text-xs text-muted flex-wrap">
          {genre && <span>{genre}</span>}
          {movie.director && (
            <>
              <span>·</span>
              <span>{movie.director}</span>
            </>
          )}
          {runtime && (
            <>
              <span>·</span>
              <span>{runtime}</span>
            </>
          )}
        </div>

        {/* Synopsis */}
        <p className="text-sm text-muted/90 line-clamp-3 leading-relaxed">
          {movie.description ||
            "Un thriller psicológico de ciencia ficción que explora los límites de la identidad y la memoria en un futuro distópico."}
        </p>

        {/* Score and Actions */}
        <div className="space-y-4">
          {typeof movie.compatibilityScore === "number" && (
            <ScoreBar
              score={movie.compatibilityScore}
              label="Compatibilidad"
              animated
              variant="gradient"
            />
          )}

          <div className="flex gap-3">
            <Button
              variant="primary"
              onClick={onViewDetails}
              className="flex-1 bg-accent2 hover:bg-accent2/90"
            >
              <ExternalLink className="w-4 h-4 mr-2" />
              Ver detalles
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggleFavorite}
              aria-label={
                isFavorite ? "Quitar de favoritos" : "Agregar a favoritos"
              }
              className="hover:bg-surface2"
            >
              <Heart
                className={cn(
                  "w-4 h-4 transition-colors",
                  isFavorite ? "fill-accent2 text-accent2" : "text-muted",
                )}
              />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Horizontal Card Skeleton ──────────────────────────────────────────────────────

function HorizontalCardSkeleton() {
  return (
    <div className="flex gap-6 rounded-xl overflow-hidden bg-surface border border-border2 p-6">
      <SkeletonBox className="shrink-0 w-32 md:w-40 aspect-2/3 rounded-lg" />
      <div className="flex-1 space-y-4">
        <SkeletonBox className="h-5 w-32 rounded-full" />
        <SkeletonBox className="h-8 w-3/4 rounded" />
        <SkeletonBox className="h-3 w-1/2 rounded" />
        <SkeletonBox className="h-16 w-full rounded" />
        <SkeletonBox className="h-2 w-full rounded" />
        <SkeletonBox className="h-10 w-full rounded" />
      </div>
    </div>
  );
}
