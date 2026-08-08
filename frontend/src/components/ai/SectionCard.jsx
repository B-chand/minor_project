import React from 'react';

export const SectionCard = ({
  icon: Icon,
  title,
  color = 'var(--accent-primary)',
  headerRight,
  children,
}) => (
  <div className="glass-card">
    <div className="flex-between mb-4">
      <h3
        style={{
          fontSize: '1rem',
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}
      >
        {Icon && <Icon size={18} color={color} />}
        {title}
      </h3>
      {headerRight}
    </div>
    {children}
  </div>
);

export const EmptyState = ({ message }) => (
  <div
    style={{
      padding: '2rem',
      textAlign: 'center',
      color: 'var(--text-muted)',
      fontSize: '0.875rem',
    }}
  >
    {message}
  </div>
);