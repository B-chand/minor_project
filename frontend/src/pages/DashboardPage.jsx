import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  IndianRupee,
  ShoppingBag,
  Package,
  AlertTriangle,
  Users,
  Truck,
  ArrowUpRight,
  TrendingUp,
  RefreshCw,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from 'recharts';
import { reportApi } from '../api';
import { StatCard, Loader } from '../components/common/UIComponents';
import { formatCurrency } from '../utils/formatters';

export const DashboardPage = () => {
  const [summary, setSummary] = useState(null);
  const [salesReport, setSalesReport] = useState([]);
  const [lowStockList, setLowStockList] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [dashRes, salesRes, lowStockRes] = await Promise.all([
        reportApi.getDashboard(),
        reportApi.getSalesReport(),
        reportApi.getLowStockReport(),
      ]);

      setSummary(dashRes.data);
      setSalesReport(salesRes.data || []);
      setLowStockList(lowStockRes.data || []);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  if (loading) return <Loader text="Loading dashboard metrics..." />;

  const chartData = [
    {
      name: 'Financial Overview',
      Sales: summary?.total_sales || 0,
      Purchases: summary?.total_purchases || 0,
    },
  ];

  return (
    <div>
      <div className="flex-between mb-6">
        <div>
          <h1 className="page-title">Executive Dashboard</h1>
          <p className="page-subtitle">Real-time tenant business performance & stock analytics</p>
        </div>
        <button className="btn btn-secondary" onClick={fetchDashboardData}>
          <RefreshCw size={16} /> Refresh Data
        </button>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid-4 mb-6">
        <StatCard
          icon={IndianRupee}
          label="Total Revenue (Sales)"
          value={formatCurrency(summary?.total_sales)}
          color="var(--status-success)"
          bg="var(--status-success-bg)"
        />
        <StatCard
          icon={ShoppingBag}
          label="Total Expenses (Purchases)"
          value={formatCurrency(summary?.total_purchases)}
          color="var(--status-info)"
          bg="var(--status-info-bg)"
        />
        <StatCard
          icon={Package}
          label="Active Products"
          value={summary?.total_products || 0}
          color="var(--accent-primary)"
          bg="var(--accent-glow)"
        />
        <StatCard
          icon={AlertTriangle}
          label="Low / Out of Stock"
          value={(summary?.low_stock_products || 0) + (summary?.out_of_stock_products || 0)}
          color="var(--status-warning)"
          bg="var(--status-warning-bg)"
        />
      </div>

      {/* Secondary Metrics & Chart Grid */}
      <div className="grid-2 mb-6" style={{ gridTemplateColumns: '2fr 1fr' }}>
        <div className="glass-card">
          <div className="flex-between mb-4">
            <h3 style={{ fontSize: '1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <TrendingUp size={18} color="var(--accent-primary)" /> Sales vs Purchases Comparison
            </h3>
          </div>
          <div style={{ width: '100%', height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <XAxis dataKey="name" stroke="var(--text-muted)" />
                <YAxis stroke="var(--text-muted)" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--bg-secondary)',
                    borderColor: 'var(--border-color)',
                    borderRadius: '8px',
                    color: '#fff',
                  }}
                  formatter={(value) => formatCurrency(value)}
                />
                <Legend />
                <Bar dataKey="Sales" fill="var(--status-success)" radius={[6, 6, 0, 0]} />
                <Bar dataKey="Purchases" fill="var(--status-info)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-card flex-between" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1.25rem' }}>Network Entities</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '1rem',
                  background: 'var(--bg-primary)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-color)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <Users size={20} color="var(--accent-secondary)" />
                  <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>Customers</span>
                </div>
                <span style={{ fontSize: '1.25rem', fontWeight: 700 }}>{summary?.total_customers || 0}</span>
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '1rem',
                  background: 'var(--bg-primary)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-color)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <Truck size={20} color="var(--status-info)" />
                  <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>Suppliers</span>
                </div>
                <span style={{ fontSize: '1.25rem', fontWeight: 700 }}>{summary?.total_suppliers || 0}</span>
              </div>
            </div>
          </div>

          <button
            className="btn btn-secondary"
            onClick={() => navigate('/reports')}
            style={{ width: '100%', marginTop: '1.5rem' }}
          >
            View Detailed Reports <ArrowUpRight size={16} />
          </button>
        </div>
      </div>

      {/* Low Stock & Recent Sales Tables */}
      <div className="grid-2">
        {/* Low Stock Widget */}
        <div className="glass-card">
          <div className="flex-between mb-4">
            <h3 style={{ fontSize: '1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <AlertTriangle size={18} color="var(--status-warning)" /> Low Stock Alerts
            </h3>
            <button className="btn btn-secondary btn-sm" onClick={() => navigate('/inventory')}>
              Manage Stock
            </button>
          </div>
          {lowStockList.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              All product stock levels are healthy!
            </div>
          ) : (
            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Current Stock</th>
                    <th>Min Limit</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {lowStockList.slice(0, 5).map((item, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: 600 }}>{item.product}</td>
                      <td style={{ color: item.quantity === 0 ? 'var(--status-danger)' : 'var(--status-warning)' }}>
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
          )}
        </div>

        {/* Recent Sales Widget */}
        <div className="glass-card">
          <div className="flex-between mb-4">
            <h3 style={{ fontSize: '1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <IndianRupee size={18} color="var(--status-success)" /> Recent Sales
            </h3>
            <button className="btn btn-secondary btn-sm" onClick={() => navigate('/sales')}>
              View All Sales
            </button>
          </div>
          {salesReport.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              No sales recorded yet.
            </div>
          ) : (
            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Invoice</th>
                    <th>Customer</th>
                    <th>Amount</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {salesReport.slice(0, 5).map((sale, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: 600 }}>{sale.invoice}</td>
                      <td>{sale.customer}</td>
                      <td style={{ fontWeight: 600, color: 'var(--status-success)' }}>
                        {formatCurrency(sale.amount)}
                      </td>
                      <td>
                        <span className="badge badge-success">{sale.status}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
