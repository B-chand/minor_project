import React, { useCallback, useEffect, useState } from 'react';
import { Plus, Eye, Trash2, PlusCircle, MinusCircle } from 'lucide-react';
import { purchaseApi, supplierApi, productApi, fetchAllPages } from '../api';
import { Modal, Loader, Pagination } from '../components/common/UIComponents';
import { useNotification } from '../context/NotificationContext';
import { formatCurrency, formatDate } from '../utils/formatters';

export const PurchasesPage = () => {
  const [purchases, setPurchases] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [products, setProducts] = useState([]);
  
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  // Detail Modal
  const [selectedPurchase, setSelectedPurchase] = useState(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

  // New Purchase Form Modal
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [headerForm, setHeaderForm] = useState({
    supplier: '',
    invoice_number: '',
    purchase_date: new Date().toISOString().split('T')[0],
    status: 'Completed',
    notes: '',
  });
  const [itemsForm, setItemsForm] = useState([
    { product: '', quantity: 1, unit_price: 0 },
  ]);
  const [submitting, setSubmitting] = useState(false);

  const { showToast } = useNotification();

  const fetchPurchases = useCallback(async () => {
    setLoading(true);
    try {
      const res = await purchaseApi.getAll({ page });
      setPurchases(res.data.results || res.data || []);
      setCount(res.data.count || (res.data || []).length);
    } catch {
      showToast('Failed to load purchase records.', 'error');
    } finally {
      setLoading(false);
    }
  }, [page, showToast]);

  const fetchDependencies = useCallback(async () => {
    try {
      const [suppliersList, productsList] = await Promise.all([
        fetchAllPages((params) => supplierApi.getAll(params)),
        fetchAllPages((params) => productApi.getAll(params)),
      ]);
      setSuppliers(suppliersList);
      setProducts(productsList);
    } catch {
      console.error('Failed to load purchase dependencies.');
    }
  }, []);

  useEffect(() => {
    fetchDependencies();
  }, [fetchDependencies]);

  useEffect(() => {
    fetchPurchases();
  }, [fetchPurchases]);

  const handleOpenCreateModal = () => {
    setHeaderForm({
      supplier: suppliers.length > 0 ? suppliers[0].id : '',
      invoice_number: `PO-${Math.floor(100000 + Math.random() * 900000)}`,
      purchase_date: new Date().toISOString().split('T')[0],
      status: 'Completed',
      notes: '',
    });
    setItemsForm([
      {
        product: products.length > 0 ? products[0].id : '',
        quantity: 1,
        unit_price: products.length > 0 ? products[0].buying_price : 0,
      },
    ]);
    setIsCreateModalOpen(true);
  };

  const handleAddItemRow = () => {
    const firstProd = products[0];
    setItemsForm((prev) => [
      ...prev,
      {
        product: firstProd ? firstProd.id : '',
        quantity: 1,
        unit_price: firstProd ? firstProd.buying_price : 0,
      },
    ]);
  };

  const handleRemoveItemRow = (index) => {
    if (itemsForm.length === 1) return;
    setItemsForm((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleItemChange = (index, field, value) => {
    setItemsForm((prev) => {
      const updated = [...prev];
      updated[index][field] = value;

      if (field === 'product') {
        const selectedProd = products.find((p) => p.id === value);
        if (selectedProd) {
          updated[index].unit_price = selectedProd.buying_price;
        }
      }
      return updated;
    });
  };

  const handleSubmitPurchase = async (e) => {
    e.preventDefault();

    if (!headerForm.supplier) {
      showToast('Please select a supplier.', 'error');
      return;
    }
    if (itemsForm.some((i) => !i.product || i.quantity <= 0)) {
      showToast('Please select valid products and positive quantities for all items.', 'error');
      return;
    }

    setSubmitting(true);
    try {
      // Step 1: Create Purchase Header
      const headerRes = await purchaseApi.create(headerForm);
      const purchaseId = headerRes.data.id;

      // Step 2: Create Purchase Items sequentially
      for (const item of itemsForm) {
        await purchaseApi.addItem({
          purchase: purchaseId,
          product: item.product,
          quantity: parseInt(item.quantity),
          unit_price: parseFloat(item.unit_price),
        });
      }

      showToast('Purchase order and stock inventory saved successfully!', 'success');
      setIsCreateModalOpen(false);
      fetchPurchases();
    } catch (err) {
      console.error('Purchase creation error:', err);
      const msg = err.response?.data?.detail || err.response?.data?.invoice_number?.[0] || 'Failed to create purchase order.';
      showToast(msg, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleViewDetails = async (id) => {
    try {
      const res = await purchaseApi.getOne(id);
      setSelectedPurchase(res.data);
      setIsDetailModalOpen(true);
    } catch {
      showToast('Failed to load purchase details.', 'error');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this purchase record?')) return;
    try {
      await purchaseApi.delete(id);
      showToast('Purchase record deleted.', 'success');
      fetchPurchases();
    } catch {
      showToast('Cannot delete purchase.', 'error');
    }
  };

  return (
    <div>
      <div className="flex-between mb-6">
        <div>
          <h1 className="page-title">Purchase Management</h1>
          <p className="page-subtitle">Record stock purchases from suppliers and auto-increment inventory</p>
        </div>
        <button className="btn btn-primary" onClick={handleOpenCreateModal}>
          <Plus size={18} /> New Purchase Order
        </button>
      </div>

      <div className="glass-card">
        {loading ? (
          <Loader text="Loading purchase history..." />
        ) : purchases.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            No purchase records found. Click "New Purchase Order" to log stock addition.
          </div>
        ) : (
          <>
            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Invoice Number</th>
                    <th>Supplier</th>
                    <th>Date</th>
                    <th>Total Amount</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {purchases.map((p) => (
                    <tr key={p.id}>
                      <td style={{ fontWeight: 600, color: 'var(--text-main)' }}>{p.invoice_number}</td>
                      <td>{p.supplier_name || 'Supplier'}</td>
                      <td style={{ color: 'var(--text-muted)' }}>{formatDate(p.purchase_date)}</td>
                      <td style={{ fontWeight: 700, color: 'var(--status-info)' }}>
                        {formatCurrency(p.total_amount)}
                      </td>
                      <td>
                        <span className={`badge ${
                          p.status === 'Completed' ? 'badge-success' :
                          p.status === 'Pending' ? 'badge-warning' : 'badge-danger'
                        }`}>
                          {p.status}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button
                            className="btn btn-secondary btn-icon btn-sm"
                            onClick={() => handleViewDetails(p.id)}
                            title="View Details"
                          >
                            <Eye size={15} color="var(--accent-primary)" />
                          </button>
                          <button
                            className="btn btn-secondary btn-icon btn-sm"
                            onClick={() => handleDelete(p.id)}
                            title="Delete Record"
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

      {/* View Detail Modal */}
      <Modal
        isOpen={isDetailModalOpen}
        onClose={() => setIsDetailModalOpen(false)}
        title={`Purchase Order: ${selectedPurchase?.invoice_number}`}
        maxWidth="650px"
      >
        {selectedPurchase && (
          <div>
            <div className="grid-2 mb-4">
              <div>
                <span className="form-label">Supplier Name</span>
                <div style={{ fontWeight: 600, marginTop: '0.2rem' }}>{selectedPurchase.supplier_name}</div>
              </div>
              <div>
                <span className="form-label">Purchase Date</span>
                <div style={{ marginTop: '0.2rem' }}>{formatDate(selectedPurchase.purchase_date)}</div>
              </div>
            </div>

            <h4 style={{ fontSize: '0.9375rem', marginBottom: '0.75rem', color: 'var(--accent-secondary)' }}>
              Purchased Product Items
            </h4>
            <div className="table-responsive mb-4">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Qty</th>
                    <th>Unit Price</th>
                    <th>Subtotal</th>
                  </tr>
                </thead>
                <tbody>
                  {(selectedPurchase.items || []).map((item) => (
                    <tr key={item.id}>
                      <td style={{ fontWeight: 500 }}>{item.product_name}</td>
                      <td>{item.quantity}</td>
                      <td>{formatCurrency(item.unit_price)}</td>
                      <td style={{ fontWeight: 600 }}>{formatCurrency(item.subtotal)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex-between" style={{ padding: '1rem', background: 'var(--bg-primary)', borderRadius: 'var(--radius-md)' }}>
              <span style={{ fontWeight: 600 }}>Grand Total:</span>
              <span style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--status-info)' }}>
                {formatCurrency(selectedPurchase.total_amount)}
              </span>
            </div>
          </div>
        )}
      </Modal>

      {/* Create Purchase Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create Purchase Order"
        maxWidth="750px"
      >
        <form onSubmit={handleSubmitPurchase}>
          <div className="grid-2 mb-4">
            <div className="form-group">
              <label className="form-label">Supplier *</label>
              <select
                className="form-select"
                value={headerForm.supplier}
                onChange={(e) => setHeaderForm({ ...headerForm, supplier: e.target.value })}
                required
              >
                <option value="">Select Supplier</option>
                {suppliers.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Invoice / Order # *</label>
              <input
                type="text"
                className="form-input"
                value={headerForm.invoice_number}
                onChange={(e) => setHeaderForm({ ...headerForm, invoice_number: e.target.value })}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Purchase Date *</label>
              <input
                type="date"
                className="form-input"
                value={headerForm.purchase_date}
                onChange={(e) => setHeaderForm({ ...headerForm, purchase_date: e.target.value })}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Status</label>
              <select
                className="form-select"
                value={headerForm.status}
                onChange={(e) => setHeaderForm({ ...headerForm, status: e.target.value })}
              >
                <option value="Completed">Completed (Update Stock Now)</option>
                <option value="Pending">Pending</option>
              </select>
            </div>
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <div className="flex-between mb-2">
              <label className="form-label" style={{ fontSize: '0.9375rem', fontWeight: 600, color: 'var(--accent-primary)' }}>
                Order Items
              </label>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={handleAddItemRow}
              >
                <PlusCircle size={14} /> Add Line Item
              </button>
            </div>

            {itemsForm.map((item, index) => (
              <div key={index} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 40px', gap: '0.75rem', alignItems: 'center', marginBottom: '0.75rem' }}>
                <select
                  className="form-select"
                  value={item.product}
                  onChange={(e) => handleItemChange(index, 'product', e.target.value)}
                  required
                >
                  <option value="">Select Product</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>
                  ))}
                </select>

                <input
                  type="number"
                  min="1"
                  className="form-input"
                  placeholder="Qty"
                  value={item.quantity}
                  onChange={(e) => handleItemChange(index, 'quantity', e.target.value)}
                  required
                />

                <input
                  type="number"
                  step="0.01"
                  className="form-input"
                  placeholder="Cost"
                  value={item.unit_price}
                  onChange={(e) => handleItemChange(index, 'unit_price', e.target.value)}
                  required
                />

                <button
                  type="button"
                  onClick={() => handleRemoveItemRow(index)}
                  style={{ background: 'none', border: 'none', color: 'var(--status-danger)', cursor: 'pointer' }}
                  disabled={itemsForm.length === 1}
                >
                  <MinusCircle size={18} />
                </button>
              </div>
            ))}
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setIsCreateModalOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Saving Order...' : 'Submit Purchase Order'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
