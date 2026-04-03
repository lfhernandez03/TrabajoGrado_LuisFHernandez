"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Loader2, MessageSquare, Plus, Sparkles, Clock } from "lucide-react";
import { Navbar } from "@/components/organisms/Navbar";
import { ProtectedRoute } from "@/components/shared/ProtectedRoute";
import { UserBubble, AssistantBubble, LoadingBubble } from "@/components/chat";
import { ContextChips, type ContextChip } from "@/components/molecules/ContextChips";
import { sendChatMessage, type ChatMessage, type ChatRecommendationResponse } from "@/services/chat.service";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const QUICK_PROMPTS = [
  { icon: "🎬", text: "Acción para ver con amigos esta noche" },
  { icon: "🍿", text: "Algo ligero y divertido" },
  { icon: "💕", text: "Romántica para ver en pareja" },
  { icon: "👨‍👩‍👧", text: "Familiar apta para niños" },
  { icon: "🧠", text: "Que me haga pensar, menos de 2 horas" },
  { icon: "😰", text: "Estoy estresado, necesito desconectarme" },
];

function genId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

interface Session {
  id: string;
  label: string;
  messages: ChatMessage[];
}

export default function ChatPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [lastRec, setLastRec] = useState<ChatRecommendationResponse | null>(null);
  const [contextChips, setContextChips] = useState<ContextChip[]>([]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => { scrollBottom(); }, [messages, isLoading, scrollBottom]);

  // ── Session helpers ───────────────────────────────────────────────────────

  const newSession = useCallback(() => {
    const id = genId();
    const session: Session = { id, label: "Nueva conversación", messages: [] };
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

    try {
      const rec = await sendChatMessage(query);
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

      // Extract context chips from response
      const ctx = rec.contextExtracted as Record<string, unknown> | undefined;
      const newChips: ContextChip[] = [];
      const emotional = ctx?.emotionalContext as Record<string, string> | undefined;
      const social = ctx?.socialContext as Record<string, unknown> | undefined;
      const requirement = ctx?.requirementContext as Record<string, unknown> | undefined;

      if (emotional?.moodDescription) {
        newChips.push({ id: genId(), label: emotional.moodDescription, type: "mood" });
      }
      if (social?.companionType && typeof social.companionType === "string") {
        newChips.push({ id: genId(), label: social.companionType, type: "companion" });
      }
      if (emotional?.desiredEnergyLevel) {
        newChips.push({ id: genId(), label: `Energía ${emotional.desiredEnergyLevel}`, type: "energy" });
      }
      if (requirement?.availableTime && typeof requirement.availableTime === "number") {
        newChips.push({ id: genId(), label: `${requirement.availableTime} min`, type: "runtime" });
      }
      setContextChips(newChips);
    } catch {
      const errMsg: ChatMessage = {
        id: genId(),
        role: "assistant",
        content: "Lo siento, hubo un error al procesar tu consulta. Por favor, intenta de nuevo.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errMsg]);
      toast.error("Error al obtener recomendación");
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, activeId]);

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
  const ctx = lastRec?.contextExtracted as Record<string, unknown> | undefined;
  const emotional = ctx?.emotionalContext as Record<string, string> | undefined;
  const social = ctx?.socialContext as Record<string, unknown> | undefined;

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
                Nueva conversación
              </button>
            </div>

            {/* Session list */}
            <div className="flex-1 p-2 flex flex-col gap-1">
              {sessions.length === 0 ? (
                <p className="text-xs text-muted text-center py-8">
                  Tus conversaciones aparecerán aquí
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
                Sugerencias rápidas
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
                    <h2 className="font-display text-3xl text-text mb-2">¿Qué quieres ver hoy?</h2>
                    <p className="text-sm text-muted max-w-sm mb-8">
                      Cuéntame tu estado de ánimo, con quién estás, cuánto tiempo tienes.
                      El grafo encontrará tu película perfecta.
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
                    placeholder="Describe qué tipo de película buscas…"
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
                Contexto extraído
              </p>
            </div>

            {lastRec ? (
              <div className="p-4 flex flex-col gap-4 text-xs">
                {/* Emotional context */}
                {emotional && (
                  <ContextPanel label="Estado emocional">
                    {emotional.moodDescription && (
                      <Row label="Mood" value={emotional.moodDescription} />
                    )}
                    {emotional.desiredEnergyLevel && (
                      <Row label="Energía" value={emotional.desiredEnergyLevel} />
                    )}
                  </ContextPanel>
                )}

                {/* Social context */}
                {social && (
                  <ContextPanel label="Contexto social">
                    {typeof social.companionType === "string" && (
                      <Row label="Compañía" value={social.companionType} />
                    )}
                  </ContextPanel>
                )}

                {/* Metrics */}
                {lastRec.moviesFound !== undefined && (
                  <ContextPanel label="Métricas">
                    <Row label="Películas" value={String(lastRec.moviesFound)} />
                    <Row label="Tiempo" value={`${lastRec.executionTimeMs}ms`} />
                  </ContextPanel>
                )}

                {/* Strategy indicator */}
                <div className="flex items-center gap-1.5 text-teal">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span className="font-medium">GraphRAG activo</span>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center flex-1 text-center p-6">
                <Clock className="w-8 h-8 text-muted/30 mb-2" />
                <p className="text-xs text-muted">
                  El contexto extraído de tu consulta aparecerá aquí.
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
