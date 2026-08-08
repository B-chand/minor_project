import React, { useEffect, useState } from 'react';
import {
  FileText,
  Plus,
  Edit2,
  Trash2,
  Search,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react';
import { aiInsightApi, fetchAllPages } from '../api';
import { Modal, Loader } from '../components/common/UIComponents';
import { useNotification } from '../context/NotificationContext';
import { formatDateTime } from '../utils/formatters';

const INSIGHT_TYPES = [
  { value: 'FORECAST', label: 'Demand Forecast' },
  { value: 'LOW_STOCK', label: 'Low Stock Prediction' },
  { value: 'RECOMMENDATION', label: 'Inventory Recommendation' },
  { value: 'ANALYSIS', label: 'Business Analysis' },
];

const TYPE_BADGES = {
  FORECAST: 'badge-info',
  LOW_STOCK: 'badge-warning',
  RECOMMENDATION: 'badge-success',
  ANALYSIS: 'badge-secondary',
};

const typeLabel = (value) => {
  const found = INSIGHT_TYPES.find((t) => t.value === value);
  return found ? found.label : value || '—';
};

const typeBadgeClass = (value) => TYPE_BADGES[value] || 'badge-info';

const getApiError = (err) => {
  const data = err.response?.data;
  if (!data) return 'Operation failed. Please try again.';
  if (Array.isArray(data)) return data[0] || 'Operation failed.';
  for (const key of Object.keys(data)) {
    const value = data[key];
    if (Array.isArray(value) && value.length) return value[0];
    if (typeof value === 'string') return value;
  }
  return 'Operation failed. Please try again.';
};

const truncate = (text = '', max = 140) =>
  text.length > max ? `${text.slice(0, max).trimEnd()}…` : text;

const initialState = {
  title: '',
  description: '',
  insight_type: '',
  confidence_score: '',
  generated_by: 'AI',
  is_active: true,
};

export const AIInsightsPage = () => {
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState('');
  const [search, setSearch] = useState('');

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [formData, setFormData] = useState(initialState);
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const { showToast } = useNotification();

  const fetchInsights = async () => {
    setLoading(true);
    setListError('');
    try {
      const items = await fetchAllPages((params) => aiInsightApi.getAll(params));
      setInsights(items);
    } catch (err) {
      setListError(getApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInsights();
  }, []);

  const openCreate = () => {
    setEditing(null);
    setFormData(initialState);
    setFormError('');
    setIsModalOpen(true);
  };

  const openEdit = (insight) => {
    setEditing(insight);
    setFormData({
      title: insight.title,
      description: insight.description,
      insight_type: insight.insight_type,
      confidence_score:
        insight.confidence_score === undefined || insight.confidence_score === null
          ? ''
          : String(insight.confidence_score),
      generated_by: insight.generated_by || 'AI',
      is_active: Boolean(insight.is_active),
    });
    setFormError('');
    setIsModalOpen(true);
  };

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.title.trim() || !formData.description.trim() || !formData.insight_type) {
      setFormError('Title, description and insight type are required.');
      return;
    }
    setSubmitting(true);
    setFormError('');
    try {
      const payload = {
        title: formData.title.trim(),
        description: formData.description.trim(),
        insight_type: formData.insight_type,
        confidence_score: formData.confidence_score === '' ? 0 : formData.confidence_score,
        generated_by: formData.generated_by.trim() || 'AI',
        is_active: formData.is_active,
      };
      if (editing) {
        await aiInsightApi.update(editing.id, payload);
        showToast('AI insight updated successfully.', 'success');
      } else {
        await aiInsightApi.create(payload);
        showToast('AI insight created successfully.', 'success');
      }
      setIsModalOpen(false);
      fetchInsights();
    } catch (err) {
      setFormError(getApiError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (insight) => {
    if (!window.confirm(`Delete the AI insight "${insight.title}"?`)) return;
    setDeletingId(insight.id);
    try {
      await aiInsightApi.delete(insight.id);
      showToast('AI insight deleted.', 'success');
      fetchInsights();
    } catch (err) {
      showToast(getApiError(err), 'error');
    } finally {
      setDeletingId(null);
    }
  };

  const filteredInsights = insights.filter((item) => {
    const query = search.trim().toLowerCase();
    if (!query) return true;
    return (
      item.title.toLowerCase().includes(query) ||
      item.description.toLowerCase().includes(query) ||
      typeLabel(item.insight_type).toLowerCase().includes(query)
    );
  });

  return (
    <div>
      <div className="flex-between mb-6">
        <div>
          <h1 className="page-title">
            <FileText
              size={24}
              style={{ verticalAlign: 'middle', marginRight: '0.5rem', color: 'var(--accent-primary)' }}
            />
            AI Insights
          </h1>
          <p className="page-subtitle">View and manage AI-generated business insight records</p>
        </div>
        <button className="btn btn-primary" onClick={openCreate}>
          <Plus size={18} /> New Insight
        </button>
      </div>

      <div className="glass-card">
        {listError ? (
          <div style={{ padding: '3rem', textAlign: 'center' }}>
            <AlertTriangle size={28} color="var(--status-danger)" style={{ marginBottom: '0.5rem' }} />
            <div style={{ color: 'var(--status-danger)', marginBottom: '1rem' }}>{listError}</div>
            <button className="btn btn-secondary" onClick={fetchInsights}>
              <RefreshCw size={16} /> Retry
            </button>
          </div>
        ) : (
          <>
            <div className="flex-between mb-4">
              <div style={{ position: 'relative', width: '320px', maxWidth: '100%' }}>
                <Search
                  size={18}
                  style={{
                    position: 'absolute',
                    left: '12px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: 'var(--text-dim)',
                  }}
                />
                <input
                  type="text"
                  className="form-input"
                  style={{ paddingLeft: '2.5rem' }}
                  placeholder="Search insights..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
            </div>

            {loading ? (
              <Loader text="Loading AI insights..." />
            ) : filteredInsights.length === 0 ? (
              <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                {insights.length === 0
                  ? 'No AI insights yet. Click "New Insight" to create one.'
                  : 'No insights match your search.'}
              </div>
            ) : (
              <div className="table-responsive">
                <table className="custom-table">
                  <thead>
                    <tr>
                      <th>Insight</th>
                      <th>Description</th>
                      <th>Type</th>
                      <th>Confidence</th>
                      <th>Source</th>
                      <th>Status</th>
                      <th>Created</th>
                      <th>Updated</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredInsights.map((item) => (
                      <tr key={item.id}>
                        <td style={{ fontWeight: 600, color: 'var(--text-main)' }}>{item.title}</td>
                        <td style={{ color: 'var(--text-muted)', maxWidth: '280px' }} title={item.description}>
                          {item.description ? truncate(item.description) : '—'}
                        </td>
                        <td>
                          <span className={`badge ${typeBadgeClass(item.insight_type)}`}>
                            {typeLabel(item.insight_type)}
                          </span>
                        </td>
                        <td>{Number(item.confidence_score ?? 0).toFixed(2)}</td>
                        <td>{item.generated_by || 'AI'}</td>
                        <td>
                          <span className={`badge ${item.is_active ? 'badge-success' : 'badge-secondary'}`}>
                            {item.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td style={{ whiteSpace: 'nowrap', color: 'var(--text-muted)' }}>{formatDateTime(item.created_at)}</td>
                        <td style={{ whiteSpace: 'nowrap', color: 'var(--text-muted)' }}>{formatDateTime(item.updated_at)}</td>
                        <td>
                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button
                              className="btn btn-secondary btn-icon btn-sm"
                              onClick={() => openEdit(item)}
                              title="Edit Insight"
                            >
                              <Edit2 size={15} color="var(--accent-secondary)" />
                            </button>
                            <button
                              className="btn btn-secondary btn-icon btn-sm"
                              onClick={() => handleDelete(item)}
                              disabled={deletingId === item.id}
                              title="Delete Insight"
                            >
                              <Trash2 size={15} color="var(--status-danger)" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editing ? 'Edit AI Insight' : 'Create AI Insight'}
      >
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Title *</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Gamma demand is rising"
              value={formData.title}
              onChange={(e) => handleChange('title', e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Description *</label>
            <textarea
              className="form-textarea"
              rows={4}
              placeholder="Describe the insight and its business impact..."
              value={formData.description}
              onChange={(e) => handleChange('description', e.target.value)}
            />
          </div>

          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">Insight Type *</label>
              <select
                className="form-select"
                value={formData.insight_type}
                onChange={(e) => handleChange('insight_type', e.target.value)}
              >
                <option value="">Select type...</option>
                {INSIGHT_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Confidence Score</label>
              <input
                type="number"
                className="form-input"
                step="0.01"
                min="0"
                value={formData.confidence_score}
                onChange={(e) => handleChange('confidence_score', e.target.value)}
                placeholder="0.00"
              />
            </div>
          </div>

          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">Generated By</label>
              <input
                type="text"
                className="form-input"
                value={formData.generated_by}
                onChange={(e) => handleChange('generated_by', e.target.value)}
                placeholder="AI"
              />
            </div>

            <div className="form-group" style={{ justifyContent: 'flex-end' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => handleChange('is_active', e.target.checked)}
                />
                <span style={{ fontSize: '0.875rem', fontWeight: 600 }}>Active</span>
              </label>
            </div>
          </div>

          {formError && (
            <div
              style={{
                marginBottom: '1rem',
                padding: '0.75rem 1rem',
                borderRadius: 'var(--radius-md)',
                background: 'var(--status-danger-bg)',
                color: 'var(--status-danger)',
                fontSize: '0.875rem',
              }}
            >
              {formError}
            </div>
          )}

          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setIsModalOpen(false)}
            >
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Saving...' : editing ? 'Update Insight' : 'Create Insight'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};