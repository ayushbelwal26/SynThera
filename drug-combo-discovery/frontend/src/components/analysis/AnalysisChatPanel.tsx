import React, { useState, useRef, useEffect } from 'react';
import { Send, Wrench, Loader2, AlertCircle, CornerDownRight } from 'lucide-react';
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

const SAMPLE_QUESTIONS = [
  'What is the biological mechanism of this combination?',
  'What PubMed literature supports this prediction?',
  'Why not Temozolomide instead?',
  'Search for other synergistic candidates in this cell line.',
];

export const AnalysisChatPanel: React.FC<AnalysisChatPanelProps> = ({ prediction }) => {
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'init-1',
      role: 'assistant',
      content:
        `Research assistant initialized for ${prediction.drug_a_name} + ${prediction.drug_b_name} in ${prediction.cell_line}.\n\n` +
        `I only state facts returned directly by SynThera's prediction, search, why-not, and literature tools. ` +
        `I will not add scientifically plausible but unverified claims.`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (textToSend?: string) => {
    const text = (textToSend ?? inputMessage).trim();
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

    const history = messages
      .filter((m) => m.id !== 'init-1')
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

      setMessages((prev) => [...prev, {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.response,
        toolsUsed: response.tools_used,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }]);
    } catch (err: any) {
      const detail = err?.message || 'Connection failed';
      setErrorMessage(detail);
      setMessages((prev) => [...prev, {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: `Unable to reach analysis service: ${detail}. Ensure OPENROUTER_API_KEY is set in your .env.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
      {/* Context bar */}
      <div style={{
        backgroundColor: 'var(--accent-subtle)',
        border: '1px solid var(--accent-border)',
        borderRadius: 6,
        padding: '8px 12px',
        marginBottom: 14,
        display: 'flex', alignItems: 'center', gap: 8,
        fontSize: 12, fontFamily: 'var(--font-mono)',
        color: 'var(--accent-text)',
      }}>
        <Wrench size={12} />
        <span>Active context: </span>
        <strong>{prediction.drug_a_name} + {prediction.drug_b_name}</strong>
        <span style={{ color: 'var(--accent-border)' }}>·</span>
        <span>{prediction.cell_line}</span>
        <span style={{ color: 'var(--accent-border)' }}>·</span>
        <span style={{ color: 'var(--text-muted)' }}>4 tools: predict_pair, search_combinations, why_not, get_literature</span>
      </div>

      {/* Message list */}
      <div style={{
        maxHeight: 440,
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: 0,
        marginBottom: 12,
      }}>
        {messages.map((msg, i) => (
          <div
            key={msg.id}
            style={{
              display: 'flex',
              flexDirection: 'column',
              borderTop: i > 0 ? '1px solid var(--border)' : undefined,
              padding: '12px 0',
            }}
          >
            {/* Role + timestamp header */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8,
              marginBottom: 6,
              fontSize: 11, fontFamily: 'var(--font-mono)',
              color: 'var(--text-muted)',
            }}>
              <span style={{
                fontWeight: 700,
                color: msg.role === 'assistant' ? 'var(--accent)' : 'var(--text-secondary)',
                textTransform: 'uppercase', letterSpacing: '0.04em',
              }}>
                {msg.role === 'assistant' ? 'SynThera' : 'You'}
              </span>
              <span style={{ color: 'var(--border-strong)' }}>·</span>
              <span>{msg.timestamp}</span>
              {msg.toolsUsed && msg.toolsUsed.length > 0 && (
                <>
                  <span style={{ color: 'var(--border-strong)' }}>·</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Wrench size={10} style={{ color: 'var(--accent)' }} />
                    {msg.toolsUsed.map((t) => (
                      <span key={t} style={{
                        fontSize: 10, fontFamily: 'var(--font-mono)',
                        backgroundColor: 'var(--accent-subtle)',
                        border: '1px solid var(--accent-border)',
                        color: 'var(--accent-text)',
                        borderRadius: 3, padding: '1px 5px',
                      }}>
                        {t}
                      </span>
                    ))}
                  </span>
                </>
              )}
            </div>

            {/* Message body */}
            <p style={{
              fontSize: 13,
              lineHeight: 1.6,
              color: msg.role === 'assistant' ? 'var(--text-primary)' : 'var(--text-secondary)',
              margin: 0,
              whiteSpace: 'pre-wrap',
              paddingLeft: msg.role === 'user' ? 16 : 0,
              borderLeft: msg.role === 'user' ? '2px solid var(--border)' : 'none',
            }}>
              {msg.content}
            </p>
          </div>
        ))}

        {isLoading && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '12px 0',
            borderTop: '1px solid var(--border)',
            fontSize: 12, color: 'var(--text-muted)',
            fontFamily: 'var(--font-mono)',
          }}>
            <Loader2 size={13} className="animate-spin" style={{ color: 'var(--accent)' }} />
            <span>Invoking tools and compiling grounded response…</span>
          </div>
        )}

        <div ref={scrollRef} />
      </div>

      {/* Error */}
      {errorMessage && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '8px 12px', marginBottom: 10,
          backgroundColor: 'var(--error-subtle)',
          border: '1px solid var(--error-border)',
          borderRadius: 6,
          fontSize: 12, color: 'var(--error)',
        }}>
          <AlertCircle size={13} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Quick prompts */}
      <div style={{
        display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10,
      }}>
        {SAMPLE_QUESTIONS.map((q) => (
          <button
            key={q}
            type="button"
            disabled={isLoading}
            onClick={() => handleSend(q)}
            style={{
              fontSize: 11, fontFamily: 'var(--font-sans)',
              padding: '5px 10px',
              backgroundColor: 'var(--surface-subtle)',
              border: '1px solid var(--border)',
              borderRadius: 20,
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              transition: 'border-color 150ms, color 150ms',
              display: 'flex', alignItems: 'center', gap: 4,
            }}
          >
            <CornerDownRight size={10} style={{ color: 'var(--text-muted)' }} />
            {q}
          </button>
        ))}
      </div>

      {/* Input */}
      <form
        onSubmit={(e) => { e.preventDefault(); handleSend(); }}
        style={{ display: 'flex', gap: 8 }}
      >
        <input
          type="text"
          value={inputMessage}
          disabled={isLoading}
          onChange={(e) => setInputMessage(e.target.value)}
          placeholder="Ask about mechanism, literature, or alternative drugs…"
          style={{
            flex: 1,
            padding: '9px 14px',
            fontSize: 13,
            fontFamily: 'var(--font-sans)',
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 6,
            color: 'var(--text-primary)',
            outline: 'none',
            transition: 'border-color 150ms',
          }}
          onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--accent)'; }}
          onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--border)'; }}
        />
        <button
          type="submit"
          disabled={!inputMessage.trim() || isLoading}
          style={{
            padding: '9px 16px',
            backgroundColor: 'var(--accent)',
            border: 'none',
            borderRadius: 6,
            color: '#FFFFFF',
            fontSize: 13,
            fontWeight: 600,
            cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: 6,
            opacity: !inputMessage.trim() || isLoading ? 0.5 : 1,
            transition: 'opacity 150ms',
          }}
        >
          {isLoading ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
          Ask
        </button>
      </form>

      {/* Grounding notice */}
      <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8, lineHeight: 1.5 }}>
        <strong style={{ color: 'var(--text-secondary)' }}>Grounding policy:</strong>{' '}
        This assistant only states facts returned by SynThera tools. No outside biological knowledge is added.
      </p>
    </div>
  );
};
