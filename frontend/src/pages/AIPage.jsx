import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  TrendingUp,
  IndianRupee,
  Sparkles,
  AlertTriangle,
  Lightbulb,
  RefreshCw,
  ShoppingBag,
  Cpu,
  PackageX,
  ShoppingCart,
  Truck,
  Users,
  Activity,
  Crown,
  CalendarRange,
  Package,
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';
import { getAIDashboard, getBusinessIntelligence, getInventorySummary, getErrorMessage } from '../services/aiService';
import { Loader, StatCard } from '../components/common/UIComponents';
import { SectionCard, EmptyState } from '../components/ai/SectionCard';
import { formatCurrency, formatDate } from '../utils/formatters';

const currency = (value) => formatCurrency(value);

const SectionError = ({ message }) => (
  <div
    style={{
      padding: '1.5rem',
      textAlign: 'center',
      color: 'var(--status-danger)',
      fontSize: '0.875rem',
    }}
  >
    <AlertTriangle size={18} style={{ verticalAlign: 'middle', marginRight: '0.5rem' }} />
    {message}
  </div>
);

export const AIPage = () => {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [bi, setBi] = useState(null);
  const [inventorySummary, setInventorySummary] = useState(null);
  const [dashboardError, setDashboardError] = useState('');
  const [biError, setBiError] = useState('');
  const [inventoryError, setInventoryError] = useState('');
  const [windowFilter, setWindowFilter] = useState({ days: 30, bucket: 'month' });

  const reloadTokenRef = useRef(0);

  const loadData = useCallback(async (filter = null) => {
    const token = ++reloadTokenRef.current;
    setLoading(true);
    try {
      const active = filter || windowFilter;
      const [dashResult, biResult, invResult] = await Promise.allSettled([
        getAIDashboard(),
        getBusinessIntelligence({ days: active.days, bucket: active.bucket }),
        getInventorySummary(),
      ]);

      if (token !== reloadTokenRef.current) return;

      if (dashResult.status === 'fulfilled') {
        setDashboard(dashResult.value);
        setDashboardError('');
      } else {
        setDashboard(dashResult.value ?? null);
        setDashboardError(getErrorMessage(dashResult.reason));
      }

      if (biResult.status === 'fulfilled') {
        setBi(biResult.value);
        setBiError('');
      } else {
        setBi(biResult.value ?? null);
        setBiError(getErrorMessage(biResult.reason));
      }

      if (invResult.status === 'fulfilled') {
        setInventorySummary(invResult.value);
        setInventoryError('');
      } else {
        setInventorySummary(invResult.value ?? null);
        setInventoryError(getErrorMessage(invResult.reason));
      }
    } catch (err) {
      console.error(err);
      setDashboardError(getErrorMessage(err));
      setBiError(getErrorMessage(err));
      setInventoryError(getErrorMessage(err));
    } finally {
      if (token === reloadTokenRef.current) {
        setLoading(false);
      }
    }
  }, [windowFilter]);

  const refresh = () => loadData();

  const handleWindowChange = (patch) => {
    setWindowFilter((prev) => ({ ...prev, ...patch }));
  };

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return <Loader text="Running AI business analysis..." />;
  }

  if (!dashboard && !bi) {
    return (
      <div>
        <div className="flex-between mb-6">
          <div>
            <h1 className="page-title">AI Business Dashboard</h1>
            <p className="page-subtitle">Intelligent insights, forecasts and restocking recommendations</p>
          </div>
          <button className="btn btn-secondary" onClick={refresh}>
            <RefreshCw size={16} /> Retry
          </button>
        </div>
        <div className="glass-card" style={{ padding: '3rem', textAlign: 'center', color: 'var(--status-danger)' }}>
          {dashboardError || biError || 'Failed to load AI dashboard data.'}
        </div>
      </div>
    );
  }

  const forecast = Array.isArray(dashboard?.forecast) ? dashboard.forecast : [];
  const recommendations = Array.isArray(dashboard?.recommendations) ? dashboard.recommendations : [];
  const insights = Array.isArray(dashboard?.insights) ? dashboard.insights : [];

  const overview = bi?.business_overview || {};
  const metrics = bi?.dashboard_metrics || {};
  const sales = bi?.sales_intelligence || {};
  const inventory = bi?.inventory_intelligence || {};
  const purchases = bi?.purchase_intelligence || {};
  const attention = bi?.business_attention || {};

  const salesSummary = sales.summary || {};
  const trendPoints = Array.isArray(sales.trend?.points) ? sales.trend.points : [];
  const topProducts = Array.isArray(sales.top_products) ? sales.top_products : [];
  const salesGrowth = sales.growth || {};

  const lowStock = Array.isArray(inventory.low_stock?.items) ? inventory.low_stock.items : [];
  const outOfStock = Array.isArray(inventory.out_of_stock?.items) ? inventory.out_of_stock.items : [];

  const invSummary = inventorySummary || {};
  const summaryConditionClass = {
    'Needs Attention': 'badge-danger',
    'Low Stock Alert': 'badge-warning',
    Monitor: 'badge-info',
    Healthy: 'badge-success',
    'No Inventory': 'badge-secondary',
  }[invSummary.overall_condition] || 'badge-secondary';

  const purchaseSummary = purchases.summary || {};
  const bySupplier = Array.isArray(purchases.by_supplier) ? purchases.by_supplier : [];

  const attentionItems = [
    ...(Array.isArray(attention.low_stock) ? attention.low_stock : []).map((item) => ({
      ...item,
      status: 'Low Stock',
      badgeClass: 'badge-warning',
    })),
    ...(Array.isArray(attention.out_of_stock) ? attention.out_of_stock : []).map((item) => ({
      ...item,
      status: 'Out of Stock',
      badgeClass: 'badge-danger',
    })),
  ];
  const productsWithNoSales = Array.isArray(attention.products_with_no_sales)
    ? attention.products_with_no_sales
    : [];

  const trendData = trendPoints.map((p) => ({
    label: formatDate(p.label),
    revenue: p.revenue,
    units: p.units,
  }));

  return (
    <div>
      <div className="flex-between mb-6">
        <div>
          <h1 className="page-title">AI Business Dashboard</h1>
          <p className="page-subtitle">Intelligent insights, demand forecasts and restocking recommendations</p>
        </div>
        <button className="btn btn-secondary" onClick={refresh}>
          <RefreshCw size={16} /> Refresh AI
        </button>
      </div>

      {/* Overview stat cards */}
      <div className="grid-4 mb-6">
        <StatCard
          icon={TrendingUp}
          label="Net Profit (90 days)"
          value={currency(overview.net)}
          color="var(--status-success)"
          bg="var(--status-success-bg)"
        />
        <StatCard
          icon={IndianRupee}
          label="Sales Revenue (90 days)"
          value={currency(overview.revenue)}
          color="var(--accent-primary)"
          bg="var(--accent-glow)"
        />
        <StatCard
          icon={ShoppingBag}
          label="Stock Value"
          value={currency(metrics.stock_value)}
          color="var(--status-info)"
          bg="var(--status-info-bg)"
        />
        <StatCard
          icon={AlertTriangle}
          label="Low Stock Items"
          value={metrics.low_stock_count || 0}
          color="var(--status-warning)"
          bg="var(--status-warning-bg)"
        />
      </div>

      {/* AI inventory summary */}
      <div className="mb-6">
        <SectionCard
          icon={Package}
          title="AI Inventory Summary"
          color="var(--status-info)"
          headerRight={
            <span className={`badge ${summaryConditionClass}`}>
              {invSummary.overall_condition || '—'}
            </span>
          }
        >
          {inventoryError ? (
            <SectionError message={inventoryError} />
          ) : !invSummary.has_data ? (
            <EmptyState message={invSummary.summary || 'No inventory data to summarize yet.'} />
          ) : (
            <>
              <p style={{ color: 'var(--text-main)', lineHeight: 1.6, marginBottom: '1rem' }}>
                {invSummary.summary}
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, minmax(0, 1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
                {[
                  { label: 'Products', value: invSummary.population?.product_count ?? 0 },
                  { label: 'Units in Stock', value: invSummary.population?.stock_units ?? 0 },
                  { label: 'Stock Value', value: currency(invSummary.population?.stock_value) },
                  { label: 'Low Stock', value: invSummary.stock_health?.low_stock_count ?? 0 },
                  { label: 'Out of Stock', value: invSummary.stock_health?.out_of_stock_count ?? 0 },
                  { label: 'No Sales', value: invSummary.stock_health?.products_with_no_sales ?? 0 },
                ].map((row) => (
                  <div key={row.label} style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '0.75rem' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{row.label}</div>
                    <div style={{ fontWeight: 700, marginTop: '0.25rem' }}>{row.value}</div>
                  </div>
                ))}
              </div>

              <div className="grid-2" style={{ gap: '1rem' }}>
                <div>
                  <div style={{ fontWeight: 600, marginBottom: '0.5rem', fontSize: '0.875rem' }}>
                    Recommended Actions
                  </div>
                  {(invSummary.recommended_actions || []).length === 0 ? (
                    <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>No recommended actions.</div>
                  ) : (
                    <ul style={{ margin: 0, paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                      {(invSummary.recommended_actions || []).map((action) => (
                        <li key={action} style={{ fontSize: '0.875rem', color: 'var(--text-main)' }}>
                          {action}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <div>
                  <div style={{ fontWeight: 600, marginBottom: '0.5rem', fontSize: '0.875rem' }}>
                    Observations
                  </div>
                  {(invSummary.observations || []).length === 0 ? (
                    <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>No observations yet.</div>
                  ) : (
                    <ul style={{ margin: 0, paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                      {(invSummary.observations || []).map((obs) => (
                        <li key={obs} style={{ fontSize: '0.875rem', color: 'var(--text-main)' }}>
                          {obs}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </>
          )}
        </SectionCard>
      </div>

      {/* Business highlights + stock health */}
      {biError && (
        <div className="mb-6">
          <div className="glass-card" style={{ padding: '0.25rem 0' }}>
            <SectionError message={biError} />
          </div>
        </div>
      )}
      <div className="grid-2 mb-6">
        <SectionCard icon={Crown} title="Business Highlights" color="var(--accent-secondary)">
          {!overview.top_selling_product && !overview.top_customer && !overview.top_supplier ? (
            <EmptyState message="Not enough sales or purchase activity to compute highlights yet." />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {overview.top_selling_product && (
                <div className="flex-between" style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '0.85rem 1rem' }}>
                  <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Top Selling Product</span>
                  <span style={{ fontWeight: 600 }}>
                    {overview.top_selling_product.name}{' '}
                    <span style={{ color: 'var(--text-muted)', fontWeight: 500 }}>
                      · {overview.top_selling_product.units} units · {currency(overview.top_selling_product.revenue)}
                    </span>
                  </span>
                </div>
              )}
              {overview.top_customer && (
                <div className="flex-between" style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '0.85rem 1rem' }}>
                  <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Top Customer</span>
                  <span style={{ fontWeight: 600 }}>
                    {overview.top_customer.name}{' '}
                    <span style={{ color: 'var(--text-muted)', fontWeight: 500 }}>
                      · {currency(overview.top_customer.revenue)}
                    </span>
                  </span>
                </div>
              )}
              {overview.top_supplier && (
                <div className="flex-between" style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '0.85rem 1rem' }}>
                  <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Top Supplier</span>
                  <span style={{ fontWeight: 600 }}>
                    {overview.top_supplier.name}{' '}
                    <span style={{ color: 'var(--text-muted)', fontWeight: 500 }}>
                      · {currency(overview.top_supplier.spend)}
                    </span>
                  </span>
                </div>
              )}
            </div>
          )}
        </SectionCard>

        <SectionCard icon={Activity} title="Stock Health" color="var(--status-info)">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '0.75rem' }}>
            {[
              { label: 'Stock Units', value: metrics.stock_units || 0 },
              { label: 'Out of Stock', value: metrics.out_of_stock_count || 0 },
              { label: 'Products w/o Sales', value: metrics.products_with_no_sales || 0 },
              { label: 'Purchases', value: metrics.purchases_count || 0 },
              { label: 'Customers', value: metrics.customer_count || 0 },
              { label: 'Suppliers', value: metrics.supplier_count || 0 },
            ].map((row) => (
              <div key={row.label} className="flex-between" style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '0.85rem 1rem' }}>
                <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>{row.label}</span>
                <span style={{ fontWeight: 700 }}>{row.value}</span>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>

      {/* Business attention */}
      <div className="mb-6">
        <SectionCard icon={AlertTriangle} title="Needs Attention" color="var(--status-danger)">
          {attentionItems.length === 0 && productsWithNoSales.length === 0 ? (
            <EmptyState message="Everything looks healthy — no products currently need attention." />
          ) : (
            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>SKU</th>
                    <th>Status</th>
                    <th>Units to Reorder</th>
                  </tr>
                </thead>
                <tbody>
                  {attentionItems.map((item) => (
                    <tr key={`${item.status}-${item.sku || item.name}`}>
                      <td style={{ fontWeight: 600 }}>{item.name}</td>
                      <td>{item.sku || '—'}</td>
                      <td>
                        <span className={`badge ${item.badgeClass}`}>{item.status}</span>
                      </td>
                      <td style={{ fontWeight: 600, color: 'var(--status-warning)' }}>{item.to_reorder ?? 0} units</td>
                    </tr>
                  ))}
                  {productsWithNoSales.map((item) => (
                    <tr key={`nosales-${item.sku || item.name}`}>
                      <td style={{ fontWeight: 600 }}>{item.name}</td>
                      <td>{item.sku || '—'}</td>
                      <td>
                        <span className="badge badge-info">No Sales</span>
                      </td>
                      <td style={{ color: 'var(--text-muted)' }}>—</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </div>

      {/* Sales intelligence */}
      <div className="flex-between mb-4" style={{ flexWrap: 'wrap', gap: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)' }}>
          <CalendarRange size={16} />
          <span style={{ fontSize: '0.875rem' }}>Sales Analysis Period</span>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <select
            className="form-select"
            value={windowFilter.days}
            onChange={(e) => handleWindowChange({ days: Number(e.target.value) })}
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={180}>Last 6 months</option>
          </select>
          <select
            className="form-select"
            value={windowFilter.bucket}
            onChange={(e) => handleWindowChange({ bucket: e.target.value })}
          >
            <option value="month">By Month</option>
            <option value="week">By Week</option>
            <option value="day">By Day</option>
          </select>
        </div>
      </div>

      <div className="grid-2 mb-6">
        <SectionCard
          icon={ShoppingBag}
          title={`Sales Activity (Last ${windowFilter.days} Days)`}
          color="var(--status-success)"
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div className="flex-between" style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '0.85rem 1rem' }}>
              <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Revenue</span>
              <span style={{ fontWeight: 700, color: 'var(--status-success)' }}>{currency(salesSummary.revenue_in_period)}</span>
            </div>
            <div className="flex-between" style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '0.85rem 1rem' }}>
              <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Transactions</span>
              <span style={{ fontWeight: 700 }}>{salesSummary.sales_in_period || 0}</span>
            </div>
            <div className="flex-between" style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '0.85rem 1rem' }}>
              <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Average Sale Value</span>
              <span style={{ fontWeight: 700 }}>{currency(salesSummary.average_sale_value)}</span>
            </div>
            <div className="flex-between" style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '0.85rem 1rem' }}>
              <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Highest Sale</span>
              <span style={{ fontWeight: 700 }}>
                {salesSummary.highest_sale
                  ? `${salesSummary.highest_sale.invoice} · ${currency(salesSummary.highest_sale.amount)}`
                  : '—'}
              </span>
            </div>
          </div>
        </SectionCard>

        <SectionCard icon={TrendingUp} title="Revenue Trend" color="var(--accent-primary)">
          {trendData.length === 0 ? (
            <EmptyState message="Not enough sales data to plot a trend yet." />
          ) : (
            <div style={{ width: '100%', height: 250 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData} margin={{ top: 10, right: 10, left: 10, bottom: 5 }}>
                  <XAxis dataKey="label" stroke="var(--text-muted)" fontSize={11} />
                  <YAxis stroke="var(--text-muted)" fontSize={11} />
                  <Tooltip
                    cursor={{ stroke: 'var(--border-color)' }}
                    contentStyle={{
                      backgroundColor: 'var(--bg-secondary)',
                      borderColor: 'var(--border-color)',
                      borderRadius: '8px',
                      color: '#fff',
                    }}
                    formatter={(value) => currency(value)}
                  />
                  <Line type="monotone" dataKey="revenue" stroke="var(--status-success)" strokeWidth={2} dot={{ r: 3, fill: 'var(--status-success)' }} name="Revenue" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </SectionCard>
      </div>

      {/* Sales growth vs previous period */}
      <div className="mb-6">
        <SectionCard icon={TrendingUp} title={`Growth: Current vs Previous ${windowFilter.days} Days`} color="var(--accent-primary)">
          {trendData.length === 0 ? (
            <EmptyState message="Not enough sales data to compare against a previous period yet." />
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '0.75rem' }}>
              {[
                {
                  label: 'Revenue',
                  current: salesGrowth.current_revenue,
                  previous: salesGrowth.previous_revenue,
                  pct: salesGrowth.revenue_growth_percent,
                  money: true,
                },
                {
                  label: 'Units Sold',
                  current: salesGrowth.current_units,
                  previous: salesGrowth.previous_units,
                  pct: salesGrowth.units_growth_percent,
                  money: false,
                },
              ].map((row) => {
                const hasPct = row.pct !== null && row.pct !== undefined;
                const up = hasPct && row.pct > 0;
                const down = hasPct && row.pct < 0;
                const badgeClass = up ? 'badge-success' : down ? 'badge-danger' : 'badge-secondary';
                const badgeText = !hasPct
                  ? '—'
                  : `${up ? '▲' : down ? '▼' : ''} ${row.pct > 0 ? '+' : ''}${row.pct.toFixed(1)}%`;
                const format = (value) => (row.money ? currency(value) : `${value ?? 0} units`);
                return (
                  <div key={row.label} style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '0.85rem 1rem' }}>
                    <div className="flex-between mb-2">
                      <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>{row.label} (this period)</span>
                      <span className={`badge ${badgeClass}`}>{badgeText}</span>
                    </div>
                    <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>{format(row.current)}</div>
                    <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                      Previous period: {format(row.previous)}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </SectionCard>
      </div>

      {/* Top products */}
      <div className="mb-6">
        <SectionCard icon={Crown} title="Best-Selling Products" color="var(--status-success)">
          {topProducts.length === 0 ? (
            <EmptyState message="No product sales recorded yet." />
          ) : (
            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>SKU</th>
                    <th>Units Sold</th>
                    <th>Sales Revenue</th>
                  </tr>
                </thead>
                <tbody>
                  {topProducts.map((item) => (
                    <tr key={item.sku || item.name}>
                      <td style={{ fontWeight: 600 }}>{item.name}</td>
                      <td>{item.sku || '—'}</td>
                      <td>{item.units_sold ?? 0} units</td>
                      <td style={{ fontWeight: 600, color: 'var(--status-success)' }}>{currency(item.sales_revenue)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </div>

      {/* Inventory intelligence */}
      <div className="grid-2 mb-6">
        <SectionCard icon={PackageX} title="Low Stock Products" color="var(--status-warning)">
          {lowStock.length === 0 ? (
            <EmptyState message="All products are above their minimum stock levels." />
          ) : (
            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Qty</th>
                    <th>Min</th>
                    <th>Reorder</th>
                  </tr>
                </thead>
                <tbody>
                  {lowStock.map((item) => (
                    <tr key={item.sku || item.name}>
                      <td style={{ fontWeight: 600 }}>{item.name}</td>
                      <td style={{ color: 'var(--status-warning)' }}>{item.quantity}</td>
                      <td>{item.minimum_stock}</td>
                      <td style={{ fontWeight: 600 }}>+{item.to_reorder ?? 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard icon={AlertTriangle} title="Out of Stock" color="var(--status-danger)">
          {outOfStock.length === 0 ? (
            <EmptyState message="No products are currently out of stock." />
          ) : (
            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>SKU</th>
                  </tr>
                </thead>
                <tbody>
                  {outOfStock.map((item) => (
                    <tr key={item.sku || item.name}>
                      <td style={{ fontWeight: 600 }}>{item.name}</td>
                      <td>{item.sku || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </div>

      {/* Purchase intelligence */}
      <div className="grid-2 mb-6">
        <SectionCard icon={Truck} title={`Purchases (Last ${windowFilter.days} Days)`} color="var(--status-info)">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div className="flex-between" style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '0.85rem 1rem' }}>
              <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Total Spend</span>
              <span style={{ fontWeight: 700, color: 'var(--status-info)' }}>{currency(purchaseSummary.spend_in_period)}</span>
            </div>
            <div className="flex-between" style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '0.85rem 1rem' }}>
              <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Purchase Orders</span>
              <span style={{ fontWeight: 700 }}>{purchaseSummary.purchases_in_period || 0}</span>
            </div>
            <div className="flex-between" style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '0.85rem 1rem' }}>
              <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Average Purchase</span>
              <span style={{ fontWeight: 700 }}>{currency(purchaseSummary.average_purchase_value)}</span>
            </div>
            <div className="flex-between" style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '0.85rem 1rem' }}>
              <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Highest Purchase</span>
              <span style={{ fontWeight: 700 }}>
                {purchaseSummary.highest_purchase
                  ? `${purchaseSummary.highest_purchase.invoice} · ${currency(purchaseSummary.highest_purchase.amount)}`
                  : '—'}
              </span>
            </div>
          </div>
        </SectionCard>

        <SectionCard icon={Users} title="Spend by Supplier" color="var(--accent-secondary)">
          {bySupplier.length === 0 ? (
            <EmptyState message="No supplier spend recorded in this period." />
          ) : (
            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Supplier</th>
                    <th>Orders</th>
                    <th>Units</th>
                    <th>Spend</th>
                  </tr>
                </thead>
                <tbody>
                  {bySupplier.map((item) => (
                    <tr key={item.supplier}>
                      <td style={{ fontWeight: 600 }}>{item.supplier}</td>
                      <td>{item.orders ?? 0}</td>
                      <td>{item.units ?? 0}</td>
                      <td style={{ fontWeight: 600, color: 'var(--status-info)' }}>{currency(item.spend)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </div>

      {/* AI forecast & recommendations */}
      {dashboardError && (
        <div className="mb-6">
          <div className="glass-card" style={{ padding: '0.25rem 0' }}>
            <SectionError message={dashboardError} />
          </div>
        </div>
      )}
      <div className="grid-2 mb-6">
        <SectionCard icon={TrendingUp} title="Demand Forecast" color="var(--accent-primary)">
          {forecast.length === 0 ? (
            <EmptyState message="Not enough sales data to generate forecasts yet." />
          ) : (
            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Predicted Demand</th>
                  </tr>
                </thead>
                <tbody>
                  {forecast.map((item) => (
                    <tr key={item.product_id}>
                      <td style={{ fontWeight: 600 }}>{item.product_name}</td>
                      <td style={{ fontWeight: 700, color: 'var(--status-info)' }}>
                        {item.predicted_quantity} units
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard icon={ShoppingCart} title="Reorder Recommendations" color="var(--status-success)">
          {recommendations.length === 0 ? (
            <EmptyState message="No restock recommendations right now." />
          ) : (
            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Current</th>
                    <th>Forecast</th>
                    <th>Order</th>
                  </tr>
                </thead>
                <tbody>
                  {recommendations.map((item) => (
                    <tr key={item.product_id}>
                      <td style={{ fontWeight: 600 }}>{item.product_name}</td>
                      <td>{item.current_stock} units</td>
                      <td>{item.forecast} units</td>
                      <td>
                        <span className="badge badge-warning">
                          +{item.recommended_order} units
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </div>

      {/* AI insights */}
      <SectionCard
        icon={Lightbulb}
        title="AI Insights"
        color="var(--accent-secondary)"
        headerRight={
          <span className="badge badge-info" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
            <Cpu size={12} /> Generated by AI
          </span>
        }
      >
        {insights.length === 0 ? (
          <EmptyState message="No insights generated yet." />
        ) : (
          <ul style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', padding: 0, listStyle: 'none' }}>
            {insights.map((text, index) => (
              <li
                key={index}
                style={{
                  padding: '0.875rem 1rem',
                  background: 'var(--bg-primary)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-main)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                }}
              >
                <Sparkles size={16} color="var(--accent-secondary)" />
                {text}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
    </div>
  );
};
