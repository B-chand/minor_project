import api from './axios';

export const fetchAllPages = async (requestFn, params = {}) => {
  const aggregated = [];
  let page = 1;

  while (true) {
    const response = await requestFn({ ...params, page });
    const data = response.data ?? [];
    const pageItems = Array.isArray(data.results) ? data.results : data;

    if (!Array.isArray(pageItems)) {
      return pageItems;
    }

    aggregated.push(...pageItems);

    if (!data.results) {
      return aggregated;
    }

    const count = typeof data.count === 'number' ? data.count : null;
    if (count === null || aggregated.length >= count) {
      return aggregated;
    }

    page += 1;
  }
};

// =====================================
// AUTH & USER APIs
// =====================================
export const authApi = {
  login: (credentials) => api.post('/token/', credentials),
  refreshToken: (refresh) => api.post('/token/refresh/', { refresh }),
  register: (userData) => api.post('/accounts/register/', userData),
  getCurrentUser: () => api.get('/accounts/me/'),
  getStaff: () => api.get('/accounts/staff/'),
  createStaff: (staffData) => api.post('/accounts/staff/', staffData),
  updateStaff: (id, staffData) => api.put(`/accounts/staff/${id}/`, staffData),
  deleteStaff: (id) => api.delete(`/accounts/staff/${id}/`),
};

// =====================================
// BUSINESS PROFILE APIs
// =====================================
export const businessApi = {
  getProfile: () => api.get('/business/profile/'),
  createProfile: (data) => api.post('/business/profile/', data),
  updateProfile: (id, data) => api.patch(`/business/profile/${id}/`, data),
};

// =====================================
// CATEGORIES & PRODUCTS APIs
// =====================================
export const categoryApi = {
  getAll: (params) => api.get('/inventory/categories/', { params }),
  create: (data) => api.post('/inventory/categories/', data),
  update: (id, data) => api.put(`/inventory/categories/${id}/`, data),
  delete: (id) => api.delete(`/inventory/categories/${id}/`),
};

export const productApi = {
  getAll: (params) => api.get('/inventory/products/', { params }),
  getOne: (id) => api.get(`/inventory/products/${id}/`),
  create: (formData) => api.post('/inventory/products/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  update: (id, formData) => api.patch(`/inventory/products/${id}/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  delete: (id) => api.delete(`/inventory/products/${id}/`),
};

// =====================================
// INVENTORY & STOCK MOVEMENTS APIs
// =====================================
export const inventoryApi = {
  getAll: (params) => api.get('/inventory/inventory/', { params }),
  update: (id, data) => api.patch(`/inventory/inventory/${id}/`, data),
  getMovements: (params) => api.get('/inventory/stock-movements/', { params }),
  createMovement: (data) => api.post('/inventory/stock-movements/', data),
};

// =====================================
// CUSTOMERS & SUPPLIERS APIs
// =====================================
export const customerApi = {
  getAll: (params) => api.get('/customers/customers/', { params }),
  getOne: (id) => api.get(`/customers/customers/${id}/`),
  create: (data) => api.post('/customers/customers/', data),
  update: (id, data) => api.put(`/customers/customers/${id}/`, data),
  delete: (id) => api.delete(`/customers/customers/${id}/`),
};

export const supplierApi = {
  getAll: (params) => api.get('/suppliers/suppliers/', { params }),
  getOne: (id) => api.get(`/suppliers/suppliers/${id}/`),
  create: (data) => api.post('/suppliers/suppliers/', data),
  update: (id, data) => api.put(`/suppliers/suppliers/${id}/`, data),
  delete: (id) => api.delete(`/suppliers/suppliers/${id}/`),
};

// =====================================
// PURCHASES APIs
// =====================================
export const purchaseApi = {
  getAll: (params) => api.get('/purchases/purchases/', { params }),
  getOne: (id) => api.get(`/purchases/purchases/${id}/`),
  create: (data) => api.post('/purchases/purchases/', data),
  update: (id, data) => api.patch(`/purchases/purchases/${id}/`, data),
  delete: (id) => api.delete(`/purchases/purchases/${id}/`),
  addItem: (itemData) => api.post('/purchases/purchase-items/', itemData),
  deleteItem: (itemId) => api.delete(`/purchases/purchase-items/${itemId}/`),
};

// =====================================
// SALES APIs
// =====================================
export const saleApi = {
  getAll: (params) => api.get('/sales/sales/', { params }),
  getOne: (id) => api.get(`/sales/sales/${id}/`),
  create: (data) => api.post('/sales/sales/', data),
  update: (id, data) => api.patch(`/sales/sales/${id}/`, data),
  delete: (id) => api.delete(`/sales/sales/${id}/`),
  addItem: (itemData) => api.post('/sales/sale-items/', itemData),
  deleteItem: (itemId) => api.delete(`/sales/sale-items/${itemId}/`),
};

// =====================================
// NOTIFICATIONS APIs
// =====================================
export const notificationApi = {
  getAll: (params) => api.get('/notifications/notifications/', { params }),
  markRead: (id) => api.patch(`/notifications/notifications/${id}/`, { is_read: true }),
  delete: (id) => api.delete(`/notifications/notifications/${id}/`),
};

// =====================================
// REPORTS & DASHBOARD APIs
// =====================================
export const reportApi = {
  getDashboard: () => api.get('/reports/dashboard/'),
  getSalesReport: () => api.get('/reports/sales/'),
  getLowStockReport: () => api.get('/reports/low-stock/'),
  getAllSaved: () => api.get('/reports/'),
  createReport: (data) => api.post('/reports/', data),
};

// =====================================
// AI INSIGHTS APIs
// =====================================
export const aiInsightApi = {
  getAll: (params) => api.get('/ai/insights/', { params }),
  getOne: (id) => api.get(`/ai/insights/${id}/`),
  create: (data) => api.post('/ai/insights/', data),
  update: (id, data) => api.patch(`/ai/insights/${id}/`, data),
  delete: (id) => api.delete(`/ai/insights/${id}/`),
};
