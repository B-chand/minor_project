import React, { useEffect, useState } from 'react';
import { Truck, Plus, Search, Edit2, Trash2, Phone, Mail, UserCheck } from 'lucide-react';
import { supplierApi } from '../api';
import { Modal, Loader, Pagination } from '../components/common/UIComponents';
import { useNotification } from '../context/NotificationContext';

export const SuppliersPage = () => {
  const [suppliers, setSuppliers] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [appliedSearch, setAppliedSearch] = useState('');

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    address: '',
    contact_person: '',
    is_active: true,
  });
  const [submitting, setSubmitting] = useState(false);

  const { showToast } = useNotification();

  const fetchSuppliers = async () => {
    setLoading(true);
    try {
      const res = await supplierApi.getAll({ page, search: appliedSearch || undefined });
      setSuppliers(res.data.results || res.data || []);
      setCount(res.data.count || (res.data || []).length);
    } catch (err) {
      showToast('Failed to load suppliers.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSuppliers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, appliedSearch]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setAppliedSearch(search.trim());
    setPage(1);
  };

  const handleOpenModal = (s = null) => {
    if (s) {
      setEditingSupplier(s);
      setFormData({
        name: s.name,
        email: s.email || '',
        phone: s.phone,
        address: s.address || '',
        contact_person: s.contact_person || '',
        is_active: s.is_active,
      });
    } else {
      setEditingSupplier(null);
      setFormData({
        name: '',
        email: '',
        phone: '',
        address: '',
        contact_person: '',
        is_active: true,
      });
    }
    setIsModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (editingSupplier) {
        await supplierApi.update(editingSupplier.id, formData);
        showToast('Supplier updated successfully!', 'success');
      } else {
        await supplierApi.create(formData);
        showToast('Supplier created successfully!', 'success');
      }
      setIsModalOpen(false);
      fetchSuppliers();
    } catch (err) {
      const errors = err.response?.data;
      let msg = 'Failed to save supplier.';
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
    if (!window.confirm('Are you sure you want to delete this supplier?')) return;
    try {
      await supplierApi.delete(id);
      showToast('Supplier deleted.', 'success');
      fetchSuppliers();
    } catch (err) {
      showToast('Cannot delete supplier with linked purchase orders.', 'error');
    }
  };

  return (
    <div>
      <div className="flex-between mb-6">
        <div>
          <h1 className="page-title">Suppliers Directory</h1>
          <p className="page-subtitle">Manage vendors, wholesale contacts, and purchase origins</p>
        </div>
        <button className="btn btn-primary" onClick={() => handleOpenModal()}>
          <Plus size={18} /> Add Supplier
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
              placeholder="Search by supplier name, phone..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <button type="submit" className="btn btn-secondary">Search</button>
        </form>
      </div>

      <div className="glass-card">
        {loading ? (
          <Loader text="Loading suppliers directory..." />
        ) : suppliers.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            No supplier records found.
          </div>
        ) : (
          <>
            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Supplier / Company</th>
                    <th>Contact Person</th>
                    <th>Phone</th>
                    <th>Email</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {suppliers.map((s) => (
                    <tr key={s.id}>
                      <td style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <Truck size={16} color="var(--status-info)" />
                          {s.name}
                        </div>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <UserCheck size={14} color="var(--text-dim)" />
                          {s.contact_person || 'N/A'}
                        </div>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <Phone size={14} color="var(--text-dim)" />
                          {s.phone}
                        </div>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)' }}>
                          <Mail size={14} color="var(--text-dim)" />
                          {s.email || 'N/A'}
                        </div>
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
                            title="Edit Supplier"
                          >
                            <Edit2 size={15} color="var(--accent-secondary)" />
                          </button>
                          <button
                            className="btn btn-secondary btn-icon btn-sm"
                            onClick={() => handleDelete(s.id)}
                            title="Delete Supplier"
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
        title={editingSupplier ? 'Edit Supplier' : 'Add New Supplier'}
      >
        <form onSubmit={handleSubmit}>
          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">Company / Supplier Name *</label>
              <input
                type="text"
                className="form-input"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Contact Person</label>
              <input
                type="text"
                className="form-input"
                value={formData.contact_person}
                onChange={(e) => setFormData({ ...formData, contact_person: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Phone Number *</label>
              <input
                type="text"
                className="form-input"
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
              {submitting ? 'Saving...' : editingSupplier ? 'Update Supplier' : 'Create Supplier'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
