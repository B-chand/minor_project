import React from 'react';
import { X, ChevronLeft, ChevronRight } from 'lucide-react';

export const Loader = ({ text = 'Loading data...' }) => (
  <div className="flex-center" style={{ padding: '3rem 1rem', flexDirection: 'column', gap: '0.75rem' }}>
    <div
      style={{
        width: '32px',
        height: '32px',
        border: '3px solid var(--border-color)',
        borderTopColor: 'var(--accent-primary)',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
      }}
    />
    <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>{text}</span>
  </div>
);

export const Modal = ({ isOpen, onClose, title, children, maxWidth = '600px' }) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-container"
        style={{ maxWidth }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>{title}</h3>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              display: 'flex',
              padding: '0.25rem',
            }}
          >
            <X size={20} />
          </button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
};

export const Pagination = ({ count, page, onPageChange, pageSize = 10 }) => {
  const totalPages = Math.ceil((count || 0) / pageSize);

  if (totalPages <= 1) return null;

  return (
    <div className="pagination">
      <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
        Showing page {page} of {totalPages} ({count} total items)
      </span>
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <button
          className="btn btn-secondary btn-sm"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          <ChevronLeft size={16} /> Previous
        </button>
        <button
          className="btn btn-secondary btn-sm"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          Next <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
};

export const StatCard = ({ icon: Icon, label, value, color = 'var(--accent-primary)', bg = 'var(--accent-glow)' }) => (
  <div className="glass-card stat-card">
    <div className="stat-icon-wrapper" style={{ background: bg, color }}>
      <Icon size={26} />
    </div>
    <div>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  </div>
);
