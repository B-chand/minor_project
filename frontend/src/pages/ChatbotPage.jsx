import React, { useEffect, useRef, useState } from 'react';
import {
  Bot,
  Send,
  Sparkles,
  RefreshCw,
  Trash2,
  AlertCircle,
  User as UserIcon,
} from 'lucide-react';
import { sendChatMessage, getChatErrorMessage } from '../services/chatbotService';
import { useNotification } from '../context/NotificationContext';

const WELCOME_MESSAGE =
  "Hi! I'm the AI Chat assistant for INVENTO, a smart multi-tenant inventory management system. I can help you with products, inventory, sales, purchases, customers, suppliers, and business operations.";

const SUGGESTIONS = [
  'Which products are low in stock right now?',
  'How much revenue did I generate recently?',
  'Who are my top customers?',
  'Summarize my current inventory.',
];

const newId = () => `msg-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

export const ChatbotPage = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const scrollRef = useRef(null);
  const { showToast } = useNotification();

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, sending]);

  const pushMessage = (item) =>
    setMessages((prev) => [...prev, { ...item, id: newId() }]);

  const handleSend = async (textOverride) => {
    const text = (textOverride ?? input).trim();
    if (!text || sending) return;

    pushMessage({ role: 'user', content: text });
    setInput('');
    setSending(true);

    // Lightweight conversation context: the sanitised user/assistant turns
    // seen so far (current turn excluded). Backend re-sanitises all of it.
    const history = messages
      .filter((m) => m.role === 'user' || m.role === 'assistant')
      .slice(-8)
      .map(({ role, content }) => ({ role, content }));

    try {
      const data = await sendChatMessage(text, history);

      if (data?.error) {
        pushMessage({
          role: 'error',
          content: data.error.message,
          retryText: text,
        });
      } else {
        const reply = data?.reply?.trim();
        pushMessage({
          role: 'assistant',
          content: reply || 'I could not find an answer. Please try rephrasing your question.',
        });
      }
    } catch (err) {
      console.error('AI chat request failed:', err);
      pushMessage({
        role: 'error',
        content: getChatErrorMessage(err),
        retryText: text,
      });
      showToast('Could not reach the AI assistant.', 'error');
    } finally {
      setSending(false);
    }
  };

  return (
    <div>
      <div className="flex-between mb-6">
        <div>
          <h1 className="page-title">
            <Bot
              size={24}
              style={{ verticalAlign: 'middle', marginRight: '0.5rem', color: 'var(--accent-primary)' }}
            />
            AI Assistant
          </h1>
          <p className="page-subtitle">
            Ask questions about your inventory, sales, purchases, customers,
            suppliers, and business performance.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button
            className="btn btn-secondary"
            onClick={() => setMessages([])}
            disabled={sending || messages.length === 0}
            title="Clear conversation history"
          >
            <Trash2 size={16} /> Clear
          </button>
          <span className="badge badge-success">AI assistant enabled</span>
        </div>
      </div>

      <div className="glass-card" style={{ maxWidth: '760px', margin: '0 auto' }}>
        <div
          ref={scrollRef}
          style={{
            minHeight: '420px',
            maxHeight: '480px',
            overflowY: 'auto',
            padding: '1.5rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
          }}
        >
          {messages.length === 0 && !sending ? (
            <div
              style={{
                textAlign: 'center',
                padding: '2.25rem 1rem',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-md)',
                background: 'rgba(99, 102, 241, 0.04)',
              }}
            >
              <Sparkles size={26} style={{ color: 'var(--accent-primary)' }} />
              <p
                style={{
                  marginTop: '0.75rem',
                  fontSize: '0.9375rem',
                  color: 'var(--text-primary)',
                }}
              >
                {WELCOME_MESSAGE}
              </p>
              <div
                style={{
                  marginTop: '1.25rem',
                  display: 'flex',
                  flexWrap: 'wrap',
                  justifyContent: 'center',
                  gap: '0.5rem',
                }}
              >
                {SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    className="btn btn-secondary btn-sm"
                    onClick={() => handleSend(suggestion)}
                    disabled={sending}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m) => (
              <div
                key={m.id}
                style={{
                  alignSelf:
                    m.role === 'user'
                      ? 'flex-end'
                      : m.role === 'error'
                        ? 'flex-start'
                        : 'flex-start',
                  maxWidth: '80%',
                  padding: '0.75rem 1rem',
                  borderRadius: 'var(--radius-md)',
                  border:
                    m.role === 'error'
                      ? '1px solid rgba(220, 38, 38, 0.25)'
                      : 'none',
                  background:
                    m.role === 'user'
                      ? 'var(--accent-primary)'
                      : m.role === 'error'
                        ? 'var(--status-danger-bg)'
                        : 'rgba(99, 102, 241, 0.1)',
                  color:
                    m.role === 'user'
                      ? '#fff'
                      : m.role === 'error'
                        ? 'var(--status-danger)'
                        : 'var(--text-primary)',
                  whiteSpace: 'pre-wrap',
                }}
              >
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start' }}>
                  {m.role === 'user' && (
                    <UserIcon
                      size={14}
                      style={{ color: 'rgba(255,255,255,0.85)', marginTop: '0.2rem' }}
                    />
                  )}
                  {m.role === 'error' && (
                    <AlertCircle size={14} style={{ marginTop: '0.2rem' }} />
                  )}
                  <span>{m.content}</span>
                </div>
                {m.role === 'error' && m.retryText && (
                  <button
                    className="btn btn-danger btn-sm"
                    style={{ marginTop: '0.625rem', width: '100%' }}
                    onClick={() => handleSend(m.retryText)}
                    disabled={sending}
                  >
                    <RefreshCw size={14} style={{ marginRight: '0.35rem' }} />
                    Retry
                  </button>
                )}
              </div>
            ))
          )}

          {sending && (
            <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              <Sparkles size={14} style={{ verticalAlign: 'middle' }} /> Thinking…
            </div>
          )}
        </div>

        <div
          style={{
            padding: '1rem',
            borderTop: '1px solid var(--border-color)',
            display: 'flex',
            gap: '0.75rem',
          }}
        >
          <input
            type="text"
            className="form-input"
            placeholder="Ask about your inventory, sales, suppliers…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          />
          <button
            className="btn btn-primary btn-icon"
            onClick={() => handleSend()}
            disabled={sending || !input.trim()}
            title="Send message"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
};