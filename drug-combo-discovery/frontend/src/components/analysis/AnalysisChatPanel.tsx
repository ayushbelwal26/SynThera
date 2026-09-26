import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  MessageSquare,
  Send,
  Loader2,
  AlertCircle,
  PanelRightClose,
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
      content: `Context: ${prediction.drug_a_name} × ${prediction.drug_b_name} (${prediction.cell_line}). Questions are answered with SynThera tools.`,
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
      <div className="fixed bottom-5 right-5 z-[60] flex flex-col items-end gap-2 pointer-events-none">
        {showGreeting && (
          <button
            type="button"
            onClick={() => {
              setShowGreeting(false);
              onOpenChange(true);
            }}
            className="pointer-events-auto max-w-[220px] text-left px-3 py-2.5 bg-[#F5F5ED] border border-[#CFC9BC] text-[13px] text-[#1A1F1C] cursor-pointer hover:border-[#1A535C]"
          >
            <span className="bench-label block mb-0.5">Ask this record</span>
            Mechanism, literature, or ranking
          </button>
        )}
        <button
          type="button"
          onClick={() => {
            setShowGreeting(false);
            onOpenChange(true);
          }}
          className="pointer-events-auto w-10 h-10 border border-[#1A1F1C] bg-[#1A1F1C] text-[#F5F5ED] flex items-center justify-center cursor-pointer hover:bg-[#1A535C] hover:border-[#1A535C]"
          title="Open assistant"
          aria-label="Open assistant"
        >
          <MessageSquare className="w-4 h-4" />
        </button>
      </div>
    );
  }

  return (
    <aside
      className="shrink-0 flex flex-col border-l border-[#CFC9BC] bg-[#FFFEF8] sticky top-0 relative"
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
        className="absolute left-0 top-0 bottom-0 w-1.5 -ml-0.5 cursor-col-resize z-10 hover:bg-[#1A535C]/30 active:bg-[#1A535C]/50"
      />

      <div className="shrink-0 h-11 px-3 border-b border-[#CFC9BC] flex items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="text-[13px] font-medium text-[#1A1F1C] truncate">
            Research assistant
          </div>
          <div className="id-text truncate">
            {prediction.drug_a_name} × {prediction.drug_b_name}
          </div>
        </div>
        <button
          type="button"
          onClick={() => onOpenChange(false)}
          className="p-1.5 text-[#6B746C] hover:text-[#1A1F1C] cursor-pointer"
          title="Close panel"
          aria-label="Close research assistant"
        >
          <PanelRightClose className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3 min-h-0">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`${msg.role === "user" ? "pl-4" : "pr-2"}`}
          >
            <div className="flex items-baseline justify-between gap-2 mb-0.5">
              <span className="bench-label">
                {msg.role === "user" ? "You" : "Assistant"}
              </span>
              <span className="id-text">{msg.timestamp}</span>
            </div>
            <p
              className={`text-[13px] leading-relaxed whitespace-pre-wrap ${
                msg.role === "user"
                  ? "text-[#1A1F1C] border-l-2 border-[#1A535C] pl-2"
                  : "text-[#4A524C]"
              }`}
            >
              {msg.content}
            </p>
            {msg.toolsUsed && msg.toolsUsed.length > 0 && (
              <p className="id-text mt-1">{msg.toolsUsed.join(", ")}</p>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="flex items-center gap-2 text-[12px] text-[#6B746C]">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-[#1A535C]" />
            Working…
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="shrink-0 px-3 py-2 border-t border-[#CFC9BC] flex flex-wrap gap-x-3 gap-y-1">
        <span className="bench-label w-full">Try</span>
        {sampleQuestions.map((q) => (
          <button
            key={q}
            type="button"
            disabled={isLoading}
            onClick={() => handleSendMessage(q)}
            className="text-[12px] text-[#1A535C] underline underline-offset-2 decoration-[#CFC9BC] hover:decoration-[#1A535C] cursor-pointer disabled:opacity-50"
          >
            {q.length > 32 ? `${q.slice(0, 30)}…` : q}
          </button>
        ))}
      </div>

      <div className="shrink-0 p-2.5 border-t border-[#CFC9BC]">
        {errorMessage && (
          <div className="flex items-start gap-1.5 mb-2 text-[12px] text-[#A84B4B]">
            <AlertCircle className="w-3 h-3 mt-0.5 shrink-0" />
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
            placeholder="Ask about this pair…"
            className="flex-1 px-0 py-1.5 bg-transparent border-0 border-b border-[#CFC9BC] text-[13px] resize-none focus:outline-none focus:border-[#1A535C]"
          />
          <button
            type="submit"
            disabled={!inputMessage.trim() || isLoading}
            className="bench-btn !px-2.5 !py-2 shrink-0"
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
