import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  MessageSquare,
  Send,
  Bot,
  User,
  Wrench,
  Loader2,
  AlertCircle,
  HelpCircle,
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

function buildDummyReply(
  question: string,
  prediction: PredictionResult,
): { content: string; toolsUsed: string[] } {
  const pair = `${prediction.drug_a_name} + ${prediction.drug_b_name}`;
  const q = question.toLowerCase();

  if (q.includes("mechanism") || q.includes("biological")) {
    return {
      toolsUsed: ["predict_pair"],
      content:
        `[Demo] For ${pair} in ${prediction.cell_line}, shared pathway edges around DNA damage / repair are highlighted. ` +
        `Class: ${prediction.predicted_class} (p_syn ≈ ${prediction.p_synergy?.toFixed(3) ?? "n/a"}).`,
    };
  }
  if (q.includes("pubmed") || q.includes("paper") || q.includes("literature")) {
    return {
      toolsUsed: ["get_literature"],
      content: `[Demo] Literature preview for ${pair}. Live mode uses PubMed via SynThera tools.`,
    };
  }
  if (q.includes("why not")) {
    return {
      toolsUsed: ["why_not"],
      content: `[Demo] Why-not: alias → filter → graph membership → GNN score → beam comparison for ${prediction.cell_line}.`,
    };
  }
  return {
    toolsUsed: ["predict_pair"],
    content: `[Demo] Assistant for ${pair} @ ${prediction.cell_line}. Ask about mechanism, literature, or why-not.`,
  };
}

function seedMessages(prediction: PredictionResult): Message[] {
  return [
    {
      id: "init-1",
      role: "assistant",
      content: `Research assistant for ${prediction.drug_a_name} × ${prediction.drug_b_name} (${prediction.cell_line}). Ask anything grounded in SynThera tools.`,
      timestamp: now(),
    },
    {
      id: "demo-user-1",
      role: "user",
      content: "What is the biological mechanism of this pair?",
      timestamp: now(),
    },
    {
      id: "demo-assistant-1",
      role: "assistant",
      content: buildDummyReply("biological mechanism", prediction).content,
      toolsUsed: ["predict_pair"],
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

  // Fresh Analysis visit / new pair → offer greeting once (not again after close)
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

  // Auto-dismiss greeting after ~3.5s
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
      .filter((m) => !m.id.startsWith("init") && !m.id.startsWith("demo"))
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
    } catch {
      const dummy = buildDummyReply(text, prediction);
      await new Promise((r) => setTimeout(r, 500));
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: dummy.content,
          toolsUsed: dummy.toolsUsed,
          timestamp: now(),
        },
      ]);
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
      <div className="fixed bottom-5 right-5 z-[60] flex flex-col items-end gap-3 pointer-events-none">
        {showGreeting && (
          <button
            type="button"
            onClick={() => {
              setShowGreeting(false);
              onOpenChange(true);
            }}
            className="pointer-events-auto max-w-[240px] text-left px-4 py-3 rounded-2xl rounded-br-md bg-[#FFFEFB] border border-[#E5E2DC] shadow-[0_8px_28px_rgba(28,36,33,0.10)] text-sm text-[#1C2421] cursor-pointer hover:border-[#2F6B5E]/50 transition-all animate-fade-in"
          >
            <span className="font-semibold text-[#2F6B5E] block text-xs mb-0.5">
              Research Assistant
            </span>
            Hi! How can I help you?
          </button>
        )}
        <button
          type="button"
          onClick={() => {
            setShowGreeting(false);
            onOpenChange(true);
          }}
          className="pointer-events-auto w-14 h-14 rounded-full bg-[#2F6B5E] hover:bg-[#25564B] text-[#FFFEFB] shadow-[0_8px_24px_rgba(47,107,94,0.28)] flex items-center justify-center cursor-pointer transition-transform hover:scale-105"
          title="Open research assistant"
          aria-label="Open research assistant"
        >
          <MessageSquare className="w-5 h-5" />
        </button>
      </div>
    );
  }

  return (
    <aside
      className="shrink-0 flex flex-col border-l border-[#E5E2DC] bg-[#FFFEFB] sticky top-0 relative"
      style={{
        width,
        minHeight: "calc(100vh - 9rem)",
        maxHeight: "calc(100vh - 5.5rem)",
      }}
      aria-label="Research assistant panel"
    >
      {/* Resize handle */}
      <div
        role="separator"
        aria-orientation="vertical"
        title="Drag to resize"
        onMouseDown={() => {
          dragging.current = true;
          document.body.style.cursor = "col-resize";
          document.body.style.userSelect = "none";
        }}
        className="absolute left-0 top-0 bottom-0 w-1.5 -ml-0.5 cursor-col-resize z-10 hover:bg-[#2F6B5E]/40 active:bg-[#2F6B5E]/60"
      />

      {/* Header */}
      <div className="shrink-0 h-12 px-3 border-b border-[#E5E2DC] flex items-center justify-between gap-2 bg-[#F3F1EC]">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-7 h-7 rounded-md bg-[#2F6B5E] text-[#FFFEFB] flex items-center justify-center shrink-0">
            <MessageSquare className="w-3.5 h-3.5" />
          </div>
          <div className="min-w-0">
            <div className="text-xs font-semibold text-[#1C2421] truncate">
              Research Assistant
            </div>
            <div className="text-[10px] font-mono text-[#6B746F] truncate">
              {prediction.drug_a_name} × {prediction.drug_b_name}
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={() => onOpenChange(false)}
          className="p-1.5 rounded-md text-[#6B746F] hover:bg-[#E5E2DC] hover:text-[#1C2421] cursor-pointer"
          title="Close panel"
          aria-label="Close research assistant"
        >
          <PanelRightClose className="w-4 h-4" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3 bg-[#F6F4EF] min-h-0">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-2 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {msg.role === "assistant" && (
              <div className="w-6 h-6 rounded-full bg-[#2F6B5E] text-[#FFFEFB] flex items-center justify-center shrink-0 mt-0.5">
                <Bot className="w-3.5 h-3.5" />
              </div>
            )}
            <div className="max-w-[88%] space-y-1">
              <div
                className={`rounded-xl px-3 py-2 text-xs leading-normal ${
                  msg.role === "user"
                    ? "bg-[#2F6B5E] text-[#FFFEFB] rounded-br-sm"
                    : "bg-[#FFFEFB] text-[#1C2421] border border-[#E5E2DC] rounded-bl-sm"
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
              {msg.toolsUsed && msg.toolsUsed.length > 0 && (
                <div className="flex items-center gap-1 px-1 text-[10px] font-mono text-[#6B746F]">
                  <Wrench className="w-3 h-3 text-[#2F6B5E]" />
                  {msg.toolsUsed.join(", ")}
                </div>
              )}
            </div>
            {msg.role === "user" && (
              <div className="w-6 h-6 rounded-full bg-[#3D4742] text-[#FFFEFB] flex items-center justify-center shrink-0 mt-0.5">
                <User className="w-3.5 h-3.5" />
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="flex items-center gap-2 text-xs text-[#6B746F]">
            <Loader2 className="w-4 h-4 animate-spin text-[#2F6B5E]" />
            Thinking…
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Prompts */}
      <div className="shrink-0 px-3 py-2 border-t border-[#E5E2DC] bg-[#FFFEFB] flex flex-wrap gap-1.5">
        <span className="text-[10px] text-[#8A918C] flex items-center gap-1 w-full">
          <HelpCircle className="w-3 h-3" /> Try
        </span>
        {sampleQuestions.map((q) => (
          <button
            key={q}
            type="button"
            disabled={isLoading}
            onClick={() => handleSendMessage(q)}
            className="text-[10px] bg-[#E8F0ED] border border-[#B5CFC6] text-[#25564B] px-2 py-0.5 rounded-full cursor-pointer disabled:opacity-50 hover:bg-[#D4E5DF]"
          >
            {q.length > 28 ? `${q.slice(0, 26)}…` : q}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="shrink-0 p-2.5 border-t border-[#E5E2DC] bg-[#FFFEFB]">
        {errorMessage && (
          <div className="flex items-center gap-1.5 mb-2 text-[10px] text-[#8B4040]">
            <AlertCircle className="w-3 h-3" />
            <span className="truncate">{errorMessage}</span>
          </div>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="flex items-end gap-1.5"
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
            placeholder="Ask about this pair… (Enter to send)"
            className="flex-1 px-3 py-2 bg-[#F3F1EC] border border-[#E5E2DC] rounded-lg text-xs resize-none focus:outline-none focus:ring-1 focus:ring-[#2F6B5E] focus:border-[#2F6B5E]"
          />
          <button
            type="submit"
            disabled={!inputMessage.trim() || isLoading}
            className="p-2.5 bg-[#2F6B5E] hover:bg-[#25564B] disabled:bg-[#D8D5CE] text-[#FFFEFB] rounded-lg cursor-pointer disabled:cursor-not-allowed"
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
