"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Search, Calendar, History } from "lucide-react";
import { HistoryEntry } from "@/services/history.service";
import { toast } from "sonner";

interface HistoryDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  history: HistoryEntry[];
  isLoading: boolean;
  onRepeatSearch: (query: string) => void;
  onRefresh: () => void;
}

export function HistoryDialog({
  open,
  onOpenChange,
  history,
  isLoading,
  onRepeatSearch,
  onRefresh,
}: HistoryDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <History className="h-5 w-5" />
            Search History
          </DialogTitle>
          <DialogDescription>
            Your last {history.length} queries
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 mt-4">
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading history...
            </div>
          ) : history.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No searches in history yet
            </div>
          ) : (
            history.map((entry) => (
              <Card
                key={entry._id}
                className="hover:shadow-md transition-shadow"
              >
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <CardTitle className="text-base flex items-center gap-2">
                        <Search className="h-4 w-4" />
                        {entry.query}
                      </CardTitle>
                      <CardDescription className="flex items-center gap-4 mt-2">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {new Date(entry.createdAt).toLocaleString("en-US", {
                            dateStyle: "short",
                            timeStyle: "short",
                          })}
                        </span>
                        {entry.executionTimeMs && (
                          <span className="text-xs">
                            ⏱️ {entry.executionTimeMs}ms
                          </span>
                        )}
                        <Badge
                          variant={
                            entry.wasSuccessful ? "default" : "destructive"
                          }
                        >
                          {entry.wasSuccessful ? "Success" : "Error"}
                        </Badge>
                      </CardDescription>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        onRepeatSearch(entry.query);
                        onOpenChange(false);
                      }}
                    >
                      Repeat
                    </Button>
                  </div>
                </CardHeader>
                {entry.resultsFound && entry.resultsFound.length > 0 && (
                  <CardContent>
                    <p className="text-sm text-muted-foreground">
                      {entry.resultsFound.length} movie{entry.resultsFound.length !== 1 ? "s" : ""} found
                    </p>
                    {entry.sparqlExecuted && (
                      <details className="mt-2">
                        <summary className="text-xs cursor-pointer text-muted-foreground hover:text-foreground">
                          View SPARQL Query
                        </summary>
                        <pre className="text-xs mt-2 p-2 bg-slate-950 text-slate-50 rounded overflow-x-auto">
                          <code>{entry.sparqlExecuted}</code>
                        </pre>
                      </details>
                    )}
                  </CardContent>
                )}
              </Card>
            ))
          )}
        </div>

        <div className="flex gap-2 pt-4 border-t mt-4">
          <Button
            variant="outline"
            onClick={() => {
              onRefresh();
              toast.success("History refreshed");
            }}
            className="flex-1"
          >
            Refresh
          </Button>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            className="flex-1"
          >
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
