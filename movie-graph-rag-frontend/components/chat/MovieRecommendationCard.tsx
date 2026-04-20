"use client";

import Image from "next/image";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Film, Star, Clock } from "lucide-react";
import type { ChatRecommendationResponse } from "@/services/chat.service";

interface MovieRecommendationCardProps {
  movie: ChatRecommendationResponse["moviesWithScores"][0];
}

export function MovieRecommendationCard({ movie }: MovieRecommendationCardProps) {
  const [imageError, setImageError] = useState(false);
  const score = movie.compatibilityScore ?? 0;
  const scoreColor =
    score >= 0.8
      ? "text-green-400"
      : score >= 0.6
      ? "text-yellow-400"
      : "text-orange-400";
  const normalizedPosterUrl =
    movie.posterUrl?.startsWith("/")
      ? `https://image.tmdb.org/t/p/w500${movie.posterUrl}`
      : movie.posterUrl;
  const hasPoster = Boolean(normalizedPosterUrl && !imageError);

  return (
    <div className="bg-background/60 border border-border/50 rounded-lg p-3 flex items-center gap-3">
      <div className="shrink-0 h-14 w-10 bg-primary/10 rounded-md overflow-hidden flex items-center justify-center p-1">
        {hasPoster && normalizedPosterUrl ? (
          <Image
            src={normalizedPosterUrl as string}
            alt={`Poster of ${movie.title}`}
            width={40}
            height={56}
            className="h-full w-full object-contain"
            onError={() => setImageError(true)}
          />
        ) : (
          <Film className="h-5 w-5 text-primary" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{movie.title}</p>
        <div className="flex items-center gap-2 mt-0.5">
          {movie.genreName && (
            <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
              {movie.genreName}
            </Badge>
          )}
          {movie.runtime && (
            <span className="text-[10px] text-muted-foreground flex items-center gap-0.5">
              <Clock className="h-3 w-3" />
              {movie.runtime} min
            </span>
          )}
          {movie.releaseDate && (
            <span className="text-[10px] text-muted-foreground">
              {new Date(movie.releaseDate).getFullYear()}
            </span>
          )}
        </div>
      </div>
      <div className="shrink-0 text-right">
        <p className={`text-sm font-bold ${scoreColor}`}>
          {(score * 100).toFixed(0)}%
        </p>
        <div className="flex items-center gap-0.5">
          <Star className="h-3 w-3 text-yellow-400 fill-yellow-400" />
          <span className="text-[10px] text-muted-foreground">match</span>
        </div>
      </div>
    </div>
  );
}
