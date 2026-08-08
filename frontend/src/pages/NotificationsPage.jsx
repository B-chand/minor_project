import React, { useEffect, useState } from 'react';
import { Bell, CheckCircle2, AlertTriangle, XCircle, ShoppingCart, ShoppingBag, Info, Trash2, CheckCheck } from 'lucide-react';
import { notificationApi } from '../api';
import { Loader } from '../components/common/UIComponents';
import { useNotification } from '../context/NotificationContext';
import { formatDateTime } from '../utils/formatters';

export const NotificationsPage = () => {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState('ALL');
  const { showToast } = useNotification();

  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const res = await notificationApi.getAll();
      setNotifications(res.data.results || res.data || []);
    } catch (err) {
      showToast('Failed to load notifications.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  const handleMarkRead = async (id) => {
    try {
      await notificationApi.markRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      showToast('Notification marked as read.', 'success');
    } catch (err) {
      showToast('Failed to update notification.', 'error');
    }
  };

  const handleDelete = async (id) => {
    try {
      await notificationApi.delete(id);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
      showToast('Notification removed.', 'success');
    } catch (err) {
      showToast('Failed to delete notification.', 'error');
    }
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'LOW_STOCK':
        return <AlertTriangle color="var(--status-warning)" size={20} />;
      case 'OUT_OF_STOCK':
        return <XCircle color="var(--status-danger)" size={20} />;
      case 'SALE':
        return <ShoppingCart color="var(--status-success)" size={20} />;
      case 'PURCHASE':
        return <ShoppingBag color="var(--status-info)" size={20} />;
      default:
        return <Info color="var(--accent-primary)" size={20} />;
    }
  };

  const filteredNotifications = notifications.filter((n) =>
    filterType === 'ALL' ? true : n.notification_type === filterType
  );

  return (
    <div>
      <div className="flex-between mb-6">
        <div>
          <h1 className="page-title">System Notifications</h1>
          <p className="page-subtitle">Low stock alerts, order completions, and automated event triggers</p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        {['ALL', 'LOW_STOCK', 'OUT_OF_STOCK', 'SALE', 'PURCHASE', 'SYSTEM'].map((type) => (
          <button
            key={type}
            className={`btn btn-sm ${filterType === type ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setFilterType(type)}
          >
            {type.replace('_', ' ')}
          </button>
        ))}
      </div>

      <div className="glass-card">
        {loading ? (
          <Loader text="Loading notification center..." />
        ) : filteredNotifications.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            No notifications found.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {filteredNotifications.map((n) => (
              <div
                key={n.id}
                style={{
                  padding: '1.25rem',
                  background: n.is_read ? 'rgba(255,255,255,0.01)' : 'rgba(99, 102, 241, 0.05)',
                  border: `1px solid ${n.is_read ? 'var(--border-color)' : 'var(--accent-glow)'}`,
                  borderRadius: 'var(--radius-md)',
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  gap: '1rem',
                }}
              >
                <div style={{ display: 'flex', gap: '1rem' }}>
                  <div style={{ marginTop: '0.2rem' }}>{getNotificationIcon(n.notification_type)}</div>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                      <h4 style={{ fontSize: '0.9375rem', fontWeight: 600 }}>{n.title}</h4>
                      {!n.is_read && <span className="badge badge-warning">Unread</span>}
                    </div>
                    <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                      {n.message}
                    </p>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.5rem' }}>
                      {formatDateTime(n.created_at)}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  {!n.is_read && (
                    <button
                      className="btn btn-secondary btn-icon btn-sm"
                      onClick={() => handleMarkRead(n.id)}
                      title="Mark as read"
                    >
                      <CheckCheck size={16} color="var(--status-success)" />
                    </button>
                  )}
                  <button
                    className="btn btn-secondary btn-icon btn-sm"
                    onClick={() => handleDelete(n.id)}
                    title="Delete notification"
                  >
                    <Trash2 size={16} color="var(--status-danger)" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
