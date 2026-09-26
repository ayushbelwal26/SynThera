import React, { useState, useRef, useEffect } from 'react';
import {
  MessageSquare,
  ChevronDown,
  ChevronUp,
  Send,
  Bot,
  User,
  Wrench,
  Loader2,
  AlertCircle,
  HelpCircle,
} from 'lucide-react';
import { sendAnalysisChatMessage } from '../../services/api';
import type { PredictionResult } from '../../types/api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolsUsed?: string[];
  timestamp: string;
}

interface AnalysisChatPanelProps {
  prediction: PredictionResult;
}

export const AnalysisChatPanel: React.FC<AnalysisChatPanelProps> = ({ prediction }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'init-1',
      role: 'assistant',
      content:
        `Hello! I am your grounded research assistant for ${prediction.drug_a_name} + ${prediction.drug_b_name} in ${prediction.cell_line}. ` +
        `I only state facts that come directly from SynThera's tools (predict_pair, search_combinations, why_not, get_literature). ` +
        `Ask me about this pair's mechanism, supporting literature, or why another drug was excluded.`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputMessage).trim();
    if (!text || isLoading) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');
    setIsLoading(true);
    setErrorMessage(null);

    // Build conversation history for API
    const history = messages
      .filter((m) => m.id !== 'init-1')
      .map((m) => ({
        role: m.role,
        content: m.content,
      }));

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

      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.response,
        toolsUsed: response.tools_used,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      console.error('Chat error:', err);
      const detail = err?.message || 'Failed to communicate with research assistant';
      setErrorMessage(detail);
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: `Error: ${detail}. If OPENROUTER_API_KEY is not configured, please set it in your .env configuration.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const sampleQuestions = [
    `What is the biological mechanism of this pair?`,
    `Are there PubMed papers supporting this?`,
    `Why not Temozolomide?`,
  ];

  return (
    <div className="bg-[#FFFFFF] border border-[#E2E8F0] rounded-xl shadow-xs overflow-hidden transition-all duration-300">
      {/* Collapsible Header */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-5 py-4 flex items-center justify-between bg-gradient-to-r from-[#F8FAFC] to-[#F1F5F9] hover:from-[#F1F5F9] hover:to-[#E2E8F0] transition-colors cursor-pointer text-left"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#0D9488]/10 text-[#0D9488] flex items-center justify-center font-bold">
            <MessageSquare className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-semibold text-[#0F172A]">
                SynThera Research Assistant
              </h4>
              <span className="px-2 py-0.5 text-[10px] font-mono font-medium rounded-full bg-[#E0F2FE] text-[#0369A1] border border-[#BAE6FD]">
                Grounded Tool Calling
              </span>
            </div>
            <p className="text-xs text-[#64748B] mt-0.5">
              Active Context: <span className="font-medium text-[#334155]">{prediction.drug_a_name} + {prediction.drug_b_name}</span> &bull; <span className="font-mono text-[#64748B]">{prediction.cell_line}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-semibold text-[#475569]">
          <span>{isOpen ? 'Collapse Chat' : 'Open Grounded Chat'}</span>
          {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {/* Expanded Panel */}
      {isOpen && (
        <div className="border-t border-[#E2E8F0] flex flex-col bg-[#F8FAFC]">
          {/* Messages Container */}
          <div className="p-4 sm:p-5 max-h-[460px] overflow-y-auto space-y-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 ${
                  msg.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {msg.role === 'assistant' && (
                  <div className="w-7 h-7 rounded-full bg-[#0D9488] text-white flex items-center justify-center shrink-0 mt-0.5 shadow-xs">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div className={`max-w-[85%] space-y-1.5 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                  <div
                    className={`rounded-xl px-4 py-3 text-xs leading-relaxed ${
                      msg.role === 'user'
                        ? 'bg-[#0D9488] text-white shadow-xs rounded-tr-none'
                        : 'bg-white text-[#1E293B] border border-[#E2E8F0] shadow-xs rounded-tl-none'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </div>

                  {/* Grounded Tool Usage Tag */}
                  {msg.role === 'assistant' && msg.toolsUsed && msg.toolsUsed.length > 0 && (
                    <div className="flex items-center gap-1.5 px-1 text-[11px] font-mono text-[#64748B]">
                      <Wrench className="w-3 h-3 text-[#0D9488]" />
                      <span>used:</span>
                      <div className="flex flex-wrap gap-1">
                        {msg.toolsUsed.map((tool) => (
                          <span
                            key={tool}
                            className="px-1.5 py-0.2 bg-[#F1F5F9] border border-[#CBD5E1] rounded text-[#334155] font-semibold"
                          >
                            {tool}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <span className="block text-[10px] text-[#94A3B8] px-1">
                    {msg.timestamp}
                  </span>
                </div>

                {msg.role === 'user' && (
                  <div className="w-7 h-7 rounded-full bg-[#334155] text-white flex items-center justify-center shrink-0 mt-0.5 shadow-xs">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-3 justify-start items-center text-xs text-[#64748B]">
                <div className="w-7 h-7 rounded-full bg-[#0D9488]/20 text-[#0D9488] flex items-center justify-center shrink-0">
                  <Loader2 className="w-4 h-4 animate-spin" />
                </div>
                <div className="bg-white border border-[#E2E8F0] rounded-xl px-4 py-2.5 shadow-xs flex items-center gap-2">
                  <span className="inline-block w-2 h-2 rounded-full bg-[#0D9488] animate-pulse" />
                  <span>Evaluating tools & compiling grounded response...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick Suggestion Chips */}
          <div className="px-4 py-2 bg-[#F1F5F9] border-t border-[#E2E8F0] flex flex-wrap items-center gap-2">
            <span className="text-[11px] font-semibold text-[#64748B] flex items-center gap-1">
              <HelpCircle className="w-3 h-3" /> Prompts:
            </span>
            {sampleQuestions.map((q) => (
              <button
                key={q}
                type="button"
                disabled={isLoading}
                onClick={() => handleSendMessage(q)}
                className="text-[11px] bg-white border border-[#CBD5E1] hover:border-[#0D9488] hover:text-[#0D9488] text-[#334155] px-2.5 py-1 rounded-full transition-colors cursor-pointer disabled:opacity-50"
              >
                {q}
              </button>
            ))}
          </div>

          {/* Input Box */}
          <div className="p-3 sm:p-4 bg-white border-t border-[#E2E8F0] space-y-2">
            {errorMessage && (
              <div className="flex items-center gap-2 p-2 bg-[#FEF2F2] border border-[#FECACA] rounded-lg text-xs text-[#991B1B]">
                <AlertCircle className="w-4 h-4 shrink-0 text-[#EF4444]" />
                <span className="truncate">{errorMessage}</span>
              </div>
            )}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                value={inputMessage}
                disabled={isLoading}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Ask about this pair's mechanism, literature evidence, or why a drug was excluded..."
                className="flex-1 px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg text-xs text-[#0F172A] placeholder-[#94A3B8] focus:outline-none focus:ring-1 focus:ring-[#0D9488] focus:border-[#0D9488] transition-all"
              />
              <button
                type="submit"
                disabled={!inputMessage.trim() || isLoading}
                className="px-4 py-2.5 bg-[#0D9488] hover:bg-[#0F766E] disabled:bg-[#CBD5E1] text-white rounded-lg font-semibold text-xs flex items-center gap-1.5 transition-colors cursor-pointer disabled:cursor-not-allowed shadow-xs"
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <Send className="w-3.5 h-3.5" />
                    <span>Send</span>
                  </>
                )}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
