import React, { useEffect, useState } from 'react';
import { Building2, Save, Globe, CreditCard, Shield } from 'lucide-react';
import { businessApi } from '../api';
import { Loader } from '../components/common/UIComponents';
import { useNotification } from '../context/NotificationContext';

export const BusinessPage = () => {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    business_type: 'RETAIL',
    pan_number: '',
    vat_number: '',
    website: '',
    currency: 'NPR',
    invoice_prefix: 'INV',
  });

  const { showToast } = useNotification();

  const fetchProfile = async () => {
    setLoading(true);
    try {
      const res = await businessApi.getProfile();
      const items = res.data.results || res.data || [];
      if (items.length > 0) {
        const p = items[0];
        setProfile(p);
        setFormData({
          business_type: p.business_type || 'RETAIL',
          pan_number: p.pan_number || '',
          vat_number: p.vat_number || '',
          website: p.website || '',
          currency: p.currency || 'NPR',
          invoice_prefix: p.invoice_prefix || 'INV',
        });
      }
    } catch (err) {
      showToast('Failed to load business profile.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (profile) {
        await businessApi.updateProfile(profile.id, formData);
        showToast('Business profile updated successfully!', 'success');
      } else {
        await businessApi.createProfile(formData);
        showToast('Business profile created successfully!', 'success');
      }
      fetchProfile();
    } catch (err) {
      showToast('Failed to update business profile.', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <Loader text="Loading business settings..." />;

  return (
    <div style={{ maxWidth: '800px' }}>
      <div className="flex-between mb-6">
        <div>
          <h1 className="page-title">Business Profile & Settings</h1>
          <p className="page-subtitle">Configure organization currency, Tax IDs (PAN/VAT), and invoice prefixes</p>
        </div>
      </div>

      <div className="glass-card">
        <form onSubmit={handleSubmit}>
          <div className="grid-2 mb-4">
            <div className="form-group">
              <label className="form-label">Business Type</label>
              <select
                className="form-select"
                value={formData.business_type}
                onChange={(e) => setFormData({ ...formData, business_type: e.target.value })}
              >
                <option value="RETAIL">Retail</option>
                <option value="WHOLESALE">Wholesale</option>
                <option value="MANUFACTURING">Manufacturing</option>
                <option value="SERVICE">Service</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Default Currency</label>
              <input
                type="text"
                className="form-input"
                placeholder="NPR (Nepalese Rupee)"
                value={formData.currency}
                readOnly
                title="Business currency is fixed to NPR (Nepalese Rupees)"
              />
            </div>

            <div className="form-group">
              <label className="form-label">Invoice Prefix</label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. INV, ACME"
                value={formData.invoice_prefix}
                onChange={(e) => setFormData({ ...formData, invoice_prefix: e.target.value })}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Website</label>
              <input
                type="url"
                className="form-input"
                placeholder="https://company.com"
                value={formData.website}
                onChange={(e) => setFormData({ ...formData, website: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label className="form-label">PAN Number</label>
              <input
                type="text"
                className="form-input"
                placeholder="Tax PAN Number"
                value={formData.pan_number}
                onChange={(e) => setFormData({ ...formData, pan_number: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label className="form-label">VAT Number</label>
              <input
                type="text"
                className="form-input"
                placeholder="Tax VAT Number"
                value={formData.vat_number}
                onChange={(e) => setFormData({ ...formData, vat_number: e.target.value })}
              />
            </div>
          </div>

          <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              <Save size={16} />
              {submitting ? 'Saving Settings...' : 'Save Profile Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
