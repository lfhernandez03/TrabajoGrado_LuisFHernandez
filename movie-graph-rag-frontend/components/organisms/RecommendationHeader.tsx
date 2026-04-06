"use client";

import { cn } from "@/lib/utils";

interface RecommendationHeaderProps {
  className?: string;
  movieTitle?: string;
  genres?: string[];
}

export function RecommendationHeader({ className, movieTitle, genres }: RecommendationHeaderProps) {
  const genreText = genres && genres.length > 0 ? genres.slice(0, 2).join(" y ") : "películas de calidad";

  return (
    <section className={cn("py-12 md:py-16", className)}>
      <div className="px-6 md:px-12 lg:px-20">
        <div className="max-w-7xl mx-auto">
          <div className="space-y-8 w-full ml-auto">
            {/* Header: Badge + Title */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 w-fit px-3 py-1.5 rounded-full border border-teal/40 bg-teal/5">
                <span className="w-1.5 h-1.5 rounded-full bg-teal animate-pulse" />
                <span className="text-xs font-semibold text-teal tracking-wide">
                  RECOMENDACIÓN SEMÁNTICA ACTIVA
                </span>
              </div>

              <h2 className="font-display tracking-tight text-5xl md:text-6xl lg:text-7xl font-black leading-tight">
                <span className="block text-text">DESCUBRE TU</span>
                <span className="block bg-linear-to-r from-accent2 via-accent2/80 to-accent2/60 bg-clip-text text-transparent">
                  PRÓXIMA PELÍCULA
                </span>
              </h2>

              {/* Subtitle with dynamic genre highlights */}
              <p className="text-sm md:text-base text-muted max-w-xl leading-relaxed">
                Basado en tu interés en{" "}
                <span className="font-semibold" style={{ color: 'var(--color-purple)' }}>
                  {genreText}
                </span>{" "}
                {movieTitle && `— y lo que viste en ${movieTitle} `} 
                dice sobre tu siguiente paso.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
