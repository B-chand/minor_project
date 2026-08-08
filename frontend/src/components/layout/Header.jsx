import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, LogOut, Building, ShieldCheck } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { notificationApi } from '../../api';

export const Header = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    const fetchUnreadCount = async () => {
      try {
        const res = await notificationApi.getAll();
        const items = res.data.results || res.data || [];
        const unread = items.filter((n) => !n.is_read).length;
        setUnreadCount(unread);
      } catch (err) {
        // Silent catch if unauthenticated or network error
      }
    };
    if (user) {
      fetchUnreadCount();
      const interval = setInterval(fetchUnreadCount, 30000); // Check every 30s
      return () => clearInterval(interval);
    }
  }, [user]);

  const getRoleBadge = (role) => {
    switch (role) {
      case 'SUPER_ADMIN': return 'Super Admin';
      case 'ADMIN': return 'Business Admin';
      case 'STAFF': return 'Staff';
      default: return role;
    }
  };

  return (
    <header className="header">
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <div
          className="glass-card"
          style={{
            padding: '0.35rem 0.75rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            borderRadius: 'var(--radius-full)',
            fontSize: '0.8125rem',
          }}
        >
          <Building size={14} color="var(--accent-primary)" />
          <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>
            {user?.organization || 'Tenant Organization'}
          </span>
        </div>
      </div>

      <div className="header-user">
        <button
          onClick={() => navigate('/notifications')}
          style={{
            position: 'relative',
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-color)',
            color: 'var(--text-main)',
            width: '40px',
            height: '40px',
            borderRadius: 'var(--radius-md)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
          title="Notifications"
        >
          <Bell size={18} />
          {unreadCount > 0 && (
            <span
              style={{
                position: 'absolute',
                top: '-4px',
                right: '-4px',
                background: 'var(--status-danger)',
                color: 'white',
                fontSize: '0.6875rem',
                fontWeight: 'bold',
                width: '18px',
                height: '18px',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div className="user-avatar">
            {user?.username ? user.username.charAt(0).toUpperCase() : 'U'}
          </div>
          <div className="user-info">
            <span className="user-name">{user?.username}</span>
            <span className="user-role" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <ShieldCheck size={12} color="var(--status-success)" />
              {getRoleBadge(user?.role)}
            </span>
          </div>
        </div>

        <button
          onClick={logout}
          className="btn btn-secondary btn-icon"
          title="Logout"
          style={{ marginLeft: '0.5rem' }}
        >
          <LogOut size={18} color="var(--status-danger)" />
        </button>
      </div>
    </header>
  );
};
