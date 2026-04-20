"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Navbar } from "@/components/organisms/Navbar";
import { ProtectedRoute } from "@/components/shared/ProtectedRoute";
import {
  Network,
  GitBranch,
  BarChart3,
  Globe,
  Users,
  Layers,
  Star,
  Zap,
} from "lucide-react";
import {
  getGraphTopology,
  GraphTopologyResponse,
  CentralityEntry,
} from "@/services/graph.service";
import { toast } from "sonner";

// ---------------------------------------------------------------------------
// Bar component (pure Tailwind, no chart library needed)
// ---------------------------------------------------------------------------

function CentralityBar({
  entry,
  maxValue,
  color,
}: {
  entry: CentralityEntry;
  maxValue: number;
  color: string;
}) {
  const pct = maxValue > 0 ? (entry.value / maxValue) * 100 : 0;
  return (
    <div className="flex items-center gap-3 py-1">
      <div className="w-40 shrink-0 text-sm truncate text-right text-muted-foreground" title={entry.title}>
        {entry.title}
      </div>
      <div className="flex-1 h-5 bg-muted rounded overflow-hidden">
        <div
          className={`h-full rounded transition-all duration-500 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-muted-foreground w-16 text-right">
        {entry.value.toFixed(4)}
      </span>
      {entry.genre && (
        <Badge variant="outline" className="text-xs shrink-0">
          {entry.genre}
        </Badge>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Stat card
// ---------------------------------------------------------------------------

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  highlight,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  sub?: string;
  highlight?: boolean;
}) {
  return (
    <Card className={highlight ? "border-primary/50 bg-primary/5" : ""}>
      <CardContent className="pt-5 pb-4">
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-lg ${highlight ? "bg-primary/10" : "bg-muted"}`}>
            <Icon className={`h-5 w-5 ${highlight ? "text-primary" : "text-muted-foreground"}`} />
          </div>
          <div className="min-w-0">
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="text-2xl font-bold mt-0.5">{value}</p>
            {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Skeleton while loading
// ---------------------------------------------------------------------------

function TopologySkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-xl" />
        ))}
      </div>
      <div className="grid md:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-72 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-64 rounded-xl" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function TopologyPage() {
  const [data, setData] = useState<GraphTopologyResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getGraphTopology()
      .then(setData)
      .catch(() => toast.error("Error loading topology dashboard"))
      .finally(() => setLoading(false));
  }, []);

  const maxDegree = data ? Math.max(...data.topByDegree.map((e) => e.value), 1) : 1;
  const maxBetween = data ? Math.max(...data.topByBetweenness.map((e) => e.value), 1) : 1;
  const maxPageRank = data ? Math.max(...data.topByPageRank.map((e) => e.value), 1) : 1;

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-background">
        <Navbar />

        <main className="container mx-auto px-4 py-8 max-w-6xl">
          {/* Header */}
          <div className="mb-8 flex items-center gap-3">
            <div className="p-3 rounded-xl bg-primary/10">
              <Network className="h-7 w-7 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">Topology Dashboard</h1>
              <p className="text-muted-foreground text-sm mt-0.5">
                Complex network metrics of the movie knowledge graph
              </p>
            </div>
          </div>

          {loading && <TopologySkeleton />}

          {!loading && data && (
            <div className="space-y-6">

              {/* Summary cards */}
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                <StatCard
                  icon={Globe}
                  label="Indexed movies"
                  value={data.graphSummary.totalMovies.toLocaleString()}
                />
                <StatCard
                  icon={GitBranch}
                  label="Estimated edges"
                  value={data.graphSummary.totalEdges.toLocaleString()}
                />
                <StatCard
                  icon={BarChart3}
                  label="Average degree"
                  value={data.graphSummary.averageDegree.toFixed(1)}
                />
                <StatCard
                  icon={Layers}
                  label="Clustering coef."
                  value={data.graphSummary.averageClusteringCoefficient.toFixed(3)}
                />
                <StatCard
                  icon={Users}
                  label="Communities"
                  value={data.graphSummary.communityCount}
                />
                <StatCard
                  icon={Star}
                  label="Modularity"
                  value={data.graphSummary.modularity.toFixed(3)}
                  sub="(higher = better separation)"
                />
              </div>

              {/* Small-world badge */}
              {data.graphSummary.isSmallWorld && (
                <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 dark:text-emerald-400">
                  <Zap className="h-4 w-4 shrink-0" />
                  <span className="text-sm font-medium">
                    Small-world detected — high clustering coefficient with reduced diameter, characteristic property of real complex networks.
                  </span>
                </div>
              )}

              {/* Centrality rankings */}
              <div className="grid md:grid-cols-3 gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                      <BarChart3 className="h-4 w-4 text-blue-500" />
                      Top — Degree Centrality
                    </CardTitle>
                    <p className="text-xs text-muted-foreground">
                      Movies with most direct connections
                    </p>
                  </CardHeader>
                  <CardContent className="space-y-1">
                    {data.topByDegree.map((e, i) => (
                      <CentralityBar
                        key={i}
                        entry={e}
                        maxValue={maxDegree}
                        color="bg-blue-500"
                      />
                    ))}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                      <GitBranch className="h-4 w-4 text-amber-500" />
                      Top — Betweenness Centrality
                    </CardTitle>
                    <p className="text-xs text-muted-foreground">
                      Bridge movies between communities
                    </p>
                  </CardHeader>
                  <CardContent className="space-y-1">
                    {data.topByBetweenness.map((e, i) => (
                      <CentralityBar
                        key={i}
                        entry={e}
                        maxValue={maxBetween}
                        color="bg-amber-500"
                      />
                    ))}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Network className="h-4 w-4 text-purple-500" />
                      Top — PageRank
                    </CardTitle>
                    <p className="text-xs text-muted-foreground">
                      Most globally influential movies
                    </p>
                  </CardHeader>
                  <CardContent className="space-y-1">
                    {data.topByPageRank.map((e, i) => (
                      <CentralityBar
                        key={i}
                        entry={e}
                        maxValue={maxPageRank}
                        color="bg-purple-500"
                      />
                    ))}
                  </CardContent>
                </Card>
              </div>

              {/* Community summary */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Users className="h-4 w-4 text-emerald-500" />
                    Detected Communities (Louvain)
                  </CardTitle>
                  <p className="text-xs text-muted-foreground">
                    Movie groups with high internal cohesion. Generated offline with NetworkX + Gemini.
                  </p>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b text-muted-foreground">
                          <th className="text-left pb-2 pr-4 font-medium">ID</th>
                          <th className="text-left pb-2 pr-4 font-medium">Label</th>
                          <th className="text-right pb-2 font-medium">Movies</th>
                          <th className="text-right pb-2 font-medium pl-4">Proportion</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.clusterSummary.map((c) => {
                          const pct =
                            data.graphSummary.totalMovies > 0
                              ? ((c.size / data.graphSummary.totalMovies) * 100).toFixed(1)
                              : "0.0";
                          return (
                            <tr key={c.clusterId} className="border-b last:border-0 hover:bg-muted/40">
                              <td className="py-2 pr-4 text-muted-foreground font-mono text-xs">
                                {c.clusterId}
                              </td>
                              <td className="py-2 pr-4">{c.label}</td>
                              <td className="py-2 text-right tabular-nums">{c.size}</td>
                              <td className="py-2 pl-4">
                                <div className="flex items-center gap-2 justify-end">
                                  <div className="w-20 h-2 bg-muted rounded overflow-hidden">
                                    <div
                                      className="h-full bg-emerald-500 rounded"
                                      style={{ width: `${pct}%` }}
                                    />
                                  </div>
                                  <span className="text-muted-foreground text-xs w-10 text-right">
                                    {pct}%
                                  </span>
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>

            </div>
          )}

          {!loading && !data && (
            <div className="flex flex-col items-center justify-center py-24 text-muted-foreground gap-3">
              <Network className="h-12 w-12 opacity-30" />
              <p>Could not load topological metrics.</p>
              <p className="text-sm">
                Ejecuta <code className="bg-muted px-1 rounded">scripts/compute_network_metrics.py</code> y vuelve a intentarlo.
              </p>
            </div>
          )}
        </main>
      </div>
    </ProtectedRoute>
  );
}
