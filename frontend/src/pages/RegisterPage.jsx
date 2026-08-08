import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Building, ArrowRight, Shield } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useNotification } from '../context/NotificationContext';

const errorTextStyle = {
  fontSize: '0.8rem',
  color: 'var(--status-danger)',
  marginTop: '0.25rem',
};

const FIELD_NAMES = [
  'organization_name',
  'organization_email',
  'organization_phone',
  'organization_address',
  'username',
  'email',
  'password',
  'phone',
];

export const RegisterPage = () => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    phone: '',
    organization_name: '',
    organization_email: '',
    organization_phone: '',
    organization_address: '',
  });

  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});

  const { register } = useAuth();
  const { showToast } = useNotification();
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
    if (fieldErrors[name]) {
      setFieldErrors((prev) => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }
  };

  const inputErrorStyle = (field) =>
    fieldErrors[field] ? { borderColor: 'var(--status-danger)' } : undefined;

  const renderError = (field) =>
    fieldErrors[field] ? <div style={errorTextStyle}>{fieldErrors[field]}</div> : null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMsg('');
    setFieldErrors({});

    try {
      await register(formData);
      showToast('Organization & Admin account registered successfully! Please log in.', 'success');
      navigate('/login');
    } catch (err) {
      console.error('Registration error:', err);
      const data = err.response?.data;

      const nextFieldErrors = {};
      let summary = '';

      if (data && typeof data === 'object' && !Array.isArray(data)) {
        Object.entries(data).forEach(([key, value]) => {
          const message = Array.isArray(value)
            ? value[0]
            : typeof value === 'string'
            ? value
            : null;

          if (message && (key === 'non_field_errors' || key === 'detail')) {
            summary = message;
            return;
          }

          if (message) {
            nextFieldErrors[key] = message;
          }
        });
      }

      setFieldErrors(nextFieldErrors);

      if (!summary && !FIELD_NAMES.some((field) => nextFieldErrors[field])) {
        summary = 'Registration failed. Please check your inputs.';
      }

      if (summary) {
        setErrorMsg(summary);
        showToast(summary, 'error');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="flex-center"
      style={{
        minHeight: '100vh',
        background: 'radial-gradient(circle at 50% 20%, rgba(139, 92, 246, 0.15), transparent 70%), var(--bg-primary)',
        padding: '2rem 1rem',
      }}
    >
      <div
        className="glass-card"
        style={{
          width: '100%',
          maxWidth: '680px',
          padding: '2.5rem',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700 }}>Register Organization</h1>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Set up your tenant business and primary admin user account
          </p>
        </div>

        {errorMsg && (
          <div
            style={{
              background: 'var(--status-danger-bg)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: 'var(--status-danger)',
              padding: '0.75rem 1rem',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.875rem',
              marginBottom: '1.5rem',
            }}
          >
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ fontSize: '1rem', color: 'var(--accent-secondary)', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Building size={18} /> Organization Information
            </h3>
            <div className="grid-2">
              <div>
                <div className="form-group">
                  <label className="form-label">Organization Name *</label>
                  <input
                    type="text"
                    name="organization_name"
                    className="form-input"
                    placeholder="e.g. Acme Retail Ltd"
                    value={formData.organization_name}
                    onChange={handleChange}
                    style={inputErrorStyle('organization_name')}
                    required
                  />
                </div>
                {renderError('organization_name')}
              </div>

              <div>
                <div className="form-group">
                  <label className="form-label">Organization Email *</label>
                  <input
                    type="email"
                    name="organization_email"
                    className="form-input"
                    placeholder="org@company.com"
                    value={formData.organization_email}
                    onChange={handleChange}
                    style={inputErrorStyle('organization_email')}
                    required
                  />
                </div>
                {renderError('organization_email')}
              </div>

              <div>
                <div className="form-group">
                  <label className="form-label">Organization Phone *</label>
                  <input
                    type="text"
                    name="organization_phone"
                    className="form-input"
                    placeholder="+977 9800000000"
                    value={formData.organization_phone}
                    onChange={handleChange}
                    style={inputErrorStyle('organization_phone')}
                    required
                  />
                </div>
                {renderError('organization_phone')}
              </div>

              <div>
                <div className="form-group">
                  <label className="form-label">Address</label>
                  <input
                    type="text"
                    name="organization_address"
                    className="form-input"
                    placeholder="City, Country"
                    value={formData.organization_address}
                    onChange={handleChange}
                    style={inputErrorStyle('organization_address')}
                  />
                </div>
                {renderError('organization_address')}
              </div>
            </div>
          </div>

          <div style={{ marginBottom: '2rem' }}>
            <h3 style={{ fontSize: '1rem', color: 'var(--accent-primary)', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Shield size={18} /> Business Admin Account
            </h3>
            <div className="grid-2">
              <div>
                <div className="form-group">
                  <label className="form-label">Admin Username *</label>
                  <input
                    type="text"
                    name="username"
                    className="form-input"
                    placeholder="admin_username"
                    value={formData.username}
                    onChange={handleChange}
                    style={inputErrorStyle('username')}
                    required
                  />
                </div>
                {renderError('username')}
              </div>

              <div>
                <div className="form-group">
                  <label className="form-label">Admin Email *</label>
                  <input
                    type="email"
                    name="email"
                    className="form-input"
                    placeholder="admin@company.com"
                    value={formData.email}
                    onChange={handleChange}
                    style={inputErrorStyle('email')}
                    required
                  />
                </div>
                {renderError('email')}
              </div>

              <div>
                <div className="form-group">
                  <label className="form-label">Password *</label>
                  <input
                    type="password"
                    name="password"
                    className="form-input"
                    placeholder="Strong password"
                    value={formData.password}
                    onChange={handleChange}
                    style={inputErrorStyle('password')}
                    required
                  />
                </div>
                {renderError('password')}
              </div>

              <div>
                <div className="form-group">
                  <label className="form-label">Admin Phone</label>
                  <input
                    type="text"
                    name="phone"
                    className="form-input"
                    placeholder="Phone number"
                    value={formData.phone}
                    onChange={handleChange}
                    style={inputErrorStyle('phone')}
                  />
                </div>
                {renderError('phone')}
              </div>
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={submitting}
            style={{ width: '100%', padding: '0.75rem', fontSize: '0.9375rem' }}
          >
            {submitting ? 'Registering Tenant...' : 'Create Business Account'}
            {!submitting && <ArrowRight size={18} />}
          </button>
        </form>

        <div
          style={{
            marginTop: '1.5rem',
            textAlign: 'center',
            fontSize: '0.875rem',
            color: 'var(--text-muted)',
          }}
        >
          Already registered?{' '}
          <Link
            to="/login"
            style={{
              color: 'var(--accent-primary)',
              textDecoration: 'none',
              fontWeight: 600,
            }}
          >
            Sign In
          </Link>
        </div>
      </div>
    </div>
  );
};