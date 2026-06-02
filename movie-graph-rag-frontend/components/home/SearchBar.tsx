"use client";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search, Heart, MessageSquare, History } from "lucide-react";

interface SearchBarProps {
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
  onSearch: () => void;
  onNavigateFavorites: () => void;
  onOpenHistory: () => void;
  onNavigateChat: () => void;
  isSearching: boolean;
}

export function SearchBar({
  searchQuery,
  onSearchQueryChange,
  onSearch,
  onNavigateFavorites,
  onOpenHistory,
  onNavigateChat,
  isSearching,
}: SearchBarProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      onSearch();
    }
  };

  return (
    <div className="container mx-auto px-4 py-4">
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Input
            placeholder="Search movies..."
            className="w-full pr-10 bg-secondary/50 border-border"
            value={searchQuery}
            onChange={(e) => onSearchQueryChange(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isSearching}
          />
          <button
            onClick={onSearch}
            disabled={isSearching}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-primary transition-colors"
          >
            <Search className="h-5 w-5" />
          </button>
        </div>

        <Button
          variant="ghost"
          size="icon"
          className="shrink-0 text-muted-foreground hover:text-primary"
          onClick={onNavigateFavorites}
          title="Favorites"
        >
          <Heart className="h-5 w-5" />
        </Button>

        <Button
          variant="ghost"
          size="icon"
          className="shrink-0 text-muted-foreground hover:text-primary"
          onClick={onNavigateChat}
          title="Recommendation Chat"
        >
          <MessageSquare className="h-5 w-5" />
        </Button>

        <Button
          variant="ghost"
          size="icon"
          className="shrink-0 text-muted-foreground hover:text-primary"
          onClick={onOpenHistory}
          title="History"
        >
          <History className="h-5 w-5" />
        </Button>
      </div>
    </div>
  );
}
