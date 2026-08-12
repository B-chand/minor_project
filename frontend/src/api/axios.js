import axios from 'axios';

const rawBaseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const normalizedBaseURL = rawBaseURL.replace(/\/+$/, '');
const baseURL = normalizedBaseURL.endsWith('/api') ? normalizedBaseURL : `${normalizedBaseURL}/api`;

const api = axios.create({
  baseURL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to attach the JWT access token.
// Login/refresh never get the Authorization header: authentication is
// business_code + username + password.
api.interceptors.request.use(
  (config) => {
    const isTokenEndpoint =
      config.url === '/token/' || config.url === '/token/refresh/';

    const token = localStorage.getItem('access_token');
    if (token && !isTokenEndpoint) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for automatic token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    const isTokenEndpoint =
      originalRequest?.url === '/token/' || originalRequest?.url === '/token/refresh/';

    if (error.response?.status === 401 && !originalRequest._retry && !isTokenEndpoint) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');

      if (refreshToken) {
        try {
          const res = await axios.post(`${baseURL}/token/refresh/`, {
            refresh: refreshToken,
          });

          if (res.status === 200) {
            localStorage.setItem('access_token', res.data.access);
            api.defaults.headers.common.Authorization = `Bearer ${res.data.access}`;
            originalRequest.headers = originalRequest.headers || {};
            originalRequest.headers.Authorization = `Bearer ${res.data.access}`;
            return api(originalRequest);
          }
        } catch (refreshError) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.assign('/login');
          return Promise.reject(refreshError);
        }
      } else {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.assign('/login');
      }
    }

    return Promise.reject(error);
  }
);

export default api;
