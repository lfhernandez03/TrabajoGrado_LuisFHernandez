"use client";

import { Bot, Loader2 } from "lucide-react";

export function LoadingBubble() {
  return (
    <div className="flex gap-3">
      <div className="shrink-0 h-8 w-8 bg-accent/30 rounded-full flex items-center justify-center">
        <Bot className="h-4 w-4 text-accent-foreground" />
      </div>
      <div className="max-w-[80%]">
        <div className="bg-muted rounded-2xl rounded-bl-md px-4 py-3">
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
            <span className="text-sm text-muted-foreground">
              Analizando tu consulta con el grafo de conocimiento...
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
