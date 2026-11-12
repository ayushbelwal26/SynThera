import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  MessageSquare,
  Send,
  Loader2,
  AlertCircle,
  PanelRightClose,
  Sparkles,
} from "lucide-react";
import { sendAnalysisChatMessage } from "../../services/api";
import type { PredictionResult } from "../../types/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolsUsed?: string[];
  timestamp: string;
}

interface AnalysisChatPanelProps {
  prediction: PredictionResult;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  width: number;
  onWidthChange: (w: number) => void;
}

const MIN_W = 300;
const MAX_W = 520;

const now = () =>
  new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

function seedMessages(prediction: PredictionResult): Message[] {
  return [
    {
      id: "init-1",
      role: "assistant",
      content: `Context: ${prediction.drug_a_name} × ${prediction.drug_b_name} (${prediction.cell_line}). Ask questions regarding mechanistic pathways, PubMed literature grounding, or toxicity penalties.`,
      timestamp: now(),
    },
  ];
}

export const AnalysisChatPanel: React.FC<AnalysisChatPanelProps> = ({
  prediction,
  isOpen,
  onOpenChange,
  width,
  onWidthChange,
}) => {
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>(() =>
    seedMessages(prediction),
  );
  const [showGreeting, setShowGreeting] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);
  const greetingShownFor = useRef<string>("");

  const predictionKey = `${prediction.drug_a}|${prediction.drug_b}|${prediction.cell_line}`;

  useEffect(() => {
    setMessages(seedMessages(prediction));
    setErrorMessage(null);
    if (greetingShownFor.current !== predictionKey) {
      greetingShownFor.current = predictionKey;
      setShowGreeting(true);
    }
  }, [
    prediction.drug_a,
    prediction.drug_b,
    prediction.cell_line,
    predictionKey,
  ]);

  useEffect(() => {
    if (!showGreeting || isOpen) return;
    const t = window.setTimeout(() => setShowGreeting(false), 3500);
    return () => window.clearTimeout(t);
  }, [showGreeting, isOpen, predictionKey]);

  useEffect(() => {
    if (isOpen) {
      setShowGreeting(false);
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isOpen, isLoading]);

  const onResizeMove = useCallback(
    (e: MouseEvent) => {
      if (!dragging.current) return;
      const next = window.innerWidth - e.clientX;
      onWidthChange(Math.min(MAX_W, Math.max(MIN_W, next)));
    },
    [onWidthChange],
  );

  const onResizeUp = useCallback(() => {
    dragging.current = false;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }, []);

  useEffect(() => {
    window.addEventListener("mousemove", onResizeMove);
    window.addEventListener("mouseup", onResizeUp);
    return () => {
      window.removeEventListener("mousemove", onResizeMove);
      window.removeEventListener("mouseup", onResizeUp);
    };
  }, [onResizeMove, onResizeUp]);

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputMessage).trim();
    if (!text || isLoading) return;

    setMessages((prev) => [
      ...prev,
      {
        id: `user-${Date.now()}`,
        role: "user",
        content: text,
        timestamp: now(),
      },
    ]);
    setInputMessage("");
    setIsLoading(true);
    setErrorMessage(null);

    const history = messages
      .filter((m) => !m.id.startsWith("init"))
      .map((m) => ({ role: m.role, content: m.content }));

    try {
      const response = await sendAnalysisChatMessage({
        message: text,
        conversation_history: history,
        context: {
          drug_a: prediction.drug_a_name || prediction.drug_a,
          drug_b: prediction.drug_b_name || prediction.drug_b,
          cell_line: prediction.cell_line,
        },
      });
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: response.response,
          toolsUsed: response.tools_used,
          timestamp: now(),
        },
      ]);
    } catch (err: unknown) {
      console.error("Chat error:", err);
      setErrorMessage(
        (err as Error)?.message ||
          "Failed to communicate with research assistant",
      );
    } finally {
      setIsLoading(false);
    }
  };

  const sampleQuestions = [
    "What is the biological mechanism of this pair?",
    "Are there PubMed papers supporting this?",
    "Why not Temozolomide?",
  ];

  if (!isOpen) {
    return (
      <div className="fixed bottom-6 right-6 z-[60] flex flex-col items-end gap-2 pointer-events-none">
        {showGreeting && (
          <button
            type="button"
            onClick={() => {
              setShowGreeting(false);
              onOpenChange(true);
            }}
            className="pointer-events-auto max-w-[240px] text-left p-3 rounded-lg bg-[var(--color-surface)] border border-[var(--color-rule-strong)] shadow-[0_4px_20px_rgba(0,0,0,0.15)] text-[12.5px] text-[var(--color-text-primary)] cursor-pointer hover:border-[var(--color-accent)] transition-all animate-bounce"
          >
            <div className="flex items-center gap-1.5 text-[var(--color-accent)] font-mono text-[10px] font-bold uppercase mb-1">
              <Sparkles size={11} />
              <span>Ask this record</span>
            </div>
            Ask about mechanism, literature, or toxicity penalties
          </button>
        )}
        <button
          type="button"
          onClick={() => {
            setShowGreeting(false);
            onOpenChange(true);
          }}
          className="pointer-events-auto w-12 h-12 rounded-full border border-[var(--color-accent)] bg-[var(--color-accent)] text-[#041A1E] flex items-center justify-center cursor-pointer shadow-[0_0_20px_var(--color-accent-glow)] hover:scale-105 transition-all"
          title="Open assistant"
          aria-label="Open assistant"
        >
          <MessageSquare className="w-5 h-5" />
        </button>
      </div>
    );
  }

  return (
    <aside
      className="shrink-0 flex flex-col border-l border-[var(--color-rule)] bg-[var(--color-panel)] sticky top-0 relative shadow-2xl backdrop-blur-md"
      style={{
        width,
        minHeight: "calc(100vh - 9rem)",
        maxHeight: "calc(100vh - 5.5rem)",
      }}
      aria-label="Research assistant panel"
    >
      <div
        role="separator"
        aria-orientation="vertical"
        title="Drag to resize"
        onMouseDown={() => {
          dragging.current = true;
          document.body.style.cursor = "col-resize";
          document.body.style.userSelect = "none";
        }}
        className="absolute left-0 top-0 bottom-0 w-2 -ml-1 cursor-col-resize z-10 hover:bg-[var(--color-accent)]/30 active:bg-[var(--color-accent)]/60"
      />

      {/* Header */}
      <div className="shrink-0 h-12 px-4 border-b border-[var(--color-rule)] flex items-center justify-between gap-2 bg-[var(--color-surface)]">
        <div className="min-w-0">
          <div className="text-[13.5px] font-semibold text-[var(--color-text-primary)] flex items-center gap-1.5 truncate">
            <Sparkles size={13} className="text-[var(--color-accent)]" />
            <span>Research Assistant</span>
          </div>
          <div className="id-text truncate text-[11px] text-[var(--color-text-muted)]">
            {prediction.drug_a_name} × {prediction.drug_b_name}
          </div>
        </div>
        <button
          type="button"
          onClick={() => onOpenChange(false)}
          className="p-1.5 rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-accent)] hover:bg-[var(--color-accent-soft)] cursor-pointer transition-colors"
          title="Close panel"
          aria-label="Close research assistant"
        >
          <PanelRightClose className="w-4 h-4" />
        </button>
      </div>

      {/* Message history */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3.5 min-h-0">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`${msg.role === "user" ? "pl-4" : "pr-2"}`}
          >
            <div className="flex items-baseline justify-between gap-2 mb-1">
              <span className="font-mono text-[10.5px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">
                {msg.role === "user" ? "You" : "SynThera Assistant"}
              </span>
              <span className="id-text text-[10px]">{msg.timestamp}</span>
            </div>
            <p
              className={`text-[13px] leading-relaxed whitespace-pre-wrap ${
                msg.role === "user"
                  ? "text-[var(--color-text-primary)] border-l-2 border-[var(--color-accent)] pl-2.5 bg-[var(--color-accent-soft)]/20 py-1 rounded-r"
                  : "text-[var(--color-text-secondary)]"
              }`}
            >
              {msg.content}
            </p>
            {msg.toolsUsed && msg.toolsUsed.length > 0 && (
              <p className="font-mono text-[10px] text-[var(--color-accent)] mt-1">
                Tools: {msg.toolsUsed.join(", ")}
              </p>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="flex items-center gap-2 text-[12px] font-mono text-[var(--color-text-muted)]">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-[var(--color-accent)]" />
            <span>Reasoning over PrimeKG…</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggestions */}
      <div className="shrink-0 px-4 py-2 border-t border-[var(--color-rule)] flex flex-wrap gap-x-3 gap-y-1 bg-[var(--color-surface)]">
        <span className="bench-label w-full text-[10px]">Prompt Ideas</span>
        {sampleQuestions.map((q) => (
          <button
            key={q}
            type="button"
            disabled={isLoading}
            onClick={() => handleSendMessage(q)}
            className="text-[11.5px] font-mono text-[var(--color-accent)] hover:underline cursor-pointer disabled:opacity-50 text-left"
          >
            {q.length > 34 ? `${q.slice(0, 32)}…` : q}
          </button>
        ))}
      </div>

      {/* Input row */}
      <div className="shrink-0 p-3 border-t border-[var(--color-rule)] bg-[var(--color-panel)]">
        {errorMessage && (
          <div className="flex items-start gap-1.5 mb-2 text-[12px] text-[var(--color-antagonism)] font-mono">
            <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
            <span className="break-words">{errorMessage}</span>
          </div>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="flex items-end gap-2"
        >
          <textarea
            value={inputMessage}
            disabled={isLoading}
            rows={2}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
            placeholder="Ask about mechanisms or literature…"
            className="flex-1 px-2.5 py-1.5 rounded-md bg-[var(--color-surface)] border border-[var(--color-rule)] text-[13px] text-[var(--color-text-primary)] resize-none focus:outline-none focus:border-[var(--color-accent)] focus:shadow-[0_0_10px_var(--color-accent-glow)] font-sans"
          />
          <button
            type="submit"
            disabled={!inputMessage.trim() || isLoading}
            className="bench-btn !p-2 shrink-0 rounded-md"
            aria-label="Send"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </form>
      </div>
    </aside>
  );
};
