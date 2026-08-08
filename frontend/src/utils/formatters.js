export const formatCurrency = (amount, currency = 'Rs.') => {
  if (amount === null || amount === undefined) return `${currency} 0.00`;
  const num = parseFloat(amount);
  if (Number.isNaN(num)) return `${currency} 0.00`;
  return `${currency} ${num.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
};

export const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
};

export const formatDateTime = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

export const getStockBadgeClass = (status) => {
  switch (status) {
    case 'In Stock':
      return 'badge-success';
    case 'Low Stock':
      return 'badge-warning';
    case 'Out of Stock':
      return 'badge-danger';
    default:
      return 'badge-info';
  }
};
