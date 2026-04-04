"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Input } from "@/components/ui/input";
import { Film, Search, Loader2 } from "lucide-react";
import {
  autocompleteMovies,
  MovieSuggestion,
} from "@/services/movies.service";

export interface MovieSearchInputProps {
  value?: string;
  onChange?: (value: string) => void;
  onSelect: (movie: MovieSuggestion) => void;
  onSubmit?: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

export function MovieSearchInput({
  value: controlledValue,
  onChange: controlledOnChange,
  onSelect,
  onSubmit,
  placeholder = "Buscar película...",
  disabled = false,
  className,
}: MovieSearchInputProps) {
  const [internalValue, setInternalValue] = useState("");
  const value = controlledValue ?? internalValue;
  const onChange = controlledOnChange ?? setInternalValue;
  const [suggestions, setSuggestions] = useState<MovieSuggestion[]>([]);
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

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      fetchSuggestions(newValue);
    }, 300);
  };

  const handleSelect = (movie: MovieSuggestion) => {
    onChange(movie.title);
    onSelect(movie);
    setIsOpen(false);
    setSuggestions([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || suggestions.length === 0) return;

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setHighlightedIndex((prev) =>
          prev < suggestions.length - 1 ? prev + 1 : 0
        );
        break;
      case "ArrowUp":
        e.preventDefault();
        setHighlightedIndex((prev) =>
          prev > 0 ? prev - 1 : suggestions.length - 1
        );
        break;
      case "Enter":
        e.preventDefault();
        if (highlightedIndex >= 0) {
          handleSelect(suggestions[highlightedIndex]);
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

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  return (
    <div ref={containerRef} className="relative w-full">
      <div className="relative">
        <Input
          value={value}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (suggestions.length > 0) setIsOpen(true);
          }}
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

      {/* Dropdown de sugerencias */}
      {isOpen && suggestions.length > 0 && (
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
