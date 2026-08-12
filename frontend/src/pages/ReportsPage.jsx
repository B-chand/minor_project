import React, { useEffect, useState } from 'react';
import { BarChart3, Plus, FileSpreadsheet, TrendingUp, AlertTriangle } from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';
import { reportApi } from '../api';
import { Modal, Loader } from '../components/common/UIComponents';
import { useNotification } from '../context/NotificationContext';
import { formatCurrency, formatDate } from '../utils/formatters';

const TYPE_DEFAULT_TAB = {
  SALES: 'sales',
  PURCHASE: 'purchases',
  INVENTORY: 'low-stock',
  CUSTOMER: 'customers',
};

export const ReportsPage = () => {
  const [activeTab, setActiveTab] = useState('sales'); // 'sales' | 'purchases' | 'low-stock' | 'saved'
  const [salesData, setSalesData] = useState([]);
  const [purchaseData, setPurchaseData] = useState([]);
  const [lowStockData, setLowStockData] = useState([]);
  const [savedReports, setSavedReports] = useState([]);
  const [loading, setLoading] = useState(true);

  // Modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [reportForm, setReportForm] = useState({ title: '', report_type: 'SALES', description: '' });
  const [submitting, setSubmitting] = useState(false);

  // View saved report modal
  const [isViewOpen, setIsViewOpen] = useState(false);
  const [viewingReport, setViewingReport] = useState(null);

  const { showToast } = useNotification();

  const fetchReportData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'sales') {
        const res = await reportApi.getSalesReport();
        setSalesData(res.data || []);
      } else if (activeTab === 'purchases') {
        const res = await reportApi.getPurchasesReport();
        setPurchaseData(res.data || []);
      } else if (activeTab === 'low-stock') {
        const res = await reportApi.getLowStockReport();
        setLowStockData(res.data || []);
      } else {
        const res = await reportApi.getAllSaved();
        setSavedReports(res.data.results || res.data || []);
      }
    } catch (err) {
      showToast('Failed to load report data.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReportData();
  }, [activeTab]);

  const buildReportData = () => {
    const rowsByType = {
      SALES: salesData,
      PURCHASE: purchaseData,
      INVENTORY: lowStockData,
    };
    return {
      config: {
        tab: TYPE_DEFAULT_TAB[reportForm.report_type] || 'sales',
        report_type: reportForm.report_type,
      },
      generated_at: new Date().toISOString(),
      rows: rowsByType[reportForm.report_type] || [],
    };
  };

  const handleCreateReport = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const report_data = buildReportData();
      await reportApi.createReport({ ...reportForm, report_data });
      showToast('Report generated & saved successfully!', 'success');
      setIsModalOpen(false);
      fetchReportData();
    } catch (err) {
      showToast('Failed to create report.', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const openCreateModal = () => {
    const defaultType = {
      sales: 'SALES',
      purchases: 'PURCHASE',
      'low-stock': 'INVENTORY',
    }[activeTab] || 'SALES';
    setReportForm({ title: '', report_type: defaultType, description: '' });
    setIsModalOpen(true);
  };

  const handleDeleteReport = async (id) => {
    if (!window.confirm('Delete this saved report?')) return;
    try {
      await reportApi.deleteReport(id);
      showToast('Saved report deleted.', 'success');
      fetchReportData();
    } catch (err) {
      showToast('Failed to delete report.', 'error');
    }
  };

  const openView = (report) => {
    setViewingReport(report);
    setIsViewOpen(true);
  };

  const renderSavedSnapshotRows = () => {
    const rows = viewingReport?.report_data?.rows || [];
    const tab = viewingReport?.report_data?.config?.tab || 'sales';

    if (rows.length === 0) {
      return (
        <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          No snapshot rows were captured for this saved report.
        </div>
      );
    }

    const columns = {
      sales: { headers: ['Date', 'Invoice #', 'Customer', 'Amount', 'Status'] },
      purchases: { headers: ['Date', 'Invoice #', 'Supplier', 'Amount', 'Status'] },
      'low-stock': { headers: ['Product', 'Available', 'Min Limit', 'Status'] },
    }[tab] || { headers: ['Date', 'Invoice #', 'Customer', 'Amount', 'Status'] };

    return (
      <div className="table-responsive">
        <table className="custom-table">
          <thead>
            <tr>
              {columns.headers.map((h) => <th key={h}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => {
              if (tab === 'low-stock') {
                return (
                  <tr key={idx}>
                    <td style={{ fontWeight: 600 }}>{row.product}</td>
                    <td style={{ fontWeight: 700, color: row.quantity === 0 ? 'var(--status-danger)' : 'var(--status-warning)' }}>
                      {row.quantity} units
                    </td>
                    <td>{row.minimum_stock}</td>
                    <td>
                      <span className={`badge ${row.quantity === 0 ? 'badge-danger' : 'badge-warning'}`}>
                        {row.status}
                      </span>
                    </td>
                  </tr>
                );
              }
              const amount = parseFloat(row.amount ?? 0);
              const isPurchase = tab === 'purchases';
              return (
                <tr key={idx}>
                  <td style={{ color: 'var(--text-muted)' }}>{row.date ? formatDate(row.date) : '—'}</td>
                  <td style={{ fontWeight: 600 }}>{row.invoice}</td>
                  <td>{isPurchase ? row.supplier : row.customer}</td>
                  <td style={{ fontWeight: 700, color: isPurchase ? 'var(--status-info)' : 'var(--status-success)' }}>
                    {formatCurrency(amount)}
                  </td>
                  <td>
                    <span className="badge badge-secondary">{row.status}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div>
      <div className="flex-between mb-6">
        <div>
          <h1 className="page-title">Analytics & Reports</h1>
          <p className="page-subtitle">Generate business intelligence reports and audit summaries</p>
        </div>
        <button className="btn btn-primary" onClick={openCreateModal}>
          <Plus size={18} /> Save Custom Report
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
        <button
          className={`btn ${activeTab === 'sales' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('sales')}
        >
          <TrendingUp size={18} /> Sales Report
        </button>
        <button
          className={`btn ${activeTab === 'purchases' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('purchases')}
        >
          <BarChart3 size={18} /> Purchase Report
        </button>
        <button
          className={`btn ${activeTab === 'low-stock' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('low-stock')}
        >
          <AlertTriangle size={18} /> Low Stock Audit
        </button>
        <button
          className={`btn ${activeTab === 'saved' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('saved')}
        >
          <FileSpreadsheet size={18} /> Saved Reports
        </button>
      </div>

      <div className="glass-card">
        {loading ? (
          <Loader text="Generating analytics..." />
        ) : activeTab === 'sales' ? (
          <div>
            <div className="flex-between mb-4">
              <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Sales Transactions Breakdown</h3>
            </div>

            {salesData.length > 0 && (
              <div style={{ width: '100%', height: 260, marginBottom: '2rem' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={salesData.slice(0, 12)} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
                    <XAxis dataKey="invoice" stroke="var(--text-muted)" fontSize={11} />
                    <YAxis stroke="var(--text-muted)" fontSize={11} />
                    <Tooltip
                      cursor={{ fill: 'rgba(99,102,241,0.08)' }}
                      contentStyle={{
                        backgroundColor: 'var(--bg-secondary)',
                        borderColor: 'var(--border-color)',
                        borderRadius: '8px',
                        color: '#fff',
                      }}
                      formatter={(value) => formatCurrency(value)}
                    />
                    <Bar dataKey="amount" fill="var(--status-success)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Invoice #</th>
                    <th>Customer Name</th>
                    <th>Sales Amount</th>
                    <th>Payment Status</th>
                  </tr>
                </thead>
                <tbody>
                  {salesData.map((s, idx) => (
                    <tr key={idx}>
                      <td style={{ color: 'var(--text-muted)' }}>{formatDate(s.date)}</td>
                      <td style={{ fontWeight: 600 }}>{s.invoice}</td>
                      <td>{s.customer}</td>
                      <td style={{ fontWeight: 700, color: 'var(--status-success)' }}>
                        {formatCurrency(s.amount)}
                      </td>
                      <td>
                        <span className="badge badge-success">{s.status}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : activeTab === 'low-stock' ? (
          <div>
            <div className="flex-between mb-4">
              <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Low Stock & Reorder Audit</h3>
            </div>

            {lowStockData.length > 0 && (
              <div style={{ width: '100%', height: 260, marginBottom: '2rem' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={lowStockData.slice(0, 12)} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
                    <XAxis dataKey="product" stroke="var(--text-muted)" fontSize={11} />
                    <YAxis stroke="var(--text-muted)" fontSize={11} />
                    <Tooltip
                      cursor={{ fill: 'rgba(217,119,6,0.08)' }}
                      contentStyle={{
                        backgroundColor: 'var(--bg-secondary)',
                        borderColor: 'var(--border-color)',
                        borderRadius: '8px',
                        color: '#fff',
                      }}
                      formatter={(value) => `${value} units`}
                    />
                    <Bar dataKey="quantity" fill="var(--status-warning)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Product Name</th>
                    <th>Available Stock</th>
                    <th>Min Limit</th>
                    <th>Stock Status</th>
                  </tr>
                </thead>
                <tbody>
                  {lowStockData.map((item, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: 600 }}>{item.product}</td>
                      <td style={{ fontWeight: 700, color: item.quantity === 0 ? 'var(--status-danger)' : 'var(--status-warning)' }}>
                        {item.quantity} units
                      </td>
                      <td>{item.minimum_stock}</td>
                      <td>
                        <span className={`badge ${item.quantity === 0 ? 'badge-danger' : 'badge-warning'}`}>
                          {item.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : activeTab === 'purchases' ? (
          <div>
            <div className="flex-between mb-4">
              <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Purchase Transactions Breakdown</h3>
            </div>

            {purchaseData.length > 0 && (
              <div style={{ width: '100%', height: 260, marginBottom: '2rem' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={purchaseData.slice(0, 12)} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
                    <XAxis dataKey="invoice" stroke="var(--text-muted)" fontSize={11} />
                    <YAxis stroke="var(--text-muted)" fontSize={11} />
                    <Tooltip
                      cursor={{ fill: 'rgba(99,102,241,0.08)' }}
                      contentStyle={{
                        backgroundColor: 'var(--bg-secondary)',
                        borderColor: 'var(--border-color)',
                        borderRadius: '8px',
                        color: '#fff',
                      }}
                      formatter={(value) => formatCurrency(value)}
                    />
                    <Bar dataKey="amount" fill="var(--status-info)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Invoice #</th>
                    <th>Supplier Name</th>
                    <th>Purchase Amount</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {purchaseData.map((p, idx) => (
                    <tr key={idx}>
                      <td style={{ color: 'var(--text-muted)' }}>{formatDate(p.date)}</td>
                      <td style={{ fontWeight: 600 }}>{p.invoice}</td>
                      <td>{p.supplier}</td>
                      <td style={{ fontWeight: 700, color: 'var(--status-info)' }}>
                        {formatCurrency(p.amount)}
                      </td>
                      <td>
                        <span className={`badge ${
                          p.status === 'Completed' ? 'badge-success' :
                          p.status === 'Pending' ? 'badge-warning' : 'badge-danger'
                        }`}>
                          {p.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div>
            <div className="flex-between mb-4">
              <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Saved Organization Reports</h3>
            </div>
            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Report Title</th>
                    <th>Type</th>
                    <th>Generated By</th>
                    <th>Description</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {savedReports.map((r) => (
                    <tr key={r.id}>
                      <td style={{ fontWeight: 600 }}>{r.title}</td>
                      <td>
                        <span className="badge badge-info">{r.report_type}</span>
                      </td>
                      <td>{r.generated_by_name || 'System Admin'}</td>
                      <td style={{ color: 'var(--text-muted)' }}>{r.description || 'N/A'}</td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button
                            className="btn btn-sm btn-secondary"
                            onClick={() => openView(r)}
                          >
                            View
                          </button>
                          <button
                            className="btn btn-sm btn-danger"
                            onClick={() => handleDeleteReport(r.id)}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Save Custom Report"
      >
        <form onSubmit={handleCreateReport}>
          <div className="form-group mb-4">
            <label className="form-label">Report Title *</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Q3 Sales & Inventory Summary"
              value={reportForm.title}
              onChange={(e) => setReportForm({ ...reportForm, title: e.target.value })}
              required
            />
          </div>

          <div className="form-group mb-4">
            <label className="form-label">Report Category *</label>
            <select
              className="form-select"
              value={reportForm.report_type}
              onChange={(e) => setReportForm({ ...reportForm, report_type: e.target.value })}
            >
              <option value="SALES">Sales Report</option>
              <option value="PURCHASE">Purchase Report</option>
              <option value="INVENTORY">Inventory Report</option>
              <option value="CUSTOMER">Customer Report</option>
            </select>
          </div>

          <div className="form-group mb-6">
            <label className="form-label">Description / Purpose</label>
            <textarea
              className="form-textarea"
              rows={3}
              placeholder="Provide context or notes..."
              value={reportForm.description}
              onChange={(e) => setReportForm({ ...reportForm, description: e.target.value })}
            />
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Generating...' : 'Save Report'}
            </button>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={isViewOpen}
        onClose={() => setIsViewOpen(false)}
        title={viewingReport ? `Saved Report — ${viewingReport.title}` : 'Saved Report'}
      >
        {viewingReport && (
          <div>
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">Report Type</label>
                <div>
                  <span className="badge badge-info">{viewingReport.report_type}</span>
                </div>
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">Generated By</label>
                <div style={{ paddingTop: '0.25rem' }}>
                  {viewingReport.generated_by_name || 'System Admin'}
                </div>
              </div>
              {viewingReport.report_data?.generated_at && (
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Snapshot Taken</label>
                  <div style={{ paddingTop: '0.25rem' }}>
                    {formatDate(viewingReport.report_data.generated_at)}
                  </div>
                </div>
              )}
            </div>
            {viewingReport.description && (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '1rem' }}>
                {viewingReport.description}
              </p>
            )}
            {renderSavedSnapshotRows()}
          </div>
        )}
        <div className="modal-footer" style={{ marginTop: '1rem' }}>
          <button type="button" className="btn btn-secondary" onClick={() => setIsViewOpen(false)}>
            Close
          </button>
        </div>
      </Modal>
    </div>
  );
};
