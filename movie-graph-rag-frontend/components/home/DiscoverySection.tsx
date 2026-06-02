"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Network, Compass, Shuffle, Smile } from "lucide-react";
import { useRouter } from "next/navigation";

const DISCOVERY_FEATURES = [
  {
    icon: Network,
    title: "Connection Explorer",
    description:
      "Discover the semantic path between two movies or directors in the graph",
    href: "/connections",
  },
  {
    icon: Compass,
    title: "Cinematic Journey",
    description:
      "Walk a curated sequence of 5–7 thematically connected movies",
    href: null,
  },
  {
    icon: Shuffle,
    title: "Random Wheel",
    description:
      "Multi-hop navigation through the graph to discover something completely new",
    href: null,
  },
  {
    icon: Smile,
    title: "Mood Selector",
    description:
      "Recommendations based on your current mood and preferences",
    href: null,
  },
] as const;

export function DiscoverySection() {
  const router = useRouter();

  return (
    <section className="mb-10">
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-center">
          Intelligent Discovery
        </h2>
        <p className="text-muted-foreground text-sm mt-1 text-center">
          Explore movies in unique ways using the power of the knowledge graph
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {DISCOVERY_FEATURES.map((feature) => (
          <Card
            key={feature.title}
            className="bg-card border-border hover:border-accent/60 transition-all cursor-pointer group"
            onClick={() => feature.href && router.push(feature.href)}
          >
            <CardContent className="p-4 flex flex-col items-center text-center gap-2">
              <div className="h-12 w-12 rounded-full bg-accent/10 flex items-center justify-center group-hover:bg-accent/20 transition-colors">
                <feature.icon className="h-6 w-6 text-accent" />
              </div>
              <h3 className="font-semibold text-base">{feature.title}</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {feature.description}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}
