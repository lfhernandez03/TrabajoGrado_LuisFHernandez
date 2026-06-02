"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { FavoriteMovie } from "@/services/favorites.service";
import { Movie } from "@/services/movies.service";
import { Heart, Trash2, Calendar } from "lucide-react";

interface FavoritesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  favorites: FavoriteMovie[];
  isLoading: boolean;
  onRemoveFavorite: (movie: Movie) => void;
  onRecommendSimilar: (movie: Movie) => void;
}

export function FavoritesDialog({
  open,
  onOpenChange,
  favorites,
  isLoading,
  onRemoveFavorite,
  onRecommendSimilar,
}: FavoritesDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Heart className="h-5 w-5 text-accent" />
            My Favorites
          </DialogTitle>
          <DialogDescription>
            {favorites.length} saved movie{favorites.length !== 1 ? "s" : ""}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 mt-4">
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading favorites...
            </div>
          ) : favorites.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              You don&apos;t have any favorite movies yet
            </div>
          ) : (
            favorites.map((movie) => (
              <Card key={movie.uri} className="border-border">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold line-clamp-1">{movie.title}</p>
                      <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                        {movie.description || movie.relationReason || "Favorite movie"}
                      </p>
                      <div className="flex flex-wrap gap-3 mt-2 text-xs text-muted-foreground">
                        {movie.year && <span>{movie.year}</span>}
                        {movie.director && <span>Dir: {movie.director}</span>}
                        {movie.addedAt && (
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {new Date(movie.addedAt).toLocaleDateString("en-US")}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex shrink-0 gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          onRecommendSimilar(movie);
                          onOpenChange(false);
                        }}
                      >
                        Similar movies
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => onRemoveFavorite(movie)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>

        <div className="pt-4 border-t mt-4">
          <Button variant="outline" className="w-full" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
