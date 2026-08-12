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
  ShoppingCart,
  Calendar,
  Hash,
  RefreshCw,
  TrendingUp,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';
import { reportApi } from '../api';
import { StatCard, Loader } from '../components/common/UIComponents';
import { formatCurrency } from '../utils/formatters';
import { useAuth } from '../context/AuthContext';

const SEGMENTS = [
  { key: 'sales', label: 'Sales', icon: ShoppingCart, color: 'var(--status-success)' },
  { key: 'purchases', label: 'Purchases', icon: ShoppingBag, color: 'var(--status-info)' },
];

const dateInputStyle = {
  width: '100%',
  padding: '0.4rem 0.5rem',
  fontSize: '0.8rem',
  borderRadius: 'var(--radius-md)',
  border: '1px solid var(--border-color)',
  background: 'var(--bg-primary)',
  color: 'inherit',
  colorScheme: 'dark',
};

const isValidDateValue = (value) => {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split('-').map(Number);
  if (month < 1 || month > 12 || day < 1 || day > 31) return false;
  const date = new Date(year, month - 1, day);
  return (
    date.getFullYear() === year &&
    date.getMonth() === month - 1 &&
    date.getDate() === day
  );
};

export const DashboardPage = () => {
  const [summary, setSummary] = useState(null);
  const [salesReport, setSalesReport] = useState([]);
  const [purchasesReport, setPurchasesReport] = useState([]);
  const [lowStockList, setLowStockList] = useState([]);
  const [activeMetric, setActiveMetric] = useState('sales');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [appliedFromDate, setAppliedFromDate] = useState('');
  const [appliedToDate, setAppliedToDate] = useState('');
  const [dateError, setDateError] = useState('');
  const [loading, setLoading] = useState(true);
  const [filterLoading, setFilterLoading] = useState(false);
  const [loadError, setLoadError] = useState('');
  const navigate = useNavigate();
  const { user } = useAuth();

  const buildDashboardParams = (from, to) => {
    const params = {};
    if (from) params.from_date = from;
    if (to) params.to_date = to;
    return params;
  };

  const fetchDashboardData = async (from = appliedFromDate, to = appliedToDate, options = {}) => {
    const full = options.full;
    if (full) setLoading(true);
    setFilterLoading(true);
    try {
      const [dashRes, salesRes, purchaseRes, lowStockRes] = await Promise.allSettled([
        reportApi.getDashboard(buildDashboardParams(from, to)),
        reportApi.getSalesReport(),
        reportApi.getPurchasesReport(),
        reportApi.getLowStockReport(),
      ]);

      setSummary(dashRes.status === 'fulfilled' ? dashRes.value.data : null);
      setSalesReport(salesRes.status === 'fulfilled' ? (salesRes.value.data || []) : []);
      setPurchasesReport(purchaseRes.status === 'fulfilled' ? (purchaseRes.value.data || []) : []);
      setLowStockList(lowStockRes.status === 'fulfilled' ? (lowStockRes.value.data || []) : []);
      const rejectedCount = [dashRes, salesRes, purchaseRes, lowStockRes].filter(
        (r) => r.status === 'rejected'
      ).length;
      setLoadError(
        rejectedCount === 4
          ? 'Dashboard data could not be loaded. Please try again.'
          : ''
      );
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setFilterLoading(false);
      if (full) setLoading(false);
    }
  };

  const applyDateFilter = (from = fromDate, to = toDate) => {
    const cleanFrom = (from || '').trim();
    const cleanTo = (to || '').trim();

    if (cleanFrom === appliedFromDate && cleanTo === appliedToDate) {
      setDateError('');
      return;
    }

    if (!cleanFrom && !cleanTo) {
      setDateError('');
      setAppliedFromDate('');
      setAppliedToDate('');
      fetchDashboardData('', '', { full: false });
      return;
    }

    if (cleanFrom && !isValidDateValue(cleanFrom)) return;
    if (cleanTo && !isValidDateValue(cleanTo)) return;

    if (cleanFrom && cleanTo && cleanFrom > cleanTo) {
      setDateError('From Date must be on or before To Date.');
      return;
    }

    setDateError('');
    setAppliedFromDate(cleanFrom);
    setAppliedToDate(cleanTo);
    fetchDashboardData(cleanFrom, cleanTo, { full: false });
  };

  const handleDateChange = (field, value) => {
    const nextFrom = field === 'from' ? value : fromDate;
    const nextTo = field === 'to' ? value : toDate;
    setFromDate(nextFrom);
    setToDate(nextTo);
    setDateError('');
    if (isValidDateValue(value)) {
      applyDateFilter(nextFrom, nextTo);
    }
  };

  const handleDateBlur = () => {
    applyDateFilter();
  };

  useEffect(() => {
    fetchDashboardData('', '', { full: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) return <Loader text="Loading dashboard metrics..." />;

  const active = SEGMENTS.find((s) => s.key === activeMetric);
  const activeData = activeMetric === 'sales' ? salesReport : purchasesReport;
  const activeTotal = activeMetric === 'sales'
    ? (summary?.total_sales || 0)
    : (summary?.total_purchases || 0);
  const activeCount = activeMetric === 'sales'
    ? (summary?.sales_count || 0)
    : (summary?.purchases_count || 0);
  const chartData = [
    { name: 'Sales', value: summary?.total_sales || 0 },
    { name: 'Purchases', value: summary?.total_purchases || 0 },
  ];
  const ActiveIcon = active.icon;

  const renderRecentTable = () => {
    if (activeData.length === 0) {
      return (
        <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          No {active.label.toLowerCase()} recorded yet.
        </div>
      );
    }

    if (activeMetric === 'sales') {
      return (
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
              {activeData.slice(0, 5).map((sale, idx) => (
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
      );
    }

    return (
      <div className="table-responsive">
        <table className="custom-table">
          <thead>
            <tr>
              <th>Invoice</th>
              <th>Supplier</th>
              <th>Amount</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {activeData.slice(0, 5).map((purchase, idx) => (
              <tr key={idx}>
                <td style={{ fontWeight: 600 }}>{purchase.invoice}</td>
                <td>{purchase.supplier}</td>
                <td style={{ fontWeight: 600, color: 'var(--status-info)' }}>
                  {formatCurrency(purchase.amount)}
                </td>
                <td>
                  <span className="badge badge-info">{purchase.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div>
      {loadError && (
        <div
          style={{
            padding: '0.75rem 1rem',
            marginBottom: '1rem',
            borderRadius: 'var(--radius-md)',
            background: 'var(--status-danger-bg)',
            color: 'var(--status-danger)',
            fontSize: '0.875rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '0.75rem',
          }}
        >
          <span>{loadError}</span>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => fetchDashboardData(appliedFromDate, appliedToDate, { full: false })}
          >
            Try again
          </button>
        </div>
      )}
      <div className="flex-between mb-6">
        <div>
          <h1 className="page-title">Executive Dashboard</h1>
          <p className="page-subtitle">Real-time tenant business performance & stock analytics</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {filterLoading && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              <span
                style={{
                  width: 14,
                  height: 14,
                  border: '2px solid var(--border-color)',
                  borderTopColor: 'var(--accent-primary)',
                  borderRadius: '50%',
                  display: 'inline-block',
                  animation: 'dash-spin 0.8s linear infinite',
                }}
              />
              <style>{`@keyframes dash-spin { to { transform: rotate(360deg); } }`}</style>
              Loading...
            </span>
          )}
          <button className="btn btn-secondary" onClick={() => fetchDashboardData(undefined, undefined, { full: true })}>
            <RefreshCw size={16} /> Refresh Data
          </button>
        </div>
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

      {/* Sales vs Purchases Performance Panel + Network Entities */}
      <div className="grid-2 mb-6" style={{ gridTemplateColumns: '2fr 1fr' }}>
        <div className="glass-card">
          <div className="flex-between mb-4" style={{ flexWrap: 'wrap', gap: '0.75rem' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <TrendingUp size={18} color="var(--accent-primary)" /> Sales vs Purchases
            </h3>
            <div style={{ display: 'flex', gap: '0.5rem' }} role="tablist" aria-label="Sales or Purchases metrics">
              {SEGMENTS.map((seg) => {
                const SegIcon = seg.icon;
                return (
                  <button
                    key={seg.key}
                    role="tab"
                    aria-selected={activeMetric === seg.key}
                    className={`metric-tab ${activeMetric === seg.key ? 'active' : ''}`}
                    onClick={() => setActiveMetric(seg.key)}
                  >
                    <SegIcon size={16} />
                    {seg.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Selected metric summary */}
          <div className="grid-3 mb-4">
            <div className="metric-summary" style={{ borderTopColor: active.color }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Total {active.label} Amount
              </div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>
                {formatCurrency(activeTotal)}
              </div>
            </div>
            <div className="metric-summary">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                <Hash size={13} /> Number of {active.label}
              </div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{activeCount}</div>
            </div>
            <div className="metric-summary">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                <Calendar size={13} /> Date Range
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginTop: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  <span style={{ whiteSpace: 'nowrap' }}>From Date</span>
                  <input
                    type="date"
                    value={fromDate}
                    onChange={(e) => handleDateChange('from', e.target.value)}
                    onBlur={handleDateBlur}
                    style={dateInputStyle}
                  />
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  <span style={{ whiteSpace: 'nowrap' }}>To Date</span>
                  <input
                    type="date"
                    value={toDate}
                    onChange={(e) => handleDateChange('to', e.target.value)}
                    onBlur={handleDateBlur}
                    style={dateInputStyle}
                  />
                </div>
                {dateError && (
                  <div style={{ color: 'var(--status-danger)', fontSize: '0.75rem', fontWeight: 600 }}>
                    {dateError}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '1.5rem', justifyContent: 'center', marginBottom: '0.5rem' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              <span
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: 3,
                  background: 'var(--status-success)',
                  display: 'inline-block',
                }}
              />
              Sales
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              <span
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: 3,
                  background: 'var(--status-info)',
                  display: 'inline-block',
                }}
              />
              Purchases
            </span>
          </div>

          <div style={{ width: '100%', height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
              >
                <XAxis dataKey="name" stroke="var(--text-muted)" />
                <YAxis stroke="var(--text-muted)" />
                <Tooltip
                  cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }}
                  contentStyle={{
                    backgroundColor: 'var(--bg-secondary)',
                    borderColor: 'var(--border-color)',
                    borderRadius: '8px',
                    color: '#fff',
                  }}
                  labelFormatter={() => ''}
                  formatter={(value, name) => [`${name}: ${formatCurrency(value)}`, '']}
                />
                <Bar
                  dataKey="value"
                  name="Amount"
                  radius={[6, 6, 0, 0]}
                  isAnimationActive={false}
                >
                  {chartData.map((entry, index) => (
                    <Cell
                      key={entry.name}
                      fill={index === 0 ? 'var(--status-success)' : 'var(--status-info)'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Total Sales and Purchases shown together for direct comparison.
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

          {user?.role === 'ADMIN' && (
            <button
              className="btn btn-secondary"
              onClick={() => navigate('/reports')}
              style={{ width: '100%', marginTop: '1.5rem' }}
            >
              View Detailed Reports <ArrowUpRight size={16} />
            </button>
          )}
        </div>
      </div>

      {/* Low Stock & Recent Tables */}
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

        {/* Recent {Sales|Purchases} Widget — follows the selected metric */}
        <div className="glass-card">
          <div className="flex-between mb-4">
            <h3 style={{ fontSize: '1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <ActiveIcon size={18} color={active.color} /> Recent {active.label}
            </h3>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => navigate(activeMetric === 'sales' ? '/sales' : '/purchases')}
            >
              View All {active.label}
            </button>
          </div>
          {renderRecentTable()}
        </div>
      </div>
    </div>
  );
};