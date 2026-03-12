import { Film, User, Tag } from "lucide-react";
import type { ConnectionNode } from "@/services/movies.service";

export function getNodeIcon(type: ConnectionNode["type"]) {
  switch (type) {
    case "movie":
      return <Film className="h-4 w-4" />;
    case "person":
      return <User className="h-4 w-4" />;
    case "genre":
      return <Tag className="h-4 w-4" />;
  }
}

export function getNodeColor(type: ConnectionNode["type"]) {
  switch (type) {
    case "movie":
      return "bg-blue-500/20 text-blue-400 border-blue-500/40";
    case "person":
      return "bg-amber-500/20 text-amber-400 border-amber-500/40";
    case "genre":
      return "bg-emerald-500/20 text-emerald-400 border-emerald-500/40";
  }
}

export function getEdgeColor(type: ConnectionNode["type"]) {
  switch (type) {
    case "movie":
      return "border-blue-500/50";
    case "person":
      return "border-amber-500/50";
    case "genre":
      return "border-emerald-500/50";
  }
}
