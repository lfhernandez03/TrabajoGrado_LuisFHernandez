"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Input } from "@/components/ui/input";
import { Film, Search, Loader2, Tag } from "lucide-react";
import { autocompleteMovies, MovieSuggestion } from "@/services/movies.service";
import { type SearchMode } from "@/lib/sparql";

// Ontology genre literals — filtered client-side in genre mode
const GENRE_SUGGESTIONS = [
  "Action", "Adventure", "Animation", "Children",
  "Comedy", "Drama", "Horror", "Romance", "Sci-Fi", "Thriller",
];

export interface MovieSearchInputProps {
  value?: string;
  onChange?: (value: string) => void;
  onSelect: (movie: MovieSuggestion) => void;
  onSubmit?: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  mode?: SearchMode;
}

export function MovieSearchInput({
  value: controlledValue,
  onChange: controlledOnChange,
  onSelect,
  onSubmit,
  placeholder = "Search movie...",
  disabled = false,
  className,
  mode = "title",
}: MovieSearchInputProps) {
  const [internalValue, setInternalValue] = useState("");
  const value = controlledValue ?? internalValue;
  const onChange = controlledOnChange ?? setInternalValue;

  const [suggestions, setSuggestions] = useState<MovieSuggestion[]>([]);
  const [genreSuggestions, setGenreSuggestions] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchSuggestions = useCallback(async (term: string) => {
    if (term.trim().length < 2) {
      setSuggestions([]);
      setIsOpen(false);
      return;
    }
    setIsLoading(true);
    try {
      const results = await autocompleteMovies(term, 6);
      setSuggestions(results);
      setIsOpen(results.length > 0);
      setHighlightedIndex(-1);
    } catch {
      setSuggestions([]);
      setIsOpen(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    onChange(newValue);

    if (mode === "title") {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => fetchSuggestions(newValue), 300);
    } else if (mode === "genre") {
      const term = newValue.trim().toLowerCase();
      const filtered = term
        ? GENRE_SUGGESTIONS.filter((g) => g.toLowerCase().includes(term))
        : GENRE_SUGGESTIONS;
      setGenreSuggestions(filtered);
      setIsOpen(filtered.length > 0);
      setHighlightedIndex(-1);
    } else {
      // director: no autocomplete
      setSuggestions([]);
      setIsOpen(false);
    }
  };

  const handleSelect = (movie: MovieSuggestion) => {
    onChange(movie.title);
    onSelect(movie);
    setIsOpen(false);
    setSuggestions([]);
  };

  const handleGenreSelect = (genre: string) => {
    onChange(genre);
    setIsOpen(false);
    setGenreSuggestions([]);
    onSubmit?.(genre);
  };

  // Reset genre dropdown when mode changes
  useEffect(() => {
    setSuggestions([]);
    setGenreSuggestions([]);
    setIsOpen(false);
  }, [mode]);

  // Show all genres on focus when genre mode and input is empty
  const handleFocus = () => {
    if (mode === "genre") {
      const term = value.trim().toLowerCase();
      const filtered = term
        ? GENRE_SUGGESTIONS.filter((g) => g.toLowerCase().includes(term))
        : GENRE_SUGGESTIONS;
      setGenreSuggestions(filtered);
      setIsOpen(filtered.length > 0);
    } else if (mode === "title" && suggestions.length > 0) {
      setIsOpen(true);
    }
  };

  const activeSuggestions = mode === "genre" ? genreSuggestions : suggestions;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || activeSuggestions.length === 0) return;

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setHighlightedIndex((prev) =>
          prev < activeSuggestions.length - 1 ? prev + 1 : 0
        );
        break;
      case "ArrowUp":
        e.preventDefault();
        setHighlightedIndex((prev) =>
          prev > 0 ? prev - 1 : activeSuggestions.length - 1
        );
        break;
      case "Enter":
        e.preventDefault();
        if (highlightedIndex >= 0) {
          if (mode === "genre") {
            handleGenreSelect(genreSuggestions[highlightedIndex]);
          } else {
            handleSelect(suggestions[highlightedIndex]);
          }
        } else if (onSubmit && value.trim()) {
          setIsOpen(false);
          onSubmit(value.trim());
        }
        break;
      case "Escape":
        setIsOpen(false);
        break;
    }
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, []);

  return (
    <div ref={containerRef} className="relative w-full">
      <div className="relative">
        <Input
          value={value}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={handleFocus}
          placeholder={placeholder}
          disabled={disabled}
          className={`pr-8 ${className || ""}`}
        />
        <div className="absolute right-2.5 top-1/2 -translate-y-1/2">
          {isLoading ? (
            <Loader2 className="h-4 w-4 text-muted-foreground animate-spin" />
          ) : (
            <Search className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </div>

      {/* Genre suggestions dropdown */}
      {isOpen && mode === "genre" && genreSuggestions.length > 0 && (
        <div className="absolute z-50 top-full mt-1 w-full bg-surface border border-border rounded-lg shadow-lg overflow-hidden">
          {genreSuggestions.map((genre, index) => (
            <button
              key={genre}
              type="button"
              onClick={() => handleGenreSelect(genre)}
              onMouseEnter={() => setHighlightedIndex(index)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors ${
                index === highlightedIndex
                  ? "bg-teal/15 text-text"
                  : "hover:bg-muted/50"
              }`}
            >
              <Tag className="h-4 w-4 shrink-0 text-teal" />
              <p className="text-sm font-medium">{genre}</p>
            </button>
          ))}
        </div>
      )}

      {/* Title suggestions dropdown (existing behavior) */}
      {isOpen && mode === "title" && suggestions.length > 0 && (
        <div className="absolute z-50 top-full mt-1 w-full bg-surface border border-border rounded-lg shadow-lg overflow-hidden">
          {suggestions.map((movie, index) => (
            <button
              key={movie.uri}
              type="button"
              onClick={() => handleSelect(movie)}
              onMouseEnter={() => setHighlightedIndex(index)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors ${
                index === highlightedIndex
                  ? "bg-accent/15 text-accent-foreground"
                  : "hover:bg-muted/50"
              }`}
            >
              <Film className="h-4 w-4 shrink-0 text-accent" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium truncate">{movie.title}</p>
                {movie.director && (
                  <p className="text-xs text-muted-foreground truncate">
                    Dir: {movie.director}
                  </p>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
