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

// Crear instancia de axios
const api = axios.create({
  baseURL: API_URL,
  timeout: 120000, // 2 minutos
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor de peticiones: Agregar token automáticamente
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

// Interceptor de respuestas: Manejar errores globalmente
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error: AxiosError) => {
    if (error.response) {
      const status = error.response.status;
      const responseData = error.response.data;
      
      // Validar y extraer mensaje de error de forma segura
      let message = 'Error desconocido';
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
          // Token inválido o expirado
          if (typeof window !== 'undefined') {
            localStorage.removeItem('auth_token');
            localStorage.removeItem('auth_user');
            toast.error('Sesión expirada. Por favor, inicia sesión nuevamente.');
            window.location.href = '/login';
          }
          break;
        
        case 403:
          // Sin permisos
          toast.error('No tienes permisos para realizar esta acción');
          break;
        
        case 404:
          // No encontrado
          toast.error('Recurso no encontrado');
          break;
        
        case 500:
          // Error del servidor
          toast.error('Error del servidor. Por favor, intenta más tarde.');
          break;
        
        default:
          // Otros errores
          toast.error(message);
      }
    } else if (error.request) {
      // La petición se hizo pero no hubo respuesta
      toast.error('No se pudo conectar con el servidor');
    } else {
      // Error al configurar la petición
      toast.error('Error en la petición');
    }

    return Promise.reject(error);
  }
);

export default api;