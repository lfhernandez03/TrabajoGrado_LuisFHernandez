"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import Image from "next/image";
import { Network, Heart, AlertCircle, ChevronRight, Star, Clapperboard, Users } from "lucide-react";
import { Navbar } from "@/components/organisms/Navbar";
import { TopologicalProfile, TopologicalProfileSkeleton } from "@/components/organisms/TopologicalProfile";
import { ProtectedRoute } from "@/components/shared/ProtectedRoute";
import { Button } from "@/components/atoms";
import { getUserTopology, type TopologicalProfileResponse } from "@/services/topology.service";
import { getMyFavorites, type FavoriteMovie } from "@/services/favorites.service";
import { useAuth } from "@/hooks/useAuth";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// ── Compact poster strip ──────────────────────────────────────────────────────

function FavoritePoster({ movie }: { movie: FavoriteMovie }) {
  return (
    <div className="relative w-24 shrink-0 aspect-2/3 rounded-lg overflow-hidden border border-border bg-surface2 group">
      {movie.posterUrl ? (
        <Image
          src={movie.posterUrl}
          alt={movie.title}
          fill
          className="object-cover transition-transform duration-300 group-hover:scale-105"
          sizes="96px"
        />
      ) : (
        <div className="flex items-center justify-center h-full text-muted text-xs text-center px-2">
          {movie.title}
        </div>
      )}
      {/* title tooltip on hover */}
      <div className="absolute inset-x-0 bottom-0 bg-linear-to-t from-black/80 to-transparent px-1.5 pb-1.5 pt-4 opacity-0 group-hover:opacity-100 transition-opacity">
        <p className="text-white text-[10px] leading-tight line-clamp-2">{movie.title}</p>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ProfilePage() {
  const { user } = useAuth();
  const [topology, setTopology] = useState<TopologicalProfileResponse | null>(null);
  const [topologyLoading, setTopologyLoading] = useState(true);
  const [topologyError, setTopologyError] = useState(false);
  const [favorites, setFavorites] = useState<FavoriteMovie[]>([]);
  const [favLoading, setFavLoading] = useState(true);

  useEffect(() => {
    getUserTopology()
      .then(setTopology)
      .catch(() => {
        setTopologyError(true);
        toast.error("Could not load topological profile");
      })
      .finally(() => setTopologyLoading(false));

    getMyFavorites()
      .then(setFavorites)
      .catch(() => toast.error("Could not load your favorites"))
      .finally(() => setFavLoading(false));
  }, []);

  const initials = user?.name ? user.name.slice(0, 2).toUpperCase() : "??";
  const recentFavorites = favorites.slice(0, 6);

  // ── Stats computed from favorites ─────────────────────────────────────────
  const genreStats = useMemo(() => {
    const counts: Record<string, number> = {};
    favorites.forEach((m) => (m.genres ?? []).forEach((g) => { counts[g] = (counts[g] ?? 0) + 1; }));
    const total = Object.values(counts).reduce((s, n) => s + n, 0) || 1;
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([genre, count]) => ({ genre, count, pct: Math.round((count / total) * 100) }));
  }, [favorites]);

  const avgRating = useMemo(() => {
    const rated = favorites.filter((m) => m.rating);
    return rated.length ? (rated.reduce((s, m) => s + m.rating!, 0) / rated.length).toFixed(1) : null;
  }, [favorites]);

  const uniqueDirectors = useMemo(
    () => new Set(favorites.map((m) => m.director).filter(Boolean)).size,
    [favorites]
  );

  const uniqueGenres = useMemo(
    () => new Set(favorites.flatMap((m) => m.genres ?? [])).size,
    [favorites]
  );

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-bg">
        <Navbar />

        <main className="container mx-auto px-4 py-8 max-w-6xl space-y-8">

          {/* ── Header ─────────────────────────────────────────────────────── */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-5">
            <div className="h-20 w-20 rounded-2xl bg-accent/10 border border-accent/30 flex items-center justify-center shrink-0">
              <span className="font-display text-3xl text-accent">{initials}</span>
            </div>
            <div className="flex-1 min-w-0">
              <h1 className="font-display text-4xl tracking-wide text-text">
                {user?.name ?? "My profile"}
              </h1>
              <p className="text-muted text-sm mt-1">
                {favorites.length} favorites · personalized movie profile
              </p>
            </div>
            <Link href="/topology">
              <Button variant="secondary" size="md">
                <Network className="h-4 w-4 mr-1.5" />
                Topology Dashboard
              </Button>
            </Link>
          </div>

          {/* ── Topological profile — full width ───────────────────────────── */}
          <section className="bg-surface rounded-xl border border-border p-6">
            {topologyLoading && <TopologicalProfileSkeleton />}

            {!topologyLoading && topologyError && (
              <div className="flex flex-col items-center py-10 gap-3 text-center">
                <AlertCircle className="h-8 w-8 text-muted opacity-50" />
                <p className="text-sm text-muted">Topological profile not available.</p>
                <p className="text-xs text-muted">
                  Requires saved favorites and executed graph analysis.
                </p>
                <Link href="/topology">
                  <Button variant="ghost" size="sm">View topology dashboard</Button>
                </Link>
              </div>
            )}

            {!topologyLoading && topology && (
              <TopologicalProfile profile={topology} orientation="horizontal" />
            )}
          </section>

          {/* ── Quick stats ───────────────────────────────────────────────── */}
          {!favLoading && favorites.length > 0 && (
            <section className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: "Favorites", value: favorites.length, icon: Heart, color: "text-accent" },
                { label: "Genres", value: uniqueGenres, icon: Clapperboard, color: "text-teal" },
                { label: "Directors", value: uniqueDirectors, icon: Users, color: "text-accent2" },
                { label: "Avg rating", value: avgRating ?? "—", icon: Star, color: "text-yellow-400" },
              ].map(({ label, value, icon: Icon, color }) => (
                <div key={label} className="bg-surface rounded-xl border border-border px-4 py-3 flex items-center gap-3">
                  <Icon className={cn("w-5 h-5 shrink-0", color)} />
                  <div>
                    <p className="text-xl font-bold font-display leading-none">{value}</p>
                    <p className="text-[11px] text-muted mt-0.5">{label}</p>
                  </div>
                </div>
              ))}
            </section>
          )}

          {/* ── Genre breakdown ────────────────────────────────────────────── */}
          {!favLoading && genreStats.length > 0 && (
            <section className="bg-surface rounded-xl border border-border p-5 space-y-4">
              <h2 className="font-display text-base tracking-wide text-muted uppercase text-[11px] font-semibold">
                Genre breakdown
              </h2>
              <div className="space-y-2.5">
                {genreStats.map(({ genre, count, pct }, i) => (
                  <div key={genre} className="flex items-center gap-3">
                    <span className="text-xs text-muted/50 tabular-nums w-4 shrink-0">{i + 1}</span>
                    <span className="text-sm text-text w-28 shrink-0 truncate">{genre}</span>
                    <div className="flex-1 h-2 bg-bg rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-teal to-accent transition-all duration-700"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-xs text-muted tabular-nums w-16 text-right shrink-0">
                      {count} · {pct}%
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* ── Recent favorites strip ─────────────────────────────────────── */}
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Heart className="h-4 w-4 text-accent" />
                <h2 className="font-display text-xl tracking-wide">Recent Favorites</h2>
              </div>
              <Link
                href="/favorites"
                className="flex items-center gap-1 text-sm text-muted hover:text-teal transition-colors"
              >
                View all ({favorites.length})
                <ChevronRight className="h-4 w-4" />
              </Link>
            </div>

            {favLoading ? (
              <div className="flex gap-4">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="w-24 aspect-2/3 rounded-lg bg-surface2 animate-pulse shrink-0" />
                ))}
              </div>
            ) : recentFavorites.length > 0 ? (
              <div className="flex gap-4">
                {recentFavorites.map((movie) => (
                  <FavoritePoster key={movie.uri} movie={movie} />
                ))}
              </div>
            ) : (
              <div className="flex items-center gap-4">
                <p className="text-sm text-muted">You don't have any favorites yet.</p>
                <Link href="/search">
                  <Button variant="primary" size="sm">Explore movies</Button>
                </Link>
              </div>
            )}
          </section>

        </main>
      </div>
    </ProtectedRoute>
  );
}
