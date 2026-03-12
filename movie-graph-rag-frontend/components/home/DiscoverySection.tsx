"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Network, Compass, Shuffle, Smile } from "lucide-react";
import { useRouter } from "next/navigation";

const DISCOVERY_FEATURES = [
  {
    icon: Network,
    title: "Explorador de Conexiones",
    description:
      "Descubre el camino semántico entre dos películas o directores en el grafo",
    href: "/connections",
  },
  {
    icon: Compass,
    title: "Viaje Cinematográfico",
    description:
      "Recorre una secuencia curada de 5-7 películas conectadas temáticamente",
    href: null,
  },
  {
    icon: Shuffle,
    title: "Rueda Aleatoria",
    description:
      "Navegación multihop por el grafo para descubrir algo completamente nuevo",
    href: null,
  },
  {
    icon: Smile,
    title: "Selector Emocional",
    description:
      "Recomendaciones basadas en tu estado de ánimo y preferencias del momento",
    href: null,
  },
] as const;

export function DiscoverySection() {
  const router = useRouter();

  return (
    <section className="mb-10">
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-center">
          Descubrimiento Inteligente
        </h2>
        <p className="text-muted-foreground text-sm mt-1 text-center">
          Explora películas de formas únicas usando el poder del grafo de
          conocimiento
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
