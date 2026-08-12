import React, { useEffect, useState } from 'react';
import {
  FileText,
  Plus,
  Edit2,
  Trash2,
  Search,
  RefreshCw,
  AlertTriangle,
  Sparkles,
  LayoutGrid,
  TrendingUp,
  ShoppingCart,
  Lightbulb,
  PackageX,
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  ReferenceLine,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from 'recharts';
import { aiInsightApi, fetchAllPages } from '../api';
import {
  getForecastDetail,
  getRecommendations,
  getBusinessIntelligence,
  getErrorMessage,
} from '../services/aiService';
import { Modal, Loader } from '../components/common/UIComponents';
import { useNotification } from '../context/NotificationContext';
import { formatDateTime, formatCurrency } from '../utils/formatters';

const INSIGHT_TYPES = [
  { value: 'FORECAST', label: 'Demand Forecast' },
  { value: 'LOW_STOCK', label: 'Low Stock Prediction' },
  { value: 'RECOMMENDATION', label: 'Inventory Recommendation' },
  { value: 'ANALYSIS', label: 'Business Analysis' },
];

const FILTERS = [
  { key: 'OVERVIEW', label: 'Stored Insights', icon: LayoutGrid, hint: 'Saved AI insight records' },
  { key: 'FORECAST', label: 'Forecast', icon: TrendingUp, hint: 'Live demand forecast' },
  { key: 'LOW_STOCK', label: 'Low Stock', icon: AlertTriangle, hint: 'Live stock alerts' },
  { key: 'RECOMMENDATION', label: 'Recommendations', icon: ShoppingCart, hint: 'Live reorder suggestions' },
  { key: 'ANALYSIS', label: 'Analysis', icon: Lightbulb, hint: 'Live business overview' },
];

const TYPE_BADGES = {
  FORECAST: 'badge-info',
  LOW_STOCK: 'badge-warning',
  RECOMMENDATION: 'badge-success',
  ANALYSIS: 'badge-secondary',
};

const tooltipStyle = {
  backgroundColor: 'var(--bg-secondary)',
  borderColor: 'var(--border-color)',
  borderRadius: '8px',
  color: '#fff',
};

const panelTitleStyle = {
  fontSize: '1rem',
  fontWeight: 600,
  display: 'flex',
  alignItems: 'center',
  gap: '0.5rem',
};

const typeLabel = (value) => {
  const found = INSIGHT_TYPES.find((t) => t.value === value);
  return found ? found.label : value || '—';
};

const typeBadgeClass = (value) => TYPE_BADGES[value] || 'badge-info';

const getApiError = (err) => {
  const data = err.response?.data;
  if (!data) return 'Operation failed. Please try again.';
  if (Array.isArray(data)) return data[0] || 'Operation failed.';
  for (const key of Object.keys(data)) {
    const value = data[key];
    if (Array.isArray(value) && value.length) return value[0];
    if (typeof value === 'string') return value;
  }
  return 'Operation failed. Please try again.';
};

const truncate = (text = '', max = 140) =>
  text.length > max ? `${text.slice(0, max).trimEnd()}…` : text;

const initialState = {
  title: '',
  description: '',
  insight_type: '',
  confidence_score: '',
  generated_by: 'AI',
  is_active: true,
};

const StatBox = ({ label, value, color = 'var(--text-main)' }) => (
  <div
    style={{
      background: 'var(--bg-primary)',
      border: '1px solid var(--border-color)',
      borderRadius: 'var(--radius-md)',
      padding: '0.75rem 1rem',
      flex: '1 1 140px',
      minWidth: '120px',
    }}
  >
    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{label}</div>
    <div style={{ fontWeight: 700, marginTop: '0.25rem', fontSize: '1rem', color }}>{value}</div>
  </div>
);

const PanelNotice = ({ icon: Icon = AlertTriangle, message }) => (
  <div
    style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '0.5rem',
      padding: '2rem 1rem',
      textAlign: 'center',
      color: 'var(--text-muted)',
      fontSize: '0.875rem',
    }}
  >
    <Icon size={20} color="var(--text-dim)" />
    <div>{message}</div>
  </div>
);

const forecastDateLabel = (value) => {
  if (!value) return '';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString('en-US', { year: '2-digit', month: 'short', day: 'numeric' });
};

const InsufficientDataNotice = ({ product }) => (
  <div style={{ textAlign: 'center', padding: '2rem 1rem' }}>
    <AlertTriangle size={30} color="var(--status-warning)" style={{ marginBottom: '0.5rem' }} />
    <div style={{ fontWeight: 700, color: 'var(--text-main)', marginBottom: '0.5rem' }}>
      Not enough sales history
    </div>
    <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', maxWidth: '520px', margin: '0 auto 0.5rem' }}>
      {product.message ||
        'Demand forecasting requires more historical sales for this product.'}
    </p>
    <p style={{ color: 'var(--text-dim)', fontSize: '0.8125rem', margin: 0 }}>
      Observed {product.observed_weeks ?? 0} week(s) with sales across {product.sale_rows ?? 0} sale
      record(s) in the last 12 weeks.
    </p>
  </div>
);

const ForecastOverview = ({ products, forecastWeeks, onSelect, resultLabel }) => (
  <div className="table-responsive">
    <table className="custom-table">
      <thead>
        <tr>
          <th>Product</th>
          <th>Current Stock</th>
          <th>Forecast Next {forecastWeeks} Weeks</th>
          <th>Trend</th>
          <th>Status</th>
          <th />
        </tr>
      </thead>
      <tbody>
        {products.map((item) => (
          <tr
            key={item.product?.id}
            style={{ cursor: 'pointer' }}
            onClick={() => onSelect(item.product?.id)}
          >
            <td style={{ fontWeight: 600 }}>{item.product?.name}</td>
            <td>{item.current_stock ?? 0} units</td>
            <td style={{ fontWeight: 700, color: 'var(--status-info)' }}>
              {item.forecastable ? `${item.forecast_total ?? 0} units` : '—'}
            </td>
            <td>
              {item.forecastable && item.trend ? (
                <span
                  className={`badge ${
                    item.trend === 'increasing'
                      ? 'badge-danger'
                      : item.trend === 'decreasing'
                        ? 'badge-warning'
                        : 'badge-secondary'
                  }`}
                >
                  {item.trend}
                </span>
              ) : (
                '—'
              )}
            </td>
            <td>
              {item.forecastable ? (
                <span className="badge badge-success">Forecast ready</span>
              ) : (
                <span className="badge badge-warning">Needs more history</span>
              )}
            </td>
            <td>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelect(item.product?.id);
                }}
              >
                View chart
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
    {resultLabel && (
      <p style={{ margin: '0.5rem 0 0', fontSize: '0.8125rem', color: 'var(--text-dim)' }}>
        {resultLabel}
      </p>
    )}
  </div>
);

const ForecastDetailChart = ({ product }) => {
  const historical = Array.isArray(product.historical) ? product.historical : [];
  const forecast = Array.isArray(product.forecast) ? product.forecast : [];
  const chartData = [
    ...historical.map((point) => ({
      label: forecastDateLabel(point.week),
      actual: point.units,
      forecast: null,
    })),
    ...forecast.map((point) => ({
      label: forecastDateLabel(point.week),
      actual: null,
      forecast: point.units,
    })),
  ];
  const boundaryLabel =
    historical.length > 0 && chartData.length > historical.length
      ? chartData[historical.length].label
      : undefined;

  const stats = [
    {
      label: 'Forecast next 4 weeks',
      value: `${product.forecast_total ?? 0} units`,
      color: 'var(--status-info)',
    },
    {
      label: 'Current stock',
      value: `${product.current_stock ?? 0} units`,
    },
    {
      label: 'Avg weekly demand',
      value: `${product.average_weekly_demand ?? 0} units`,
    },
    {
      label: 'Trend',
      value: product.trend ?? '—',
      color:
        product.trend === 'increasing'
          ? 'var(--status-danger)'
          : product.trend === 'decreasing'
            ? 'var(--status-warning)'
            : 'var(--text-main)',
    },
  ];

  return (
    <>
      <div style={{ width: '100%', height: 320, marginBottom: '0.75rem' }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 12, right: 20, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
              tickLine={false}
              interval="preserveStartEnd"
              angle={-25}
              textAnchor="end"
              height={52}
            />
            <YAxis
              tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
              tickLine={false}
              allowDecimals={false}
            />
            <Tooltip
              cursor={{ stroke: 'var(--border-color)' }}
              contentStyle={tooltipStyle}
              formatter={(value, name) =>
                name === 'Forecast'
                  ? [`${value} units`, 'Forecast']
                  : [`${value} units`, 'Actual demand']
              }
            />
            <Legend wrapperStyle={{ fontSize: '0.8125rem' }} />
            {boundaryLabel && (
              <ReferenceLine
                x={boundaryLabel}
                stroke="var(--text-dim)"
                strokeDasharray="4 4"
                label={{
                  value: 'Forecast begins',
                  position: 'insideTopRight',
                  fill: 'var(--text-muted)',
                  fontSize: 11,
                }}
              />
            )}
            <Line
              type="monotone"
              dataKey="actual"
              name="Actual demand"
              stroke="var(--accent-primary)"
              strokeWidth={2}
              dot={{ r: 3, fill: 'var(--accent-primary)' }}
              activeDot={{ r: 5 }}
              connectNulls={false}
            />
            <Line
              type="monotone"
              dataKey="forecast"
              name="Forecast"
              stroke="var(--accent-secondary)"
              strokeWidth={2}
              strokeDasharray="6 4"
              dot={{ r: 4, fill: 'var(--accent-secondary)' }}
              activeDot={{ r: 5 }}
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '0.75rem' }}>
        {stats.map((stat) => (
          <StatBox key={stat.label} label={stat.label} value={stat.value} color={stat.color} />
        ))}
      </div>
      <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', margin: 0 }}>
        Solid line = actual weekly sales for <strong>{product.product?.name}</strong> over the last 12
        weeks (zero-filled). Dashed line = forecast for the next 4 weeks.{' '}
        {product.method_note || ''}
      </p>
    </>
  );
};

const ForecastProductHeader = ({ product, onBack }) => (
  <div className="flex-between mb-4" style={{ flexWrap: 'wrap', gap: '0.75rem' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
      <button type="button" className="btn btn-secondary btn-sm" onClick={onBack}>
        ← All products
      </button>
      <h4 style={{ margin: 0, fontWeight: 700, color: 'var(--text-main)' }}>
        {product.product?.name}
      </h4>
      {product.forecastable ? (
        <span className="badge badge-info">Forecast ready</span>
      ) : (
        <span className="badge badge-warning">Needs more history</span>
      )}
    </div>
  </div>
);

const ForecastPanel = ({ data, loading, error }) => {
  const [selectedProductId, setSelectedProductId] = useState('all');
  const [productQuery, setProductQuery] = useState('');

  if (loading) return <Loader text="Loading demand forecast..." />;
  if (error) return <PanelNotice message={error} />;

  const products = Array.isArray(data?.products) ? data.products : [];
  const forecastWeeks = data?.forecast_weeks ?? 4;

  if (products.length === 0) {
    return (
      <PanelNotice
        icon={TrendingUp}
        message="No demand forecast data available yet. Forecasts appear once products have enough sales history."
      />
    );
  }

  const selected =
    selectedProductId === 'all'
      ? null
      : products.find(
          (item) => String(item.product?.id) === String(selectedProductId)
        ) || null;

  const query = productQuery.trim().toLowerCase();
  const visibleProducts = query
    ? products.filter((item) =>
        (item.product?.name || '').toLowerCase().includes(query)
      )
    : products;

  const select = (id) => setSelectedProductId(String(id));

  return (
    <div className="glass-card">
      <div className="flex-between mb-4" style={{ flexWrap: 'wrap', gap: '0.75rem' }}>
        <h3 style={panelTitleStyle}>
          <TrendingUp size={16} color="var(--accent-primary)" /> Demand Forecast
        </h3>
        <span className="badge badge-info">Live — from current sales data</span>
      </div>

      {selected ? (
        <ForecastProductHeader product={selected} onBack={() => select('all')} />
      ) : (
        <div className="mb-4" style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', width: '300px', maxWidth: '100%' }}>
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
              placeholder="Search products..."
              value={productQuery}
              onChange={(e) => setProductQuery(e.target.value)}
            />
          </div>
          <select
            className="form-select"
            value={selectedProductId}
            onChange={(e) => select(e.target.value)}
            style={{ width: 'auto', maxWidth: '100%' }}
            aria-label="Select a product to inspect its weekly demand forecast"
          >
            <option value="all">All products (overview)</option>
            {products.map((item) => (
              <option key={item.product?.id} value={item.product?.id}>
                {item.product?.name}
                {item.forecastable
                  ? ` — ${item.forecast_total ?? 0} units`
                  : ' — not enough history'}
              </option>
            ))}
          </select>
        </div>
      )}

      {selected ? (
        selected.forecastable ? (
          <ForecastDetailChart product={selected} />
        ) : (
          <InsufficientDataNotice product={selected} />
        )
      ) : visibleProducts.length === 0 ? (
        <PanelNotice
          icon={Search}
          message={`No products match "${productQuery}". Try a different product name.`}
        />
      ) : visibleProducts.length === products.length ? (
        <ForecastOverview
          products={visibleProducts}
          forecastWeeks={forecastWeeks}
          onSelect={select}
          resultLabel={`${products.length} product(s) with recent sales in the forecast window.`}
        />
      ) : (
        <ForecastOverview
          products={visibleProducts}
          forecastWeeks={forecastWeeks}
          onSelect={select}
          resultLabel={`${visibleProducts.length} of ${products.length} products shown.`}
        />
      )}
    </div>
  );
};

const LowStockPanel = ({ data, loading, error }) => {
  if (loading) return <Loader text="Loading stock intelligence..." />;
  if (error) return <PanelNotice message={error} />;
  const inventory = data?.inventory_intelligence || {};
  const lowItems = Array.isArray(inventory.low_stock?.items) ? inventory.low_stock.items : [];
  const outItems = Array.isArray(inventory.out_of_stock?.items) ? inventory.out_of_stock.items : [];
  const rows = [
    ...lowItems.map((item) => ({
      key: `low-${item.sku || item.name}`,
      product: item.name,
      sku: item.sku,
      current: item.quantity,
      minStock: item.minimum_stock,
      reorder: item.to_reorder,
      out: false,
    })),
    ...outItems.map((item) => ({
      key: `out-${item.sku || item.name}`,
      product: item.name,
      sku: item.sku,
      current: 0,
      minStock: item.minimum_stock ?? null,
      reorder: item.to_reorder,
      out: true,
    })),
  ];
  if (rows.length === 0) {
    return (
      <PanelNotice message="All products are above their minimum stock levels — no low-stock or out-of-stock items right now." />
    );
  }
  return (
    <div className="glass-card">
      <div className="flex-between mb-4">
        <h3 style={panelTitleStyle}>
          <PackageX size={16} color="var(--status-warning)" /> Stock Status
        </h3>
        <span className="badge badge-warning">
          {rows.filter((row) => !row.out).length} low · {rows.filter((row) => row.out).length} out
        </span>
      </div>
      <div className="table-responsive">
        <table className="custom-table">
          <thead>
            <tr>
              <th>Product</th>
              <th>SKU</th>
              <th>Current Stock</th>
              <th>Minimum</th>
              <th>Status</th>
              <th>Recommended Reorder</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key}>
                <td style={{ fontWeight: 600 }}>{row.product}</td>
                <td style={{ color: 'var(--text-muted)' }}>{row.sku || '—'}</td>
                <td style={{ fontWeight: 600, color: row.out ? 'var(--status-danger)' : 'var(--status-warning)' }}>
                  {row.current}
                </td>
                <td>{row.minStock ?? '—'}</td>
                <td>
                  <span className={`badge ${row.out ? 'badge-danger' : 'badge-warning'}`}>
                    {row.out ? 'Out of Stock' : 'Low Stock'}
                  </span>
                </td>
                <td style={{ fontWeight: 600 }}>
                  {row.reorder != null && row.reorder > 0 ? `+${row.reorder} units` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const RecommendationPanel = ({ data, loading, error, onRetry }) => {
  if (loading) return <Loader text="Generating recommendations..." />;
  if (error)
    return (
      <div style={{ padding: '3rem', textAlign: 'center' }}>
        <AlertTriangle size={28} color="var(--status-danger)" style={{ marginBottom: '0.5rem' }} />
        <div style={{ color: 'var(--status-danger)', marginBottom: '1rem' }}>{error}</div>
        <button className="btn btn-secondary" onClick={onRetry}>
          <RefreshCw size={16} /> Retry
        </button>
      </div>
    );
  const items = Array.isArray(data) ? data : [];
  if (items.length === 0) {
    return <PanelNotice message="No reorder recommendations right now. Stock levels are healthy or there is not enough forecast history." />;
  }
  return (
    <div className="glass-card">
      <div className="flex-between mb-4">
        <h3 style={panelTitleStyle}>
          <ShoppingCart size={16} color="var(--status-success)" /> Reorder Recommendations
        </h3>
        <span className="badge badge-success">{items.length} products</span>
      </div>
      <div className="table-responsive">
        <table className="custom-table">
          <thead>
            <tr>
              <th>Product</th>
              <th>Current Stock</th>
              <th>Minimum</th>
              <th>Forecast Demand</th>
              <th>Recommended Order</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const order = item.recommended_order ?? 0;
              const needsRestock = order > 0;
              return (
                <tr key={item.product_id}>
                  <td style={{ fontWeight: 600 }}>{item.product_name}</td>
                  <td>{item.current_stock ?? 0} units</td>
                  <td>{item.minimum_stock ?? '—'}</td>
                  <td>{item.forecast ?? 0} units</td>
                  <td style={{ fontWeight: 700, color: 'var(--status-success)' }}>+{order} units</td>
                  <td>
                    <span className={`badge ${needsRestock ? 'badge-warning' : 'badge-success'}`}>
                      {needsRestock ? 'Restock' : 'Adequate'}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const AnalysisPanel = ({ data, loading, error }) => {
  if (loading) return <Loader text="Loading business analysis..." />;
  if (error) return <PanelNotice message={error} />;
  const overview = data?.business_overview || {};
  const metrics = data?.dashboard_metrics || {};
  const stats = [
    { label: 'Revenue (90 days)', value: formatCurrency(overview.revenue) },
    { label: 'Net Profit (90 days)', value: formatCurrency(overview.net) },
    { label: 'Stock Value', value: formatCurrency(metrics.stock_value) },
    { label: 'Stock Units', value: metrics.stock_units ?? 0 },
    { label: 'Low Stock Items', value: metrics.low_stock_count ?? 0 },
    { label: 'Out of Stock', value: metrics.out_of_stock_count ?? 0 },
    { label: 'Purchases', value: metrics.purchases_count ?? 0 },
    { label: 'Customers', value: metrics.customer_count ?? 0 },
  ];
  return (
    <div className="glass-card">
      <div className="flex-between mb-4">
        <h3 style={panelTitleStyle}>
          <Lightbulb size={16} color="var(--accent-secondary)" /> Business Analysis
        </h3>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '1rem' }}>
        {stats.map((stat) => (
          <StatBox key={stat.label} label={stat.label} value={stat.value} />
        ))}
      </div>
      {overview.top_selling_product && (
        <p style={{ fontSize: '0.875rem', color: 'var(--text-main)', margin: 0 }}>
          Top selling product:{' '}
          <strong>{overview.top_selling_product.name}</strong> · {overview.top_selling_product.units ?? 0} units ·{' '}
          {formatCurrency(overview.top_selling_product.revenue)}
        </p>
      )}
    </div>
  );
};

export const AIInsightsPage = () => {
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState('');
  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState('OVERVIEW');

  const [aiData, setAiData] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState('');
  const [reloadToken, setReloadToken] = useState(0);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [formData, setFormData] = useState(initialState);
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [generating, setGenerating] = useState(false);

  const { showToast } = useNotification();

  const fetchInsights = async () => {
    setLoading(true);
    setListError('');
    try {
      const items = await fetchAllPages((params) => aiInsightApi.getAll(params));
      setInsights(items);
    } catch (err) {
      setListError(getApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInsights();
  }, []);

  useEffect(() => {
    let cancelled = false;
    if (activeFilter === 'OVERVIEW') {
      setAiData(null);
      setAiError('');
      setAiLoading(false);
      return undefined;
    }
    setAiLoading(true);
    setAiError('');
    let request;
    if (activeFilter === 'FORECAST') {
      request = getForecastDetail;
    } else if (activeFilter === 'RECOMMENDATION') {
      request = getRecommendations;
    } else {
      request = getBusinessIntelligence;
    }
    request()
      .then((data) => {
        if (!cancelled) setAiData(data);
      })
      .catch((err) => {
        if (!cancelled) setAiError(getErrorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setAiLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeFilter, reloadToken]);

  const openCreate = () => {
    setEditing(null);
    setFormData(initialState);
    setFormError('');
    setIsModalOpen(true);
  };

  const openEdit = (insight) => {
    setEditing(insight);
    setFormData({
      title: insight.title,
      description: insight.description,
      insight_type: insight.insight_type,
      confidence_score:
        insight.confidence_score === undefined || insight.confidence_score === null
          ? ''
          : String(insight.confidence_score),
      generated_by: insight.generated_by || 'AI',
      is_active: Boolean(insight.is_active),
    });
    setFormError('');
    setIsModalOpen(true);
  };

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.title.trim() || !formData.description.trim() || !formData.insight_type) {
      setFormError('Title, description and insight type are required.');
      return;
    }
    setSubmitting(true);
    setFormError('');
    try {
      const payload = {
        title: formData.title.trim(),
        description: formData.description.trim(),
        insight_type: formData.insight_type,
        confidence_score: formData.confidence_score === '' ? 0 : formData.confidence_score,
        generated_by: formData.generated_by.trim() || 'AI',
        is_active: formData.is_active,
      };
      if (editing) {
        await aiInsightApi.update(editing.id, payload);
        showToast('AI insight updated successfully.', 'success');
      } else {
        await aiInsightApi.create(payload);
        showToast('AI insight created successfully.', 'success');
      }
      setIsModalOpen(false);
      fetchInsights();
    } catch (err) {
      setFormError(getApiError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (insight) => {
    if (!window.confirm(`Delete the AI insight "${insight.title}"?`)) return;
    setDeletingId(insight.id);
    try {
      await aiInsightApi.delete(insight.id);
      showToast('AI insight deleted.', 'success');
      fetchInsights();
    } catch (err) {
      showToast(getApiError(err), 'error');
    } finally {
      setDeletingId(null);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await aiInsightApi.generate();
      const { created = 0, skipped = 0, message = 'AI insights generated successfully.' } =
        res.data || {};
      showToast(`${message} (${created} new, ${skipped} already present)`, 'success');
      fetchInsights();
    } catch (err) {
      showToast(getApiError(err), 'error');
    } finally {
      setGenerating(false);
    }
  };

  const summaryCounts = { FORECAST: 0, LOW_STOCK: 0, RECOMMENDATION: 0, ANALYSIS: 0 };
  insights.forEach((item) => {
    if (summaryCounts[item.insight_type] !== undefined) summaryCounts[item.insight_type] += 1;
  });

  const filteredInsights = insights.filter((item) => {
    if (activeFilter !== 'OVERVIEW' && item.insight_type !== activeFilter) return false;
    const query = search.trim().toLowerCase();
    if (!query) return true;
    return (
      (item.title || '').toLowerCase().includes(query) ||
      (item.description || '').toLowerCase().includes(query) ||
      typeLabel(item.insight_type).toLowerCase().includes(query)
    );
  });

  const retry = () => setReloadToken((t) => t + 1);

  const panelProps = { data: aiData, loading: aiLoading, error: aiError, onRetry: retry };

  return (
    <div>
      <div className="flex-between mb-6" style={{ flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 className="page-title">
            <FileText
              size={24}
              style={{ verticalAlign: 'middle', marginRight: '0.5rem', color: 'var(--accent-primary)' }}
            />
            AI Insights
          </h1>
          <p className="page-subtitle">
            Stored AI insight records and live analysis from current business data
          </p>
        </div>
        {activeFilter === 'OVERVIEW' && (
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button className="btn btn-secondary" onClick={handleGenerate} disabled={generating}>
              <Sparkles size={18} /> {generating ? 'Generating...' : 'Generate Insights'}
            </button>
            <button className="btn btn-primary" onClick={openCreate}>
              <Plus size={18} /> New Insight
            </button>
          </div>
        )}
      </div>

      <div className="mb-6">
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {FILTERS.map((filter) => {
            const Icon = filter.icon;
            const active = activeFilter === filter.key;
            return (
              <button
                key={filter.key}
                type="button"
                className={`btn btn-sm ${active ? 'btn-primary' : 'btn-secondary'}`}
                aria-pressed={active}
                title={filter.hint}
                onClick={() => setActiveFilter(filter.key)}
              >
                <Icon size={15} /> {filter.label}
              </button>
            );
          })}
        </div>
      </div>

      {activeFilter === 'OVERVIEW' ? (
        <>
          <div
            className="mb-6"
            style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}
          >
            <StatBox label="Total Insights" value={insights.length} color="var(--accent-primary)" />
            <StatBox label="Forecast" value={summaryCounts.FORECAST} color="var(--status-info)" />
            <StatBox label="Low Stock" value={summaryCounts.LOW_STOCK} color="var(--status-warning)" />
            <StatBox label="Recommendation" value={summaryCounts.RECOMMENDATION} color="var(--status-success)" />
            <StatBox label="Analysis" value={summaryCounts.ANALYSIS} />
          </div>

          <div className="glass-card">
            {listError ? (
              <div style={{ padding: '3rem', textAlign: 'center' }}>
                <AlertTriangle size={28} color="var(--status-danger)" style={{ marginBottom: '0.5rem' }} />
                <div style={{ color: 'var(--status-danger)', marginBottom: '1rem' }}>{listError}</div>
                <button className="btn btn-secondary" onClick={fetchInsights}>
                  <RefreshCw size={16} /> Retry
                </button>
              </div>
            ) : (
              <>
                <div className="flex-between mb-4">
                  <h3 style={panelTitleStyle}>
                    <LayoutGrid size={16} color="var(--accent-primary)" /> Stored Insight Records
                  </h3>
                  <div style={{ position: 'relative', width: '320px', maxWidth: '100%' }}>
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
                      placeholder="Search insights..."
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                    />
                  </div>
                </div>

                {loading ? (
                  <Loader text="Loading AI insights..." />
                ) : filteredInsights.length === 0 ? (
                  <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                    {insights.length === 0
                      ? 'No AI insights yet. Click "Generate Insights" or "New Insight" to create one.'
                      : 'No insights match your search or filter.'}
                  </div>
                ) : (
                  <div className="table-responsive">
                    <table className="custom-table">
                      <thead>
                        <tr>
                          <th>Insight</th>
                          <th>Description</th>
                          <th>Type</th>
                          <th>Confidence</th>
                          <th>Source</th>
                          <th>Status</th>
                          <th>Created</th>
                          <th>Updated</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredInsights.map((item) => (
                          <tr key={item.id}>
                            <td style={{ fontWeight: 600, color: 'var(--text-main)' }}>{item.title}</td>
                            <td style={{ color: 'var(--text-muted)', maxWidth: '280px' }} title={item.description}>
                              {item.description ? truncate(item.description) : '—'}
                            </td>
                            <td>
                              <span className={`badge ${typeBadgeClass(item.insight_type)}`}>
                                {typeLabel(item.insight_type)}
                              </span>
                            </td>
                            <td>{Number(item.confidence_score ?? 0).toFixed(2)}</td>
                            <td>{item.generated_by || 'AI'}</td>
                            <td>
                              <span className={`badge ${item.is_active ? 'badge-success' : 'badge-secondary'}`}>
                                {item.is_active ? 'Active' : 'Inactive'}
                              </span>
                            </td>
                            <td style={{ whiteSpace: 'nowrap', color: 'var(--text-muted)' }}>{formatDateTime(item.created_at)}</td>
                            <td style={{ whiteSpace: 'nowrap', color: 'var(--text-muted)' }}>{formatDateTime(item.updated_at)}</td>
                            <td>
                              <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <button
                                  className="btn btn-secondary btn-icon btn-sm"
                                  onClick={() => openEdit(item)}
                                  title="Edit Insight"
                                >
                                  <Edit2 size={15} color="var(--accent-secondary)" />
                                </button>
                                <button
                                  className="btn btn-secondary btn-icon btn-sm"
                                  onClick={() => handleDelete(item)}
                                  disabled={deletingId === item.id}
                                  title="Delete Insight"
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
                )}
              </>
            )}
          </div>
        </>
      ) : (
        <div className="mb-6">
          {activeFilter === 'FORECAST' && <ForecastPanel {...panelProps} />}
          {activeFilter === 'LOW_STOCK' && <LowStockPanel {...panelProps} />}
          {activeFilter === 'RECOMMENDATION' && <RecommendationPanel {...panelProps} />}
          {activeFilter === 'ANALYSIS' && <AnalysisPanel {...panelProps} />}
        </div>
      )}

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editing ? 'Edit AI Insight' : 'Create AI Insight'}
      >
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Title *</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Gamma demand is rising"
              value={formData.title}
              onChange={(e) => handleChange('title', e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Description *</label>
            <textarea
              className="form-textarea"
              rows={4}
              placeholder="Describe the insight and its business impact..."
              value={formData.description}
              onChange={(e) => handleChange('description', e.target.value)}
            />
          </div>

          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">Insight Type *</label>
              <select
                className="form-select"
                value={formData.insight_type}
                onChange={(e) => handleChange('insight_type', e.target.value)}
              >
                <option value="">Select type...</option>
                {INSIGHT_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Confidence Score</label>
              <input
                type="number"
                className="form-input"
                step="0.01"
                min="0"
                value={formData.confidence_score}
                onChange={(e) => handleChange('confidence_score', e.target.value)}
                placeholder="0.00"
              />
            </div>
          </div>

          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">Generated By</label>
              <input
                type="text"
                className="form-input"
                value={formData.generated_by}
                onChange={(e) => handleChange('generated_by', e.target.value)}
                placeholder="AI"
              />
            </div>

            <div className="form-group" style={{ justifyContent: 'flex-end' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => handleChange('is_active', e.target.checked)}
                />
                <span style={{ fontSize: '0.875rem', fontWeight: 600 }}>Active</span>
              </label>
            </div>
          </div>

          {formError && (
            <div
              style={{
                marginBottom: '1rem',
                padding: '0.75rem 1rem',
                borderRadius: 'var(--radius-md)',
                background: 'var(--status-danger-bg)',
                color: 'var(--status-danger)',
                fontSize: '0.875rem',
              }}
            >
              {formError}
            </div>
          )}

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Saving...' : editing ? 'Update Insight' : 'Create Insight'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};