"use client";

import { Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";

export function FloatingChatButton() {
  const router = useRouter();

  return (
    <div className="fixed bottom-6 right-6 z-50 flex items-end gap-3">
      <div className="bg-card border border-accent/40 text-foreground text-sm rounded-2xl rounded-br-none px-4 py-3 shadow-lg max-w-50">
        <p className="font-medium text-accent">¿Necesitas ayuda?</p>
        <p className="text-muted-foreground text-xs mt-0.5">
          Pregúntame sobre películas, géneros o recomendaciones.
        </p>
      </div>
      <button
        onClick={() => router.push("/chat")}
        className="h-14 w-14 shrink-0 rounded-full bg-accent text-accent-foreground shadow-lg hover:bg-accent/90 transition-all hover:scale-105 flex items-center justify-center"
        title="Asistente IA"
      >
        <Sparkles className="h-6 w-6" />
      </button>
    </div>
  );
}
