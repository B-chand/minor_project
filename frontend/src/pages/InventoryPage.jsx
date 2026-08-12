import React, { useEffect, useState } from 'react';
import { Boxes, History, Edit2, Plus, ArrowUpRight, ArrowDownLeft, Sliders, RefreshCw, Search, Filter, PackageOpen } from 'lucide-react';
import { inventoryApi, categoryApi, productApi, fetchAllPages } from '../api';
import { Modal, Loader, Pagination } from '../components/common/UIComponents';
import { useNotification } from '../context/NotificationContext';
import { getStockBadgeClass, formatDateTime } from '../utils/formatters';

const ADJUSTMENT_REASONS = ['Correction', 'Damaged', 'Lost', 'Found', 'Physical Count', 'Other'];

export const InventoryPage = () => {
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'history'
  const [inventoryList, setInventoryList] = useState([]);
  const [movementList, setMovementList] = useState([]);
  const [categories, setCategories] = useState([]);

  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const [search, setSearch] = useState('');
  const [appliedSearch, setAppliedSearch] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [filterStatus, setFilterStatus] = useState('');

  // Edit thresholds modal
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [selectedInventory, setSelectedInventory] = useState(null);
  const [editForm, setEditForm] = useState({ minimum_stock: 10, maximum_stock: 1000 });

  // Adjustment modal state
  const [isAdjustmentModalOpen, setIsAdjustmentModalOpen] = useState(false);
  const [inventoryOptions, setInventoryOptions] = useState([]);
  const [adjustmentForm, setAdjustmentForm] = useState({
    inventory_id: '',
    adjustment: '',
    reason: 'Correction',
    note: '',
  });

  const [submitting, setSubmitting] = useState(false);
  const { showToast } = useNotification();

  // Opening stock modal state
  const [isOpeningStockModalOpen, setIsOpeningStockModalOpen] = useState(false);
  const [productOptions, setProductOptions] = useState([]);
  const [productInventoryMap, setProductInventoryMap] = useState({});
  const [openingForm, setOpeningForm] = useState({ product: '', quantity: '', note: '' });
  const [openingSubmitting, setOpeningSubmitting] = useState(false);

  const fetchInventory = async () => {
    setLoading(true);
    try {
      if (activeTab === 'overview') {
        const params = {
          page,
          search: appliedSearch || undefined,
          'product__category': filterCategory || undefined,
          stock_status: filterStatus || undefined,
        };
        const res = await inventoryApi.getAll(params);
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

  const fetchCategories = async () => {
    try {
      const items = await fetchAllPages((params) => categoryApi.getAll(params));
      setCategories(items);
    } catch (err) {
      console.error('Failed to load categories:', err);
    }
  };

  useEffect(() => {
    fetchCategories();
  }, []);

  useEffect(() => {
    fetchInventory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, page, filterCategory, filterStatus, appliedSearch]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setAppliedSearch(search.trim());
    setPage(1);
  };

  // Edit stock limits (thresholds only; quantity changes happen via adjustments)
  const handleOpenEditModal = (inv) => {
    setSelectedInventory(inv);
    setEditForm({
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
      showToast('Stock thresholds updated successfully!', 'success');
      setIsEditModalOpen(false);
      fetchInventory();
    } catch (err) {
      showToast('Failed to update stock thresholds.', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  // Stock adjustment
  const openAdjustmentModal = async (inventory = null) => {
    let options;
    try {
      options = await fetchAllPages((params) => inventoryApi.getAll(params));
    } catch (err) {
      options = inventoryList;
    }
    setInventoryOptions(options);
    setAdjustmentForm({
      inventory_id: inventory ? inventory.id : (options.length > 0 ? options[0].id : ''),
      adjustment: '',
      reason: 'Correction',
      note: '',
    });
    setIsAdjustmentModalOpen(true);
  };

  const selectedAdjustInventory = inventoryOptions.find(
    (i) => Number(i.id) === Number(adjustmentForm.inventory_id)
  );

  const hasValidAdjustment = /^-?\d+$/.test(adjustmentForm.adjustment.trim());
  const adjustNumber = hasValidAdjustment ? parseInt(adjustmentForm.adjustment, 10) : NaN;
  const previewNew = selectedAdjustInventory && hasValidAdjustment
    ? selectedAdjustInventory.quantity + adjustNumber
    : NaN;
  const previewInvalid = selectedAdjustInventory && hasValidAdjustment && previewNew < 0;

  // Opening stock
  const openOpeningStockModal = async () => {
    try {
      const [products, inventory] = await Promise.all([
        fetchAllPages((params) => productApi.getAll(params)),
        fetchAllPages((params) => inventoryApi.getAll(params)),
      ]);
      const invMap = {};
      inventory.forEach((inv) => { invMap[inv.product] = inv.quantity; });
      setProductOptions(products);
      setProductInventoryMap(invMap);
      setOpeningForm({
        product: products.length > 0 ? products[0].id : '',
        quantity: '',
        note: '',
      });
      setIsOpeningStockModalOpen(true);
    } catch {
      showToast('Failed to load products for opening stock.', 'error');
    }
  };

  const selectedOpeningProduct = productOptions.find(
    (p) => Number(p.id) === Number(openingForm.product)
  );

  const handleCreateOpeningStock = async (e) => {
    e.preventDefault();

    if (!openingForm.product) {
      showToast('Please select a product.', 'error');
      return;
    }
    const qty = parseInt(openingForm.quantity, 10);
    if (!openingForm.quantity || isNaN(qty) || qty <= 0) {
      showToast('Please enter a positive whole number for the opening quantity.', 'error');
      return;
    }

    setOpeningSubmitting(true);
    try {
      await inventoryApi.createMovement({
        product: openingForm.product,
        movement_type: 'IN',
        quantity: qty,
        remarks: openingForm.note.trim() ? `Opening stock entry: ${openingForm.note.trim()}` : 'Opening stock entry',
      });
      showToast('Opening stock recorded successfully!', 'success');
      setIsOpeningStockModalOpen(false);
      fetchInventory();
    } catch (err) {
      const data = err.response?.data;
      let msg = 'Failed to record opening stock.';
      if (data && typeof data === 'object') {
        const keys = Object.keys(data);
        if (keys.length > 0) {
          const first = data[keys[0]];
          msg = Array.isArray(first) ? first[0] : (typeof first === 'string' ? first : msg);
        }
      }
      showToast(msg, 'error');
    } finally {
      setOpeningSubmitting(false);
    }
  };

  const handleCreateAdjustment = async (e) => {
    e.preventDefault();

    if (!adjustmentForm.inventory_id) {
      showToast('Please select a product.', 'error');
      return;
    }
    if (!hasValidAdjustment) {
      showToast('Please enter a valid whole number for the adjustment.', 'error');
      return;
    }
    if (previewInvalid) {
      showToast('This adjustment would take stock below zero.', 'error');
      return;
    }

    setSubmitting(true);
    try {
      await inventoryApi.adjust(adjustmentForm.inventory_id, {
        adjustment: adjustNumber,
        reason: adjustmentForm.reason,
        note: adjustmentForm.note,
      });
      showToast('Stock adjustment recorded successfully!', 'success');
      setIsAdjustmentModalOpen(false);
      fetchInventory();
    } catch (err) {
      const data = err.response?.data;
      let msg = 'Failed to adjust stock.';
      if (data && typeof data === 'object') {
        const keys = Object.keys(data);
        if (keys.length > 0) {
          const first = data[keys[0]];
          msg = Array.isArray(first) ? first[0] : (typeof first === 'string' ? first : msg);
        }
      }
      showToast(msg, 'error');
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
          <button className="btn btn-secondary" onClick={() => openOpeningStockModal()}>
            <PackageOpen size={16} /> Opening Stock
          </button>
          <button className="btn btn-primary" onClick={() => openAdjustmentModal()}>
            <Sliders size={16} /> Adjust Stock
          </button>
        </div>
      </div>

      {/* How stock changes - workflow guide */}
      <div className="glass-card mb-6">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.25rem', alignItems: 'center', fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
          <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>How stock changes:</span>
          <span>Opening Stock &amp; Purchases add stock.</span>
          <span>Sales remove stock.</span>
          <span>Stock Adjustments correct discrepancies (damaged, lost, found, counts).</span>
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

      {activeTab === 'overview' ? (
        <>
          {/* Filter & Search Bar */}
          <div className="glass-card mb-6">
            <form onSubmit={handleSearchSubmit} className="flex-between" style={{ gap: '1rem', flexWrap: 'wrap' }}>
              <div style={{ position: 'relative', flex: 1, minWidth: '240px' }}>
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
                  placeholder="Search by product name, SKU, barcode, category..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                <Filter size={18} color="var(--text-muted)" />
                <select
                  className="form-select"
                  style={{ width: '200px' }}
                  value={filterCategory}
                  onChange={(e) => { setFilterCategory(e.target.value); setPage(1); }}
                >
                  <option value="">All Categories</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
                <select
                  className="form-select"
                  style={{ width: '180px' }}
                  value={filterStatus}
                  onChange={(e) => { setFilterStatus(e.target.value); setPage(1); }}
                >
                  <option value="">All Stock Levels</option>
                  <option value="in">In Stock</option>
                  <option value="low">Low Stock</option>
                  <option value="out">Out of Stock</option>
                </select>
                <button type="submit" className="btn btn-secondary">
                  Search
                </button>
              </div>
            </form>
          </div>

          <div className="glass-card">
            {loading ? (
              <Loader text="Loading inventory metrics..." />
            ) : inventoryList.length === 0 ? (
              <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                No inventory records found matching the current filters.
              </div>
            ) : (
              <>
                <div className="table-responsive">
                  <table className="custom-table">
                    <thead>
                      <tr>
                        <th>Product</th>
                        <th>SKU</th>
                        <th>Category</th>
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
                          <td style={{ fontSize: '0.8125rem', fontFamily: 'monospace' }}>{inv.product_sku}</td>
                          <td>
                            <span className="badge badge-info">{inv.category_name || 'Uncategorized'}</span>
                          </td>
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
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                              <button
                                className="btn btn-secondary btn-icon btn-sm"
                                onClick={() => openAdjustmentModal(inv)}
                                title="Adjust Stock"
                              >
                                <Sliders size={15} color="var(--accent-primary)" />
                              </button>
                              <button
                                className="btn btn-secondary btn-icon btn-sm"
                                onClick={() => handleOpenEditModal(inv)}
                                title="Edit Stock Thresholds"
                              >
                                <Edit2 size={15} color="var(--accent-secondary)" />
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
        </>
      ) : (
        <div className="glass-card">
          {loading ? (
            <Loader text="Loading movement logs..." />
          ) : movementList.length === 0 ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              No stock movements recorded yet.
            </div>
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
      )}

      {/* Edit Stock & Thresholds Modal */}
      <Modal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        title={`Edit Stock Thresholds - ${selectedInventory?.product_name || ''}`}
      >
        <form onSubmit={handleUpdateStockLimits}>
          <div
            className="flex-between mb-4"
            style={{ background: 'var(--bg-tertiary)', borderRadius: '8px', padding: '0.75rem 1rem' }}
          >
            <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>Current Stock Quantity</span>
            <span style={{ fontWeight: 700 }}>
              {selectedInventory?.quantity ?? 0} units
            </span>
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

          <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
            These values only set alert thresholds. To add stock, use Opening Stock or a Purchase.
            To correct a quantity discrepancy, use Adjust Stock — both are recorded in the audit log.
          </p>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setIsEditModalOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Updating...' : 'Save Thresholds'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Stock Adjustment Modal */}
      <Modal
        isOpen={isAdjustmentModalOpen}
        onClose={() => setIsAdjustmentModalOpen(false)}
        title="Adjust Stock"
        maxWidth="580px"
      >
        <form onSubmit={handleCreateAdjustment}>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
            Stock Adjustment corrects the actual stock quantity when it differs from the system quantity.
            The change is signed (+ adds, - removes), recorded as a movement, and logged to the audit trail.
          </p>
          <div className="form-group mb-4">
            <label className="form-label">Select Product *</label>
            <select
              className="form-select"
              value={adjustmentForm.inventory_id}
              onChange={(e) => setAdjustmentForm({ ...adjustmentForm, inventory_id: e.target.value })}
              required
            >
              <option value="" disabled>Select product...</option>
              {inventoryOptions.map((i) => (
                <option key={i.id} value={i.id}>{i.product_name} ({i.product_sku})</option>
              ))}
            </select>
          </div>

          {selectedAdjustInventory && (
            <div
              className="flex-between mb-4"
              style={{ background: 'var(--bg-tertiary)', borderRadius: '8px', padding: '0.75rem 1rem' }}
            >
              <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>Current Stock</span>
              <span style={{ fontWeight: 700 }}>{selectedAdjustInventory.quantity} units</span>
            </div>
          )}

          {selectedAdjustInventory && hasValidAdjustment && (
            <div
              className="flex-between mb-4"
              style={{
                background: previewInvalid ? 'var(--status-danger)' : 'var(--status-success)',
                borderRadius: '8px',
                padding: '0.75rem 1rem',
                color: '#fff',
              }}
            >
              <span>New Stock After Adjustment</span>
              <span style={{ fontWeight: 700 }}>
                {previewInvalid ? 'Below zero - blocked' : `${previewNew} units`}
              </span>
            </div>
          )}

          <div className="form-group mb-4">
            <label className="form-label">
              Adjustment Amount (positive adds stock, negative removes stock) *
            </label>
            <input
              type="number"
              step="1"
              className="form-input"
              placeholder="e.g. -3 or +5"
              value={adjustmentForm.adjustment}
              onChange={(e) => setAdjustmentForm({ ...adjustmentForm, adjustment: e.target.value })}
              required
            />
          </div>

          <div className="form-group mb-4">
            <label className="form-label">Reason *</label>
            <select
              className="form-select"
              value={adjustmentForm.reason}
              onChange={(e) => setAdjustmentForm({ ...adjustmentForm, reason: e.target.value })}
            >
              {ADJUSTMENT_REASONS.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>

          {adjustmentForm.reason === 'Other' ? (
            <div className="form-group mb-6">
              <label className="form-label">Note (required for "Other") *</label>
              <textarea
                className="form-textarea"
                rows={2}
                placeholder="Describe why this adjustment is needed..."
                value={adjustmentForm.note}
                onChange={(e) => setAdjustmentForm({ ...adjustmentForm, note: e.target.value })}
                required
                minLength={5}
              />
            </div>
          ) : (
            <div className="form-group mb-6">
              <label className="form-label">Additional Note (optional)</label>
              <textarea
                className="form-textarea"
                rows={2}
                placeholder="Optional context for this adjustment..."
                value={adjustmentForm.note}
                onChange={(e) => setAdjustmentForm({ ...adjustmentForm, note: e.target.value })}
              />
            </div>
          )}

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setIsAdjustmentModalOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              <Plus size={16} /> {submitting ? 'Adjusting...' : 'Confirm Adjustment'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Opening Stock Modal */}
      <Modal
        isOpen={isOpeningStockModalOpen}
        onClose={() => setIsOpeningStockModalOpen(false)}
        title="Enter Opening Stock"
        maxWidth="580px"
      >
        <form onSubmit={handleCreateOpeningStock}>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
            Used to enter the initial/current stock quantity for a product. This records an audited stock-in movement.
          </p>

          <div className="form-group mb-4">
            <label className="form-label">Select Product *</label>
            <select
              className="form-select"
              value={openingForm.product}
              onChange={(e) => setOpeningForm({ ...openingForm, product: e.target.value })}
              required
            >
              <option value="" disabled>Select product...</option>
              {productOptions.map((p) => (
                <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>
              ))}
            </select>
          </div>

          {selectedOpeningProduct && (
            <div
              className="flex-between mb-4"
              style={{ background: 'var(--bg-tertiary)', borderRadius: '8px', padding: '0.75rem 1rem' }}
            >
              <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>Current On-Hand Stock</span>
              <span style={{ fontWeight: 700 }}>
                {productInventoryMap[Number(openingForm.product)] !== undefined
                  ? `${productInventoryMap[Number(openingForm.product)]} units`
                  : 'No stock yet'}
              </span>
            </div>
          )}

          <div className="form-group mb-4">
            <label className="form-label">Opening Quantity (units) *</label>
            <input
              type="number"
              min="1"
              step="1"
              className="form-input"
              placeholder="e.g. 50"
              value={openingForm.quantity}
              onChange={(e) => setOpeningForm({ ...openingForm, quantity: e.target.value })}
              required
            />
          </div>

          <div className="form-group mb-6">
            <label className="form-label">Note (optional)</label>
            <textarea
              className="form-textarea"
              rows={2}
              placeholder="Optional context, e.g. manual count on setup day..."
              value={openingForm.note}
              onChange={(e) => setOpeningForm({ ...openingForm, note: e.target.value })}
            />
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setIsOpeningStockModalOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={openingSubmitting}>
              <Plus size={16} /> {openingSubmitting ? 'Saving...' : 'Save Opening Stock'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};