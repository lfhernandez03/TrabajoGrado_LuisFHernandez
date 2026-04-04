"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Network, Heart, AlertCircle, ChevronRight } from "lucide-react";
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
        toast.error("No se pudo cargar el perfil topológico");
      })
      .finally(() => setTopologyLoading(false));

    getMyFavorites()
      .then(setFavorites)
      .catch(() => toast.error("No se pudieron cargar tus favoritos"))
      .finally(() => setFavLoading(false));
  }, []);

  const initials = user?.name ? user.name.slice(0, 2).toUpperCase() : "??";
  const recentFavorites = favorites.slice(0, 3);

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
                {user?.name ?? "Mi perfil"}
              </h1>
              <p className="text-muted text-sm mt-1">
                {favorites.length} favoritos · perfil cinematográfico personalizado
              </p>
            </div>
            <Link href="/topology">
              <Button variant="secondary" size="md">
                <Network className="h-4 w-4 mr-1.5" />
                Dashboard topológico
              </Button>
            </Link>
          </div>

          {/* ── Topological profile — full width ───────────────────────────── */}
          <section className="bg-surface rounded-xl border border-border p-6">
            {topologyLoading && <TopologicalProfileSkeleton />}

            {!topologyLoading && topologyError && (
              <div className="flex flex-col items-center py-10 gap-3 text-center">
                <AlertCircle className="h-8 w-8 text-muted opacity-50" />
                <p className="text-sm text-muted">Perfil topológico no disponible.</p>
                <p className="text-xs text-muted">
                  Requiere favoritos guardados y análisis de grafo ejecutado.
                </p>
                <Link href="/topology">
                  <Button variant="ghost" size="sm">Ver dashboard topológico</Button>
                </Link>
              </div>
            )}

            {!topologyLoading && topology && (
              <TopologicalProfile profile={topology} orientation="horizontal" />
            )}
          </section>

          {/* ── Recent favorites strip ─────────────────────────────────────── */}
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Heart className="h-4 w-4 text-accent" />
                <h2 className="font-display text-xl tracking-wide">Últimas favoritas</h2>
              </div>
              <Link
                href="/favorites"
                className="flex items-center gap-1 text-sm text-muted hover:text-teal transition-colors"
              >
                Ver todas ({favorites.length})
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
                <p className="text-sm text-muted">Aún no tienes favoritas.</p>
                <Link href="/search">
                  <Button variant="primary" size="sm">Explorar películas</Button>
                </Link>
              </div>
            )}
          </section>

        </main>
      </div>
    </ProtectedRoute>
  );
}
