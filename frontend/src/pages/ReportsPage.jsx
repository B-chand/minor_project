import React, { useEffect, useState } from 'react';
import { BarChart3, Plus, FileSpreadsheet, TrendingUp, AlertTriangle, Download } from 'lucide-react';
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

export const ReportsPage = () => {
  const [activeTab, setActiveTab] = useState('sales'); // 'sales' | 'low-stock' | 'saved'
  const [salesData, setSalesData] = useState([]);
  const [lowStockData, setLowStockData] = useState([]);
  const [savedReports, setSavedReports] = useState([]);
  const [loading, setLoading] = useState(true);

  // Modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [reportForm, setReportForm] = useState({ title: '', report_type: 'SALES', description: '' });
  const [submitting, setSubmitting] = useState(false);

  const { showToast } = useNotification();

  const fetchReportData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'sales') {
        const res = await reportApi.getSalesReport();
        setSalesData(res.data || []);
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

  const handleCreateReport = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await reportApi.createReport(reportForm);
      showToast('Report generated & saved successfully!', 'success');
      setIsModalOpen(false);
      fetchReportData();
    } catch (err) {
      showToast('Failed to create report.', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <div className="flex-between mb-6">
        <div>
          <h1 className="page-title">Analytics & Reports</h1>
          <p className="page-subtitle">Generate business intelligence reports and audit summaries</p>
        </div>
        <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
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
    </div>
  );
};
