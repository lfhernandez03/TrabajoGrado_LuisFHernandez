import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { toast } from 'sonner';

const API_HOST = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_PREFIX = process.env.NEXT_PUBLIC_API_PREFIX || '/api/v1';

const normalizedHost = API_HOST.replace(/\/+$/, '');
const normalizedPrefix = API_PREFIX
  ? API_PREFIX.startsWith('/')
    ? API_PREFIX
    : `/${API_PREFIX}`
  : '';

const API_URL = normalizedPrefix
  ? normalizedHost.endsWith(normalizedPrefix)
    ? normalizedHost
    : `${normalizedHost}${normalizedPrefix}`
  : normalizedHost;

const api = axios.create({
  baseURL: API_URL,
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('auth_token');
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error: AxiosError) => {
    if (error.response) {
      const status = error.response.status;
      const responseData = error.response.data;
      
      let message = 'Unknown error';
      if (typeof responseData === 'object' && responseData !== null) {
        const data = responseData as Record<string, any>;
        message = data.detail || data.message || data.msg || error.message || message;
      } else if (typeof responseData === 'string') {
        message = responseData;
      } else {
        message = error.message || message;
      }

      switch (status) {
        case 401:
          if (typeof window !== 'undefined') {
            localStorage.removeItem('auth_token');
            localStorage.removeItem('auth_user');
            toast.error('Session expired. Please log in again.');
            window.location.href = '/login';
          }
          break;
        case 403:
          toast.error('You do not have permission to perform this action');
          break;
        case 404:
          toast.error('Resource not found');
          break;
        case 500:
          toast.error('Server error. Please try again later.');
          break;
        default:
          toast.error(message);
      }
    } else if (error.request) {
      toast.error('Could not connect to the server');
    } else {
      toast.error('Request error');
    }

    return Promise.reject(error);
  }
);

export default api;