import React, { useEffect, useState } from 'react';
import { Boxes, History, Edit2, Plus, ArrowUpRight, ArrowDownLeft, Sliders, RefreshCw } from 'lucide-react';
import { inventoryApi, productApi, fetchAllPages } from '../api';
import { Modal, Loader, Pagination } from '../components/common/UIComponents';
import { useNotification } from '../context/NotificationContext';
import { getStockBadgeClass, formatDateTime } from '../utils/formatters';

export const InventoryPage = () => {
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'history'
  const [inventoryList, setInventoryList] = useState([]);
  const [movementList, setMovementList] = useState([]);
  const [products, setProducts] = useState([]);
  
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  // Modals state
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [selectedInventory, setSelectedInventory] = useState(null);
  const [editForm, setEditForm] = useState({ quantity: 0, minimum_stock: 10, maximum_stock: 1000 });

  const [isAdjustmentModalOpen, setIsAdjustmentModalOpen] = useState(false);
  const [adjustmentForm, setAdjustmentForm] = useState({
    product: '',
    movement_type: 'ADJUSTMENT',
    quantity: 1,
    remarks: '',
  });

  const [submitting, setSubmitting] = useState(false);
  const { showToast } = useNotification();

  const fetchInventory = async () => {
    setLoading(true);
    try {
      if (activeTab === 'overview') {
        const res = await inventoryApi.getAll({ page });
        setInventoryList(res.data.results || res.data || []);
        setCount(res.data.count || (res.data || []).length);
      } else {
        const res = await inventoryApi.getMovements({ page });
        setMovementList(res.data.results || res.data || []);
        setCount(res.data.count || (res.data || []).length);
      }
    } catch (err) {
      showToast('Failed to load inventory data.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchProducts = async () => {
    try {
      const items = await fetchAllPages((params) => productApi.getAll(params));
      setProducts(items);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  useEffect(() => {
    fetchInventory();
  }, [activeTab, page]);

  // Edit stock limits
  const handleOpenEditModal = (inv) => {
    setSelectedInventory(inv);
    setEditForm({
      quantity: inv.quantity,
      minimum_stock: inv.minimum_stock,
      maximum_stock: inv.maximum_stock,
    });
    setIsEditModalOpen(true);
  };

  const handleUpdateStockLimits = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await inventoryApi.update(selectedInventory.id, editForm);
      showToast('Stock limits updated successfully!', 'success');
      setIsEditModalOpen(false);
      fetchInventory();
    } catch (err) {
      showToast('Failed to update stock limits.', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  // Create Stock Movement / Adjustment
  const handleOpenAdjustmentModal = () => {
    setAdjustmentForm({
      product: products.length > 0 ? products[0].id : '',
      movement_type: 'ADJUSTMENT',
      quantity: 1,
      remarks: '',
    });
    setIsAdjustmentModalOpen(true);
  };

  const handleCreateAdjustment = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await inventoryApi.createMovement(adjustmentForm);
      showToast('Stock movement logged successfully!', 'success');
      setIsAdjustmentModalOpen(false);
      fetchInventory();
    } catch (err) {
      showToast('Failed to record stock movement.', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <div className="flex-between mb-6">
        <div>
          <h1 className="page-title">Inventory & Stock Tracking</h1>
          <p className="page-subtitle">Monitor product quantities, stock thresholds, and movement audit logs</p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button className="btn btn-secondary" onClick={() => fetchInventory()}>
            <RefreshCw size={16} /> Refresh
          </button>
          <button className="btn btn-primary" onClick={handleOpenAdjustmentModal}>
            <Sliders size={16} /> Record Adjustment
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
        <button
          className={`btn ${activeTab === 'overview' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => { setActiveTab('overview'); setPage(1); }}
        >
          <Boxes size={18} /> Stock Overview
        </button>
        <button
          className={`btn ${activeTab === 'history' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => { setActiveTab('history'); setPage(1); }}
        >
          <History size={18} /> Movement Logs
        </button>
      </div>

      {/* Content */}
      <div className="glass-card">
        {loading ? (
          <Loader text="Loading inventory metrics..." />
        ) : activeTab === 'overview' ? (
          <>
            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Available Quantity</th>
                    <th>Min Threshold</th>
                    <th>Max Limit</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {inventoryList.map((inv) => (
                    <tr key={inv.id}>
                      <td style={{ fontWeight: 600 }}>{inv.product_name}</td>
                      <td style={{ fontSize: '1rem', fontWeight: 700 }}>
                        {inv.quantity} units
                      </td>
                      <td>{inv.minimum_stock}</td>
                      <td>{inv.maximum_stock}</td>
                      <td>
                        <span className={`badge ${getStockBadgeClass(inv.stock_status)}`}>
                          {inv.stock_status}
                        </span>
                      </td>
                      <td>
                        <button
                          className="btn btn-secondary btn-icon btn-sm"
                          onClick={() => handleOpenEditModal(inv)}
                          title="Edit Stock Thresholds"
                        >
                          <Edit2 size={15} color="var(--accent-secondary)" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination count={count} page={page} onPageChange={setPage} pageSize={10} />
          </>
        ) : (
          <>
            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Date & Time</th>
                    <th>Product</th>
                    <th>Type</th>
                    <th>Quantity</th>
                    <th>Remarks</th>
                    <th>Logged By</th>
                  </tr>
                </thead>
                <tbody>
                  {movementList.map((m) => (
                    <tr key={m.id}>
                      <td style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                        {formatDateTime(m.created_at)}
                      </td>
                      <td style={{ fontWeight: 600 }}>{m.product_name}</td>
                      <td>
                        <span className={`badge ${
                          m.movement_type === 'IN' ? 'badge-success' :
                          m.movement_type === 'OUT' ? 'badge-danger' : 'badge-info'
                        }`}>
                          {m.movement_type === 'IN' && <ArrowDownLeft size={12} />}
                          {m.movement_type === 'OUT' && <ArrowUpRight size={12} />}
                          {m.movement_type}
                        </span>
                      </td>
                      <td style={{ fontWeight: 700 }}>{m.quantity}</td>
                      <td style={{ color: 'var(--text-muted)' }}>{m.remarks || '-'}</td>
                      <td style={{ fontSize: '0.8125rem' }}>{m.created_by_name || 'System'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination count={count} page={page} onPageChange={setPage} pageSize={10} />
          </>
        )}
      </div>

      {/* Edit Limits Modal */}
      <Modal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        title={`Adjust Stock Limits - ${selectedInventory?.product_name}`}
      >
        <form onSubmit={handleUpdateStockLimits}>
          <div className="form-group mb-4">
            <label className="form-label">Current Stock Quantity</label>
            <input
              type="number"
              className="form-input"
              value={editForm.quantity}
              onChange={(e) => setEditForm({ ...editForm, quantity: parseInt(e.target.value) || 0 })}
              required
            />
          </div>

          <div className="grid-2 mb-6">
            <div className="form-group">
              <label className="form-label">Minimum Stock Alert Limit</label>
              <input
                type="number"
                className="form-input"
                value={editForm.minimum_stock}
                onChange={(e) => setEditForm({ ...editForm, minimum_stock: parseInt(e.target.value) || 0 })}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Maximum Capacity Limit</label>
              <input
                type="number"
                className="form-input"
                value={editForm.maximum_stock}
                onChange={(e) => setEditForm({ ...editForm, maximum_stock: parseInt(e.target.value) || 0 })}
                required
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setIsEditModalOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Updating...' : 'Save Stock Thresholds'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Manual Movement Modal */}
      <Modal
        isOpen={isAdjustmentModalOpen}
        onClose={() => setIsAdjustmentModalOpen(false)}
        title="Log Manual Stock Movement"
      >
        <form onSubmit={handleCreateAdjustment}>
          <div className="form-group">
            <label className="form-label">Select Product *</label>
            <select
              className="form-select"
              value={adjustmentForm.product}
              onChange={(e) => setAdjustmentForm({ ...adjustmentForm, product: e.target.value })}
              required
            >
              {products.map((p) => (
                <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>
              ))}
            </select>
          </div>

          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">Movement Type *</label>
              <select
                className="form-select"
                value={adjustmentForm.movement_type}
                onChange={(e) => setAdjustmentForm({ ...adjustmentForm, movement_type: e.target.value })}
              >
                <option value="IN">Stock In (+)</option>
                <option value="OUT">Stock Out (-)</option>
                <option value="ADJUSTMENT">Adjustment (Manual)</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Quantity *</label>
              <input
                type="number"
                min="1"
                className="form-input"
                value={adjustmentForm.quantity}
                onChange={(e) => setAdjustmentForm({ ...adjustmentForm, quantity: parseInt(e.target.value) || 1 })}
                required
              />
            </div>
          </div>

          <div className="form-group mb-6">
            <label className="form-label">Remarks / Reason</label>
            <textarea
              className="form-textarea"
              rows={2}
              placeholder="e.g. Damaged items return, Physical audit adjustment..."
              value={adjustmentForm.remarks}
              onChange={(e) => setAdjustmentForm({ ...adjustmentForm, remarks: e.target.value })}
            />
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setIsAdjustmentModalOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Recording...' : 'Record Movement'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
