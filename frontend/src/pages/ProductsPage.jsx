import React, { useEffect, useState } from 'react';
import { Package, Plus, Search, Filter, Edit2, Trash2, Tag, Image as ImageIcon } from 'lucide-react';
import { productApi, categoryApi, fetchAllPages } from '../api';
import { Modal, Loader, Pagination } from '../components/common/UIComponents';
import { useNotification } from '../context/NotificationContext';
import { formatCurrency } from '../utils/formatters';

export const ProductsPage = () => {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const [formData, setFormData] = useState({
    name: '',
    sku: '',
    barcode: '',
    description: '',
    category: '',
    buying_price: '',
    selling_price: '',
    is_active: true,
  });
  const [imageFile, setImageFile] = useState(null);

  const { showToast } = useNotification();

  const fetchCategories = async () => {
    try {
      const items = await fetchAllPages((params) => categoryApi.getAll(params));
      setCategories(items);
    } catch (err) {
      console.error('Failed to load categories:', err);
    }
  };

  const fetchProducts = async () => {
    setLoading(true);
    try {
      const params = {
        page,
        search: search || undefined,
        category: selectedCategory || undefined,
      };
      const res = await productApi.getAll(params);
      if (res.data.results) {
        setProducts(res.data.results);
        setCount(res.data.count);
      } else {
        setProducts(res.data || []);
        setCount((res.data || []).length);
      }
    } catch (err) {
      showToast('Failed to load products.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCategories();
  }, []);

  useEffect(() => {
    fetchProducts();
  }, [page, selectedCategory]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchProducts();
  };

  const handleOpenModal = (product = null) => {
    setImageFile(null);
    if (product) {
      setEditingProduct(product);
      setFormData({
        name: product.name,
        sku: product.sku,
        barcode: product.barcode || '',
        description: product.description || '',
        category: product.category || '',
        buying_price: product.buying_price,
        selling_price: product.selling_price,
        is_active: product.is_active,
      });
    } else {
      setEditingProduct(null);
      setFormData({
        name: '',
        sku: `SKU-${Math.floor(100000 + Math.random() * 900000)}`,
        barcode: '',
        description: '',
        category: categories.length > 0 ? categories[0].id : '',
        buying_price: '',
        selling_price: '',
        is_active: true,
      });
    }
    setIsModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (parseFloat(formData.selling_price) < parseFloat(formData.buying_price)) {
      showToast('Selling price cannot be less than buying price.', 'error');
      return;
    }

    setSubmitting(true);
    try {
      const data = new FormData();
      Object.keys(formData).forEach((key) => {
        if (formData[key] !== null && formData[key] !== undefined) {
          data.append(key, formData[key]);
        }
      });
      if (imageFile) {
        data.append('image', imageFile);
      }

      if (editingProduct) {
        await productApi.update(editingProduct.id, data);
        showToast('Product updated successfully!', 'success');
      } else {
        await productApi.create(data);
        showToast('Product created successfully!', 'success');
      }
      setIsModalOpen(false);
      fetchProducts();
    } catch (err) {
      console.error('Product save error:', err);
      const errors = err.response?.data;
      let msg = 'Failed to save product.';
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
    if (!window.confirm('Are you sure you want to delete this product?')) return;
    try {
      await productApi.delete(id);
      showToast('Product deleted successfully.', 'success');
      fetchProducts();
    } catch (err) {
      const errMsg = err.response?.data?.error || 'Failed to delete product.';
      showToast(errMsg, 'error');
    }
  };

  return (
    <div>
      <div className="flex-between mb-6">
        <div>
          <h1 className="page-title">Products Directory</h1>
          <p className="page-subtitle">Manage organization items, prices, SKUs, and images</p>
        </div>
        <button className="btn btn-primary" onClick={() => handleOpenModal()}>
          <Plus size={18} /> Add Product
        </button>
      </div>

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
              placeholder="Search by SKU, barcode, name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Filter size={18} color="var(--text-muted)" />
            <select
              className="form-select"
              style={{ width: '200px' }}
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All Categories</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
            <button type="submit" className="btn btn-secondary">
              Search
            </button>
          </div>
        </form>
      </div>

      {/* Products Table */}
      <div className="glass-card">
        {loading ? (
          <Loader text="Loading products catalog..." />
        ) : products.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            No products found matching filters.
          </div>
        ) : (
          <>
            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>SKU / Barcode</th>
                    <th>Category</th>
                    <th>Buying Price</th>
                    <th>Selling Price</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map((p) => (
                    <tr key={p.id}>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                          {p.image ? (
                            <img
                              src={p.image}
                              alt={p.name}
                              style={{ width: '36px', height: '36px', borderRadius: '6px', objectFit: 'cover' }}
                            />
                          ) : (
                            <div
                              style={{
                                width: '36px',
                                height: '36px',
                                borderRadius: '6px',
                                background: 'var(--bg-tertiary)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                color: 'var(--text-dim)',
                              }}
                            >
                              <Package size={20} />
                            </div>
                          )}
                          <div>
                            <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{p.name}</div>
                            {p.description && (
                              <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                                {p.description.substring(0, 40)}...
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td>
                        <div style={{ fontSize: '0.8125rem', fontFamily: 'monospace' }}>{p.sku}</div>
                        {p.barcode && (
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>BC: {p.barcode}</div>
                        )}
                      </td>
                      <td>
                        <span className="badge badge-info">{p.category_name || 'Uncategorized'}</span>
                      </td>
                      <td style={{ color: 'var(--text-muted)' }}>{formatCurrency(p.buying_price)}</td>
                      <td style={{ fontWeight: 600, color: 'var(--status-success)' }}>
                        {formatCurrency(p.selling_price)}
                      </td>
                      <td>
                        <span className={`badge ${p.is_active ? 'badge-success' : 'badge-danger'}`}>
                          {p.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button
                            className="btn btn-secondary btn-icon btn-sm"
                            onClick={() => handleOpenModal(p)}
                            title="Edit Product"
                          >
                            <Edit2 size={15} color="var(--accent-secondary)" />
                          </button>
                          <button
                            className="btn btn-secondary btn-icon btn-sm"
                            onClick={() => handleDelete(p.id)}
                            title="Delete Product"
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

            <Pagination
              count={count}
              page={page}
              onPageChange={(newPage) => setPage(newPage)}
              pageSize={10}
            />
          </>
        )}
      </div>

      {/* Modal Form */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingProduct ? 'Edit Product' : 'Add New Product'}
        maxWidth="650px"
      >
        <form onSubmit={handleSubmit}>
          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">Product Name *</label>
              <input
                type="text"
                className="form-input"
                placeholder="Product title"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">SKU (Unique) *</label>
              <input
                type="text"
                className="form-input"
                placeholder="SKU-1001"
                value={formData.sku}
                onChange={(e) => setFormData({ ...formData, sku: e.target.value })}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Category</label>
              <select
                className="form-select"
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              >
                <option value="">Select Category</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Barcode (Optional)</label>
              <input
                type="text"
                className="form-input"
                placeholder="Barcode number"
                value={formData.barcode}
                onChange={(e) => setFormData({ ...formData, barcode: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Buying Price (Cost) *</label>
              <input
                type="number"
                step="0.01"
                className="form-input"
                placeholder="0.00"
                value={formData.buying_price}
                onChange={(e) => setFormData({ ...formData, buying_price: e.target.value })}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Selling Price *</label>
              <input
                type="number"
                step="0.01"
                className="form-input"
                placeholder="0.00"
                value={formData.selling_price}
                onChange={(e) => setFormData({ ...formData, selling_price: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="form-group mb-4">
            <label className="form-label">Product Image</label>
            <input
              type="file"
              accept="image/*"
              className="form-input"
              onChange={(e) => setImageFile(e.target.files[0])}
            />
          </div>

          <div className="form-group mb-6">
            <label className="form-label">Description</label>
            <textarea
              className="form-textarea"
              rows={2}
              placeholder="Product description and details..."
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            />
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Saving...' : editingProduct ? 'Update Product' : 'Create Product'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
