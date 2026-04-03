"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { User, Heart, Network, AlertCircle } from "lucide-react";
import { Navbar } from "@/components/organisms/Navbar";
import { MovieGrid } from "@/components/organisms/MovieGrid";
import { TopologicalProfile, TopologicalProfileSkeleton } from "@/components/organisms/TopologicalProfile";
import { type MovieCardMovie } from "@/components/organisms/MovieCard";
import { ProtectedRoute } from "@/components/shared/ProtectedRoute";
import { Button } from "@/components/atoms";
import { getUserTopology, type TopologicalProfileResponse } from "@/services/topology.service";
import { getMyFavorites, type FavoriteMovie } from "@/services/favorites.service";
import { useAuth } from "@/hooks/useAuth";
import { toast } from "sonner";

function toCardMovie(m: FavoriteMovie): MovieCardMovie {
  return {
    uri: m.uri,
    title: m.title,
    posterUrl: m.posterUrl,
    year: m.year,
    runtime: m.runtime,
    genres: m.genres,
    rating: m.rating,
  };
}

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

  const initials = user?.name
    ? user.name.slice(0, 2).toUpperCase()
    : "??";

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-bg">
        <Navbar />

        <main className="container mx-auto px-4 py-8 max-w-6xl">

          {/* ── Header ─────────────────────────────────────────────────────── */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-5 mb-10">
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

          {/* ── Main grid ──────────────────────────────────────────────────── */}
          <div className="grid lg:grid-cols-[1fr_340px] gap-8">

            {/* Left — Favorites */}
            <section className="space-y-5">
              <div className="flex items-center gap-2">
                <Heart className="h-5 w-5 text-accent" />
                <h2 className="font-display text-2xl tracking-wide">Mis favoritas</h2>
                {!favLoading && (
                  <span className="text-sm text-muted ml-1">({favorites.length})</span>
                )}
              </div>

              <MovieGrid
                movies={favorites.map(toCardMovie)}
                isLoading={favLoading}
                skeletonCount={8}
                isFavorite={() => true}
                emptyMessage="Aún no tienes películas favoritas. ¡Explora y agrega algunas!"
              />

              {!favLoading && favorites.length === 0 && (
                <div className="flex justify-center pt-2">
                  <Link href="/search">
                    <Button variant="primary" size="md">
                      Explorar películas
                    </Button>
                  </Link>
                </div>
              )}
            </section>

            {/* Right — Topological profile */}
            <aside className="space-y-5">
              <div className="flex items-center gap-2">
                <User className="h-5 w-5 text-teal" />
                <h2 className="font-display text-2xl tracking-wide">Perfil topológico</h2>
              </div>

              <div className="bg-surface rounded-xl border border-border p-5">
                {topologyLoading && <TopologicalProfileSkeleton />}

                {!topologyLoading && topologyError && (
                  <div className="flex flex-col items-center py-8 gap-3 text-center">
                    <AlertCircle className="h-8 w-8 text-muted opacity-50" />
                    <p className="text-sm text-muted">
                      Perfil topológico no disponible.
                    </p>
                    <p className="text-xs text-muted">
                      Requiere favoritos guardados y análisis de grafo ejecutado.
                    </p>
                    <Link href="/topology">
                      <Button variant="ghost" size="sm">Ver dashboard topológico</Button>
                    </Link>
                  </div>
                )}

                {!topologyLoading && topology && (
                  <TopologicalProfile profile={topology} />
                )}
              </div>
            </aside>

          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
