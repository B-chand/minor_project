import React, { createContext, useContext, useState, useCallback } from 'react';
import { CheckCircle2, AlertTriangle, XCircle, Info, X } from 'lucide-react';

const NotificationContext = createContext();

export const NotificationProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const showToast = useCallback((message, type = 'info', duration = 4000) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message, type }]);

    setTimeout(() => {
      setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, duration);
  }, []);

  const removeToast = (id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  };

  return (
    <NotificationContext.Provider value={{ showToast, unreadCount, setUnreadCount }}>
      {children}
      {/* Global Toast Container */}
      <div style={{
        position: 'fixed',
        bottom: '1.5rem',
        right: '1.5rem',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem',
        maxWidth: '400px',
      }}>
        {toasts.map((t) => {
          const getIcon = () => {
            switch (t.type) {
              case 'success': return <CheckCircle2 size={18} color="var(--status-success)" />;
              case 'warning': return <AlertTriangle size={18} color="var(--status-warning)" />;
              case 'error': return <XCircle size={18} color="var(--status-danger)" />;
              default: return <Info size={18} color="var(--status-info)" />;
            }
          };

          return (
            <div
              key={t.id}
              className="glass-card"
              style={{
                padding: '0.875rem 1rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '0.75rem',
                borderLeft: `4px solid ${
                  t.type === 'success' ? 'var(--status-success)' :
                  t.type === 'warning' ? 'var(--status-warning)' :
                  t.type === 'error' ? 'var(--status-danger)' : 'var(--status-info)'
                }`,
                boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
                animation: 'fadeIn 0.2s ease',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                {getIcon()}
                <span style={{ fontSize: '0.875rem', color: 'var(--text-main)' }}>{t.message}</span>
              </div>
              <button
                onClick={() => removeToast(t.id)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-dim)',
                  cursor: 'pointer',
                  display: 'flex',
                }}
              >
                <X size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </NotificationContext.Provider>
  );
};

export const useNotification = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotification must be used within NotificationProvider');
  }
  return context;
};
