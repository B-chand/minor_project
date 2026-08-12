import React, { useEffect, useState } from 'react';
import { Plus, Edit2, Trash2, Mail, Phone } from 'lucide-react';
import { authApi } from '../api';
import { Modal, Loader, PasswordInput } from '../components/common/UIComponents';
import { useNotification } from '../context/NotificationContext';

export const StaffPage = () => {
  const [staffList, setStaffList] = useState([]);
  const [loading, setLoading] = useState(true);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingStaff, setEditingStaff] = useState(null);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    phone: '',
    is_active: true,
  });
  const [submitting, setSubmitting] = useState(false);

  const { showToast } = useNotification();

  const fetchStaff = async () => {
    setLoading(true);
    try {
      const res = await authApi.getStaff();
      setStaffList(res.data.results || res.data || []);
    } catch (err) {
      showToast('Failed to load staff list.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStaff();
  }, []);

  const handleOpenModal = (staff = null) => {
    if (staff) {
      setEditingStaff(staff);
      setFormData({
        username: staff.username,
        email: staff.email || '',
        password: '',
        phone: staff.phone || '',
        is_active: staff.is_active,
      });
    } else {
      setEditingStaff(null);
      setFormData({
        username: '',
        email: '',
        password: '',
        phone: '',
        is_active: true,
      });
    }
    setIsModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (editingStaff) {
        const payload = { ...formData };
        if (!payload.password) delete payload.password;
        await authApi.updateStaff(editingStaff.id, payload);
        showToast('Staff user updated successfully!', 'success');
      } else {
        await authApi.createStaff(formData);
        showToast('Staff user created successfully!', 'success');
      }
      setIsModalOpen(false);
      fetchStaff();
    } catch (err) {
      const errors = err.response?.data;
      let msg = 'Operation failed.';
      if (typeof errors === 'object') {
        const firstKey = Object.keys(errors)[0];
        msg = `${firstKey}: ${Array.isArray(errors[firstKey]) ? errors[firstKey][0] : errors[firstKey]}`;
      }
      showToast(msg, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this staff user?')) return;
    try {
      await authApi.deleteStaff(id);
      showToast('Staff account deleted.', 'success');
      fetchStaff();
    } catch (err) {
      showToast('Cannot delete staff member.', 'error');
    }
  };

  return (
    <div>
      <div className="flex-between mb-6">
        <div>
          <h1 className="page-title">Staff Management</h1>
          <p className="page-subtitle">Add and manage staff members for your tenant organization</p>
        </div>
        <button className="btn btn-primary" onClick={() => handleOpenModal()}>
          <Plus size={18} /> Add Staff User
        </button>
      </div>

      <div className="glass-card">
        {loading ? (
          <Loader text="Loading staff records..." />
        ) : staffList.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            No staff members found. Click "Add Staff User" to invite staff.
          </div>
        ) : (
          <div className="table-responsive">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Email</th>
                  <th>Phone</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {staffList.map((s) => (
                  <tr key={s.id}>
                    <td style={{ fontWeight: 600, color: 'var(--text-main)' }}>{s.username}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)' }}>
                        <Mail size={14} /> {s.email || 'N/A'}
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <Phone size={14} /> {s.phone || 'N/A'}
                      </div>
                    </td>
                    <td>
                      <span className="badge badge-info">STAFF</span>
                    </td>
                    <td>
                      <span className={`badge ${s.is_active ? 'badge-success' : 'badge-danger'}`}>
                        {s.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          className="btn btn-secondary btn-icon btn-sm"
                          onClick={() => handleOpenModal(s)}
                          title="Edit Staff"
                        >
                          <Edit2 size={15} color="var(--accent-secondary)" />
                        </button>
                        <button
                          className="btn btn-secondary btn-icon btn-sm"
                          onClick={() => handleDelete(s.id)}
                          title="Delete Staff"
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
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingStaff ? 'Edit Staff User' : 'Create Staff User'}
      >
        <form onSubmit={handleSubmit}>
          <div className="form-group mb-4">
            <label className="form-label">Username *</label>
            <input
              type="text"
              className="form-input"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              required
            />
          </div>

          <div className="grid-2 mb-4">
            <div className="form-group">
              <label className="form-label">Email Address *</label>
              <input
                type="email"
                className="form-input"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Phone Number</label>
              <input
                type="text"
                className="form-input"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
              />
            </div>
          </div>

          <div className="form-group mb-6">
            <label className="form-label">
              Password {editingStaff && '(Leave empty to keep existing password)'}
            </label>
            <PasswordInput
              placeholder={editingStaff ? '••••••••' : 'Password'}
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              autoComplete="new-password"
              required={!editingStaff}
            />
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Saving...' : editingStaff ? 'Update Staff' : 'Create Staff'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
