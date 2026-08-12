import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Building, ArrowRight, Shield } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useNotification } from '../context/NotificationContext';
import { PasswordInput } from '../components/common/UIComponents';

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
  const [registeredCode, setRegisteredCode] = useState('');

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
      const data = await register(formData);
      const code = data?.business_code || data?.organization_code || '';
      setRegisteredCode(code);
      showToast('Organization registered successfully! Save your Business Code.', 'success');
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
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700 }}>INVENTO</h1>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Register Organization — Set up your tenant business and primary admin user account
          </p>
        </div>

        {registeredCode && (
          <div style={{ textAlign: 'center', padding: '0.5rem 0' }}>
            <div
              style={{
                width: '56px',
                height: '56px',
                margin: '0 auto 1rem',
                background: 'var(--status-success-bg, rgba(34, 197, 94, 0.15))',
                border: '2px solid var(--status-success, #22c55e)',
                borderRadius: '50%',
                color: 'var(--status-success, #22c55e)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.5rem',
                fontWeight: 700,
              }}
            >
              ✓
            </div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>
              Organization Registered!
            </h2>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
              Your tenant is ready. Save this Business Code — you will need it
              together with your username and password to log in.
            </p>
            <div
              style={{
                margin: '1.25rem auto',
                padding: '1rem',
                background: 'var(--bg-tertiary)',
                border: '2px dashed var(--accent-primary)',
                borderRadius: 'var(--radius-md)',
                fontSize: '1.5rem',
                fontWeight: 700,
                letterSpacing: '0.1em',
                color: 'var(--accent-primary)',
                width: 'fit-content',
              }}
            >
              {registeredCode}
            </div>
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={async () => {
                  if (navigator.clipboard?.writeText) {
                    await navigator.clipboard.writeText(registeredCode);
                    showToast('Business Code copied!', 'success');
                  } else {
                    showToast('Select the code to copy it manually.', 'error');
                  }
                }}
              >
                Copy Code
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => navigate('/login')}
              >
                Go to Login
              </button>
            </div>
          </div>
        )}

        {!registeredCode && (
          <>
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
                  <PasswordInput
                    name="password"
                    placeholder="Strong password"
                    value={formData.password}
                    onChange={handleChange}
                    style={inputErrorStyle('password')}
                    autoComplete="new-password"
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
          </>
        )}
      </div>
    </div>
  );
};