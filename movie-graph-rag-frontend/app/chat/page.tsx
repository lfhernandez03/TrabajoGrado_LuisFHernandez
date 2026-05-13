"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Loader2, MessageSquare, Plus, Sparkles, Clock } from "lucide-react";
import { Navbar } from "@/components/organisms/Navbar";
import { ProtectedRoute } from "@/components/shared/ProtectedRoute";
import { UserBubble, AssistantBubble, LoadingBubble } from "@/components/chat";
import { ContextChips, type ContextChip } from "@/components/molecules/ContextChips";
import { sendChatConversation, type ChatMessage, type ChatResponse } from "@/services/chat.service";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const QUICK_PROMPTS = [
  { icon: "🎬", text: "Action movie to watch with friends tonight" },
  { icon: "🍿", text: "Something light and fun" },
  { icon: "💕", text: "Romantic movie for couples" },
  { icon: "👨‍👩‍👧", text: "Family-friendly for kids" },
  { icon: "🧠", text: "Makes me think, less than 2 hours" },
  { icon: "😰", text: "I'm stressed, I need to disconnect" },
];

const SESSIONS_KEY = "moviq_sessions";
const ACTIVE_KEY = "moviq_active_session";
const MAX_SESSIONS = 20;

function genId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

interface Session {
  id: string;
  label: string;
  messages: ChatMessage[];
}

function deserializeSessions(raw: string): Session[] {
  try {
    const parsed = JSON.parse(raw) as Session[];
    return parsed.map((s) => ({
      ...s,
      messages: s.messages.map((m) => ({
        ...m,
        timestamp: new Date(m.timestamp),
      })),
    }));
  } catch {
    return [];
  }
}

function readStoredSessions(): Session[] {
  if (typeof window === "undefined") return [];
  const raw = localStorage.getItem(SESSIONS_KEY);
  return raw ? deserializeSessions(raw) : [];
}

function readStoredActiveId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACTIVE_KEY);
}

export default function ChatPage() {
  const [sessions, setSessions] = useState<Session[]>(() => readStoredSessions());
  const [activeId, setActiveId] = useState<string | null>(() => readStoredActiveId());
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const storedSessions = readStoredSessions();
    const storedActiveId = readStoredActiveId();
    const active = storedSessions.find((s) => s.id === storedActiveId);
    return active?.messages ?? [];
  });
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [lastRec, setLastRec] = useState<ChatResponse | null>(() => {
    const storedSessions = readStoredSessions();
    const storedActiveId = readStoredActiveId();
    const active = storedSessions.find((s) => s.id === storedActiveId);
    if (!active) return null;
    const last = active.messages.findLast((m) => m.recommendation);
    return last?.recommendation ?? null;
  });
  const [contextChips, setContextChips] = useState<ContextChip[]>([]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => { scrollBottom(); }, [messages, isLoading, scrollBottom]);

  // ── Persistence ───────────────────────────────────────────────────────────

  useEffect(() => {
    try {
      const trimmed = sessions.slice(0, MAX_SESSIONS);
      localStorage.setItem(SESSIONS_KEY, JSON.stringify(trimmed));
    } catch {
      // Quota exceeded — silently ignore
    }
  }, [sessions]);

  useEffect(() => {
    if (activeId) localStorage.setItem(ACTIVE_KEY, activeId);
    else localStorage.removeItem(ACTIVE_KEY);
  }, [activeId]);

  // ── Session helpers ───────────────────────────────────────────────────────

  const newSession = useCallback(() => {
    const id = genId();
    const session: Session = { id, label: "New conversation", messages: [] };
    setSessions((prev) => [session, ...prev]);
    setActiveId(id);
    setMessages([]);
    setLastRec(null);
    setContextChips([]);
  }, []);

  const switchSession = useCallback((session: Session) => {
    setActiveId(session.id);
    setMessages(session.messages);
    const last = session.messages.findLast((m) => m.recommendation);
    setLastRec(last?.recommendation ?? null);
    setContextChips([]);
  }, []);

  // ── Send ──────────────────────────────────────────────────────────────────

  const handleSend = useCallback(async (text?: string) => {
    const query = (text ?? input).trim();
    if (!query || isLoading) return;

    // Ensure we have an active session
    let sid = activeId;
    let currentMessages = messages;
    if (!sid) {
      const id = genId();
      const session: Session = {
        id,
        label: query.slice(0, 40),
        messages: [],
      };
      setSessions((prev) => [session, ...prev]);
      setActiveId(id);
      sid = id;
      currentMessages = [];
    }

    const userMsg: ChatMessage = {
      id: genId(),
      role: "user",
      content: query,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);
    setTimeout(() => textareaRef.current?.focus(), 0);

    // Build the full message history to send to the backend
    const apiMessages = [
      ...currentMessages.map((m) => ({ role: m.role, content: m.content })),
      { role: "user" as const, content: query },
    ];

    try {
      const rec = await sendChatConversation(sid, apiMessages);
      const assistantMsg: ChatMessage = {
        id: genId(),
        role: "assistant",
        content: rec.explanation,
        timestamp: new Date(),
        recommendation: rec,
      };
      setMessages((prev) => {
        const updated = [...prev, assistantMsg];
        setSessions((sessions) =>
          sessions.map((s) =>
            s.id === sid
              ? { ...s, label: query.slice(0, 40), messages: updated }
              : s
          )
        );
        return updated;
      });
      setLastRec(rec);

      // Extract context chips from flat context_extracted
      const ctx = rec.context_extracted;
      const newChips: ContextChip[] = [];
      if (ctx.mood) {
        newChips.push({ id: genId(), label: ctx.mood, type: "mood" });
      }
      if (ctx.companion) {
        newChips.push({ id: genId(), label: ctx.companion, type: "companion" });
      }
      if (ctx.energy) {
        newChips.push({ id: genId(), label: `Energy ${ctx.energy}`, type: "energy" });
      }
      if (ctx.runtime_max) {
        newChips.push({ id: genId(), label: `${ctx.runtime_max} min`, type: "runtime" });
      }
      setContextChips(newChips);
    } catch {
      const errMsg: ChatMessage = {
        id: genId(),
        role: "assistant",
        content: "Sorry, there was an error processing your query. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errMsg]);
      toast.error("Error getting recommendation");
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, activeId, messages]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const removeChip = (id: string) =>
    setContextChips((prev) => prev.filter((c) => c.id !== id));

  const isEmpty = messages.length === 0;

  // ── Context panel data ────────────────────────────────────────────────────
  const ctx = lastRec?.context_extracted;

  return (
    <ProtectedRoute>
      <div className="flex flex-col h-screen bg-bg">
        <Navbar />

        {/* 3-column layout */}
        <div className="flex flex-1 overflow-hidden">

          {/* ── Left sidebar ─────────────────────────────────────── */}
          <aside className="hidden lg:flex flex-col w-65 shrink-0 border-r border-border bg-surface overflow-y-auto">
            <div className="p-4 border-b border-border">
              <button
                type="button"
                onClick={newSession}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-surface2 border border-border text-sm text-text hover:border-accent/40 hover:text-accent transition-all"
              >
                <Plus className="w-4 h-4" />
                New conversation
              </button>
            </div>

            {/* Session list */}
            <div className="flex-1 p-2 flex flex-col gap-1">
              {sessions.length === 0 ? (
                <p className="text-xs text-muted text-center py-8">
                  Your conversations will appear here
                </p>
              ) : (
                sessions.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => switchSession(s)}
                    className={cn(
                      "w-full text-left px-3 py-2 rounded-lg text-sm truncate transition-colors",
                      activeId === s.id
                        ? "bg-surface2 text-text border border-border2"
                        : "text-muted hover:bg-surface2/60 hover:text-text"
                    )}
                  >
                    <MessageSquare className="w-3.5 h-3.5 inline mr-2 opacity-60" />
                    {s.label}
                  </button>
                ))
              )}
            </div>

            {/* Quick prompts */}
            <div className="p-3 border-t border-border">
              <p className="text-[10px] font-semibold text-muted uppercase tracking-wider mb-2">
                Quick suggestions
              </p>
              <div className="flex flex-col gap-1">
                {QUICK_PROMPTS.slice(0, 4).map((p) => (
                  <button
                    key={p.text}
                    type="button"
                    onClick={() => handleSend(p.text)}
                    disabled={isLoading}
                    className="flex items-center gap-2 px-2 py-1.5 rounded text-xs text-muted hover:text-text hover:bg-surface2 transition-colors disabled:opacity-40 text-left"
                  >
                    <span>{p.icon}</span>
                    <span className="line-clamp-1">{p.text}</span>
                  </button>
                ))}
              </div>
            </div>
          </aside>

          {/* ── Center: chat ──────────────────────────────────────── */}
          <div className="flex flex-col flex-1 min-w-0">
            {/* Messages area */}
            <div className="flex-1 overflow-y-auto px-6 py-6">
              <div className="max-w-3xl mx-auto space-y-6">

                {/* Empty state */}
                {isEmpty && !isLoading && (
                  <div className="flex flex-col items-center justify-center text-center py-20">
                    <div className="w-16 h-16 rounded-full bg-teal/10 flex items-center justify-center mb-4">
                      <span className="text-2xl text-teal">✦</span>
                    </div>
                    <h2 className="font-display text-3xl text-text mb-2">What do you want to watch today?</h2>
                    <p className="text-sm text-muted max-w-sm mb-8">
                      Tell me your mood, who you're with, how much time you have.
                      The graph will find your perfect movie.
                    </p>
                    {/* Quick chips on empty state */}
                    <div className="flex flex-wrap gap-2 justify-center">
                      {QUICK_PROMPTS.map((p) => (
                        <button
                          key={p.text}
                          type="button"
                          onClick={() => handleSend(p.text)}
                          disabled={isLoading}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border bg-surface2 text-xs text-muted hover:border-teal/40 hover:text-text transition-all disabled:opacity-40"
                        >
                          <span>{p.icon}</span>
                          {p.text}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Messages */}
                {messages.map((msg) =>
                  msg.role === "user" ? (
                    <UserBubble key={msg.id} message={msg} />
                  ) : (
                    <AssistantBubble key={msg.id} message={msg} />
                  )
                )}
                {isLoading && <LoadingBubble />}
                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Input area */}
            <div className="border-t border-border bg-surface px-6 py-4">
              <div className="max-w-3xl mx-auto flex flex-col gap-2">
                {/* Context chips */}
                {contextChips.length > 0 && (
                  <ContextChips chips={contextChips} onRemove={removeChip} removable />
                )}

                <div className="flex items-end gap-3">
                  <textarea
                    ref={textareaRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Describe what kind of movie you're looking for…"
                    disabled={isLoading}
                    rows={1}
                    className={cn(
                      "flex-1 resize-none rounded-xl px-4 py-3 text-sm",
                      "bg-surface2 text-text border border-border",
                      "placeholder:text-muted",
                      "focus:outline-none focus:border-accent2 focus:ring-1 focus:ring-accent2/20",
                      "disabled:opacity-50 disabled:cursor-not-allowed",
                      "min-h-11 max-h-36 field-sizing-content"
                    )}
                  />
                  <button
                    type="button"
                    onClick={() => handleSend()}
                    disabled={!input.trim() || isLoading}
                    className={cn(
                      "w-11 h-11 rounded-xl shrink-0 flex items-center justify-center",
                      "bg-accent2 text-bg",
                      "hover:bg-accent2/90 transition-colors",
                      "disabled:opacity-40 disabled:cursor-not-allowed"
                    )}
                    aria-label="Enviar"
                  >
                    {isLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* ── Right panel: context ──────────────────────────────── */}
          <aside className="hidden xl:flex flex-col w-65 shrink-0 border-l border-border bg-surface overflow-y-auto">
            <div className="p-4 border-b border-border">
              <p className="text-xs font-semibold text-muted uppercase tracking-wider">
                Extracted context
              </p>
            </div>

            {lastRec ? (
              <div className="p-4 flex flex-col gap-4 text-xs">
                {/* Emotional context */}
                {(ctx?.mood || ctx?.energy) && (
                  <ContextPanel label="Emotional state">
                    {ctx.mood && <Row label="Mood" value={ctx.mood} />}
                    {ctx.energy && <Row label="Energy" value={ctx.energy} />}
                  </ContextPanel>
                )}

                {/* Social context */}
                {ctx?.companion && (
                  <ContextPanel label="Social context">
                    <Row label="Companion" value={ctx.companion} />
                    {ctx.has_children && <Row label="Children" value="Yes" />}
                  </ContextPanel>
                )}

                {/* Preferences */}
                {(ctx?.genres?.length || ctx?.runtime_max || ctx?.exclusions?.length) ? (
                  <ContextPanel label="Preferences">
                    {ctx.genres && ctx.genres.length > 0 && (
                      <Row label="Genres" value={ctx.genres.join(", ")} />
                    )}
                    {ctx.runtime_max && (
                      <Row label="Max runtime" value={`${ctx.runtime_max} min`} />
                    )}
                    {ctx.exclusions && ctx.exclusions.length > 0 && (
                      <Row label="Exclude" value={ctx.exclusions.join(", ")} />
                    )}
                  </ContextPanel>
                ) : null}

                {/* Metrics */}
                <ContextPanel label="Metrics">
                  <Row label="Movies" value={String(lastRec.movies.length)} />
                  <Row label="Time" value={`${lastRec.execution_ms}ms`} />
                  <Row label="Turn" value={String(lastRec.turn_count)} />
                  {lastRec.strategy_used && (
                    <Row label="Strategy" value={lastRec.strategy_used} />
                  )}
                  {ctx?.confidence !== undefined && (
                    <Row label="Confidence" value={`${Math.round(ctx.confidence * 100)}%`} />
                  )}
                </ContextPanel>

                {/* Strategy indicator */}
                <div className="flex items-center gap-1.5 text-teal">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span className="font-medium">GraphRAG active</span>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center flex-1 text-center p-6">
                <Clock className="w-8 h-8 text-muted/30 mb-2" />
                <p className="text-xs text-muted">
                  The context extracted from your query will appear here.
                </p>
              </div>
            )}
          </aside>

        </div>
      </div>
    </ProtectedRoute>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function ContextPanel({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="font-semibold text-muted uppercase tracking-wider text-[10px]">{label}</p>
      <div className="flex flex-col gap-1">{children}</div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2">
      <span className="text-muted">{label}</span>
      <span className="text-text font-medium text-right">{value}</span>
    </div>
  );
}
