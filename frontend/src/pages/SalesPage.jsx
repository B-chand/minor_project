import React, { useCallback, useEffect, useState } from 'react';
import { Plus, Eye, Trash2, PlusCircle, MinusCircle } from 'lucide-react';
import { saleApi, customerApi, productApi, inventoryApi, fetchAllPages } from '../api';
import { Modal, Loader, Pagination } from '../components/common/UIComponents';
import { useNotification } from '../context/NotificationContext';
import { formatCurrency, formatDate } from '../utils/formatters';

export const SalesPage = () => {
  const [sales, setSales] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [products, setProducts] = useState([]);
  const [inventoryMap, setInventoryMap] = useState({});
  
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  // Detail Modal
  const [selectedSale, setSelectedSale] = useState(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

  // Create Modal
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [headerForm, setHeaderForm] = useState({
    customer: '',
    invoice_number: '',
    sale_date: new Date().toISOString().split('T')[0],
    payment_status: 'Paid',
    notes: '',
  });
  const [itemsForm, setItemsForm] = useState([
    { product: '', quantity: 1, unit_price: 0 },
  ]);
  const [submitting, setSubmitting] = useState(false);

  const { showToast } = useNotification();

  const fetchSales = useCallback(async () => {
    setLoading(true);
    try {
      const res = await saleApi.getAll({ page });
      setSales(res.data.results || res.data || []);
      setCount(res.data.count || (res.data || []).length);
    } catch {
      showToast('Failed to load sales history.', 'error');
    } finally {
      setLoading(false);
    }
  }, [page, showToast]);

  const fetchDependencies = useCallback(async () => {
    try {
      const [custList, prodList, invList] = await Promise.all([
        fetchAllPages((params) => customerApi.getAll(params)),
        fetchAllPages((params) => productApi.getAll(params)),
        fetchAllPages((params) => inventoryApi.getAll(params)),
      ]);
      setProducts(prodList);

      setCustomers(custList);

      const map = {};
      invList.forEach((item) => {
        if (item.product) {
          map[item.product] = item.quantity;
        }
      });
      setInventoryMap(map);
    } catch (err) {
      console.error(err);
    }
  }, []);

  useEffect(() => {
    fetchDependencies();
  }, [fetchDependencies]);

  useEffect(() => {
    fetchSales();
  }, [fetchSales]);

  const handleOpenCreateModal = () => {
    setHeaderForm({
      customer: customers.length > 0 ? customers[0].id : '',
      invoice_number: `INV-${Math.floor(100000 + Math.random() * 900000)}`,
      sale_date: new Date().toISOString().split('T')[0],
      payment_status: 'Paid',
      notes: '',
    });

    const firstProd = products[0];
    setItemsForm([
      {
        product: firstProd ? firstProd.id : '',
        quantity: 1,
        unit_price: firstProd ? firstProd.selling_price : 0,
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
        unit_price: firstProd ? firstProd.selling_price : 0,
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
          updated[index].unit_price = selectedProd.selling_price;
        }
      }
      return updated;
    });
  };

  const handleSubmitSale = async (e) => {
    e.preventDefault();

    // Check stock availability
    for (const item of itemsForm) {
      const available = inventoryMap[item.product] || 0;
      if (item.quantity > available) {
        const prod = products.find((p) => p.id === item.product);
        showToast(
          `Insufficient stock for "${prod?.name || 'product'}". Only ${available} available.`,
          'error'
        );
        return;
      }
    }

    setSubmitting(true);
    try {
      // Step 1: Create Sale Header
      const headerData = { ...headerForm };
      if (!headerData.customer) delete headerData.customer; // Handle walk-in customer

      const headerRes = await saleApi.create(headerData);
      const saleId = headerRes.data.id;

      // Step 2: Create Sale Items sequentially
      for (const item of itemsForm) {
        await saleApi.addItem({
          sale: saleId,
          product: item.product,
          quantity: parseInt(item.quantity),
          unit_price: parseFloat(item.unit_price),
        });
      }

      showToast('Sale order completed and inventory updated!', 'success');
      setIsCreateModalOpen(false);
      fetchDependencies();
      fetchSales();
    } catch (err) {
      console.error('Sale creation error:', err);
      const errors = err.response?.data;
      let msg = 'Failed to create sale order.';
      if (typeof errors === 'object') {
        const firstKey = Object.keys(errors)[0];
        msg = `${firstKey}: ${Array.isArray(errors[firstKey]) ? errors[firstKey][0] : errors[firstKey]}`;
      }
      showToast(msg, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleViewDetails = async (id) => {
    try {
      const res = await saleApi.getOne(id);
      setSelectedSale(res.data);
      setIsDetailModalOpen(true);
    } catch {
      showToast('Failed to load sale details.', 'error');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this sales invoice record?')) return;
    try {
      await saleApi.delete(id);
      showToast('Sale record deleted.', 'success');
      fetchSales();
    } catch {
      showToast('Cannot delete sale invoice.', 'error');
    }
  };

  return (
    <div>
      <div className="flex-between mb-6">
        <div>
          <h1 className="page-title">Sales & Billing Management</h1>
          <p className="page-subtitle">Process customer transactions, billing invoices, and automated stock deductions</p>
        </div>
        <button className="btn btn-primary" onClick={handleOpenCreateModal}>
          <Plus size={18} /> New Sales Order
        </button>
      </div>

      <div className="glass-card">
        {loading ? (
          <Loader text="Loading sales history..." />
        ) : sales.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            No sales invoices recorded yet. Click "New Sales Order" to create an invoice.
          </div>
        ) : (
          <>
            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Invoice #</th>
                    <th>Customer</th>
                    <th>Date</th>
                    <th>Total Amount</th>
                    <th>Payment Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {sales.map((s) => (
                    <tr key={s.id}>
                      <td style={{ fontWeight: 600, color: 'var(--text-main)' }}>{s.invoice_number}</td>
                      <td>{s.customer_name || 'Walk-in Customer'}</td>
                      <td style={{ color: 'var(--text-muted)' }}>{formatDate(s.sale_date)}</td>
                      <td style={{ fontWeight: 700, color: 'var(--status-success)' }}>
                        {formatCurrency(s.total_amount)}
                      </td>
                      <td>
                        <span className={`badge ${
                          s.payment_status === 'Paid' ? 'badge-success' :
                          s.payment_status === 'Partial' ? 'badge-warning' : 'badge-danger'
                        }`}>
                          {s.payment_status}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button
                            className="btn btn-secondary btn-icon btn-sm"
                            onClick={() => handleViewDetails(s.id)}
                            title="View Invoice"
                          >
                            <Eye size={15} color="var(--accent-primary)" />
                          </button>
                          <button
                            className="btn btn-secondary btn-icon btn-sm"
                            onClick={() => handleDelete(s.id)}
                            title="Delete Invoice"
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

      {/* Detail Invoice Modal */}
      <Modal
        isOpen={isDetailModalOpen}
        onClose={() => setIsDetailModalOpen(false)}
        title={`Sales Invoice: ${selectedSale?.invoice_number}`}
        maxWidth="650px"
      >
        {selectedSale && (
          <div>
            <div className="grid-2 mb-4">
              <div>
                <span className="form-label">Customer Name</span>
                <div style={{ fontWeight: 600, marginTop: '0.2rem' }}>
                  {selectedSale.customer_name || 'Walk-in Customer'}
                </div>
              </div>
              <div>
                <span className="form-label">Invoice Date</span>
                <div style={{ marginTop: '0.2rem' }}>{formatDate(selectedSale.sale_date)}</div>
              </div>
            </div>

            <h4 style={{ fontSize: '0.9375rem', marginBottom: '0.75rem', color: 'var(--accent-primary)' }}>
              Invoice Line Items
            </h4>
            <div className="table-responsive mb-4">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Item</th>
                    <th>Qty</th>
                    <th>Unit Price</th>
                    <th>Subtotal</th>
                  </tr>
                </thead>
                <tbody>
                  {(selectedSale.items || []).map((item) => (
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
              <span style={{ fontWeight: 600 }}>Grand Total Amount:</span>
              <span style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--status-success)' }}>
                {formatCurrency(selectedSale.total_amount)}
              </span>
            </div>
          </div>
        )}
      </Modal>

      {/* Create Sale Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create Sales Order Invoice"
        maxWidth="750px"
      >
        <form onSubmit={handleSubmitSale}>
          <div className="grid-2 mb-4">
            <div className="form-group">
              <label className="form-label">Customer</label>
              <select
                className="form-select"
                value={headerForm.customer}
                onChange={(e) => setHeaderForm({ ...headerForm, customer: e.target.value })}
              >
                <option value="">Walk-in Customer (Unregistered)</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>{c.first_name} {c.last_name}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Invoice Number *</label>
              <input
                type="text"
                className="form-input"
                value={headerForm.invoice_number}
                onChange={(e) => setHeaderForm({ ...headerForm, invoice_number: e.target.value })}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Sale Date *</label>
              <input
                type="date"
                className="form-input"
                value={headerForm.sale_date}
                onChange={(e) => setHeaderForm({ ...headerForm, sale_date: e.target.value })}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Payment Status</label>
              <select
                className="form-select"
                value={headerForm.payment_status}
                onChange={(e) => setHeaderForm({ ...headerForm, payment_status: e.target.value })}
              >
                <option value="Paid">Paid</option>
                <option value="Pending">Pending</option>
                <option value="Partial">Partial</option>
              </select>
            </div>
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <div className="flex-between mb-2">
              <label className="form-label" style={{ fontSize: '0.9375rem', fontWeight: 600, color: 'var(--status-success)' }}>
                Products & Billing Items
              </label>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={handleAddItemRow}
              >
                <PlusCircle size={14} /> Add Line Item
              </button>
            </div>

            {itemsForm.map((item, index) => {
              const availableStock = inventoryMap[item.product] || 0;
              return (
                <div key={index} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 40px', gap: '0.75rem', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <div>
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
                    {item.product && (
                      <div style={{ fontSize: '0.75rem', marginTop: '0.2rem', color: availableStock > 0 ? 'var(--status-success)' : 'var(--status-danger)' }}>
                        Available Stock: {availableStock} units
                      </div>
                    )}
                  </div>

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
                    placeholder="Price"
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
              );
            })}
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setIsCreateModalOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Processing Invoice...' : 'Complete Sales Order'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
