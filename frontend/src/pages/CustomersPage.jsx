import React, { useEffect, useState } from 'react';
import { Plus, Search, Edit2, Trash2, Phone, Mail, Award } from 'lucide-react';
import { customerApi } from '../api';
import { Modal, Loader, Pagination } from '../components/common/UIComponents';
import { useNotification } from '../context/NotificationContext';

export const CustomersPage = () => {
  const [customers, setCustomers] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [appliedSearch, setAppliedSearch] = useState('');

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState(null);
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    address: '',
    loyalty_points: 0,
    is_active: true,
  });
  const [submitting, setSubmitting] = useState(false);

  const { showToast } = useNotification();

  const fetchCustomers = async () => {
    setLoading(true);
    try {
      const res = await customerApi.getAll({ page, search: appliedSearch || undefined });
      setCustomers(res.data.results || res.data || []);
      setCount(res.data.count || (res.data || []).length);
    } catch (err) {
      showToast('Failed to load customers.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCustomers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, appliedSearch]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setAppliedSearch(search.trim());
    setPage(1);
  };

  const handleOpenModal = (c = null) => {
    if (c) {
      setEditingCustomer(c);
      setFormData({
        first_name: c.first_name,
        last_name: c.last_name || '',
        email: c.email || '',
        phone: c.phone,
        address: c.address || '',
        loyalty_points: c.loyalty_points || 0,
        is_active: c.is_active,
      });
    } else {
      setEditingCustomer(null);
      setFormData({
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        address: '',
        loyalty_points: 0,
        is_active: true,
      });
    }
    setIsModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (editingCustomer) {
        await customerApi.update(editingCustomer.id, formData);
        showToast('Customer updated successfully!', 'success');
      } else {
        await customerApi.create(formData);
        showToast('Customer created successfully!', 'success');
      }
      setIsModalOpen(false);
      fetchCustomers();
    } catch (err) {
      const errors = err.response?.data;
      let msg = 'Failed to save customer.';
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
    if (!window.confirm('Are you sure you want to delete this customer?')) return;
    try {
      await customerApi.delete(id);
      showToast('Customer deleted.', 'success');
      fetchCustomers();
    } catch (err) {
      showToast('Cannot delete customer with sales history.', 'error');
    }
  };

  return (
    <div>
      <div className="flex-between mb-6">
        <div>
          <h1 className="page-title">Customers Management</h1>
          <p className="page-subtitle">Client profiles, contact numbers, and loyalty reward points</p>
        </div>
        <button className="btn btn-primary" onClick={() => handleOpenModal()}>
          <Plus size={18} /> Add Customer
        </button>
      </div>

      <div className="glass-card mb-6">
        <form onSubmit={handleSearchSubmit} className="flex-between">
          <div style={{ position: 'relative', width: '320px' }}>
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
              placeholder="Search by name, phone, email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <button type="submit" className="btn btn-secondary">Search</button>
        </form>
      </div>

      <div className="glass-card">
        {loading ? (
          <Loader text="Loading customers..." />
        ) : customers.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            No customer records found.
          </div>
        ) : (
          <>
            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Customer Name</th>
                    <th>Phone</th>
                    <th>Email</th>
                    <th>Loyalty Points</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {customers.map((c) => (
                    <tr key={c.id}>
                      <td style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                        {c.first_name} {c.last_name}
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <Phone size={14} color="var(--text-dim)" />
                          {c.phone}
                        </div>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)' }}>
                          <Mail size={14} color="var(--text-dim)" />
                          {c.email || 'N/A'}
                        </div>
                      </td>
                      <td>
                        <span className="badge badge-info" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                          <Award size={12} /> {c.loyalty_points} pts
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${c.is_active ? 'badge-success' : 'badge-danger'}`}>
                          {c.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button
                            className="btn btn-secondary btn-icon btn-sm"
                            onClick={() => handleOpenModal(c)}
                            title="Edit Customer"
                          >
                            <Edit2 size={15} color="var(--accent-secondary)" />
                          </button>
                          <button
                            className="btn btn-secondary btn-icon btn-sm"
                            onClick={() => handleDelete(c.id)}
                            title="Delete Customer"
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
            <Pagination count={count} page={page} onPageChange={setPage} pageSize={10} />
          </>
        )}
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingCustomer ? 'Edit Customer' : 'Add New Customer'}
      >
        <form onSubmit={handleSubmit}>
          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">First Name *</label>
              <input
                type="text"
                className="form-input"
                value={formData.first_name}
                onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Last Name</label>
              <input
                type="text"
                className="form-input"
                value={formData.last_name}
                onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Phone Number *</label>
              <input
                type="text"
                className="form-input"
                placeholder="+977 9800000000"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Email Address</label>
              <input
                type="email"
                className="form-input"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              />
            </div>
          </div>

          <div className="form-group mb-4">
            <label className="form-label">Loyalty Points</label>
            <input
              type="number"
              className="form-input"
              value={formData.loyalty_points}
              onChange={(e) => setFormData({ ...formData, loyalty_points: parseInt(e.target.value) || 0 })}
            />
          </div>

          <div className="form-group mb-6">
            <label className="form-label">Address</label>
            <textarea
              className="form-textarea"
              rows={2}
              value={formData.address}
              onChange={(e) => setFormData({ ...formData, address: e.target.value })}
            />
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Saving...' : editingCustomer ? 'Update Customer' : 'Create Customer'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
