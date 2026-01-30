import api from "@/lib/api";
import { AxiosError } from "axios";
import { toast } from "sonner";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3001";

export interface AuthResponse {
  access_token: string;
  user: {
    id: string;
    name: string;
    email: string;
  };
}

export interface LoginDto {
  email: string;
  password: string;
}

export interface RegisterDto {
  name: string;
  email: string;
  password: string;
}

class AuthService {
  private readonly TOKEN_KEY = "auth_token";
  private readonly USER_KEY = "auth_user";

  /**
   * Inicia sesión
   */
  async login(credentials: LoginDto): Promise<AuthResponse> {
    try {
      const response = await api.post<AuthResponse>("/auth/login", credentials);

      this.setSession(response.data);
      return response.data;
    } catch (error) {
      if (error instanceof AxiosError) {
        const message =
          error.response?.data?.message || "Error al iniciar sesión";
        throw new Error(message);
      }
      throw new Error("Error de conexión con el servidor");
    }
  }

  /**
   * Registra un nuevo usuario
   */
  async register(userData: RegisterDto): Promise<AuthResponse> {
    try {
      const response = await api.post<AuthResponse>("/auth/register", userData);

      this.setSession(response.data);
      return response.data;
    } catch (error) {
      if (error instanceof AxiosError) {
        const message = error.response?.data?.message || "Error al registrarse";
        throw new Error(message);
      }
      throw new Error("Error de conexión con el servidor");
    }
  }

  /**
   * Obtiene el perfil del usuario actual
   */
  async getProfile(): Promise<AuthResponse["user"]> {
    const token = this.getToken();
    if (!token) {
      throw new Error("No hay sesión activa");
    }

    try {
      const response = await api.get<AuthResponse["user"]>("/auth/profile");

      this.setUser(response.data);
      return response.data;
    } catch (error) {
      this.logout();
      throw error;
    }
  }

  /**
   * Guarda la sesión en localStorage
   */
  private setSession(data: AuthResponse): void {
    if (typeof window === "undefined") return;

    localStorage.setItem(this.TOKEN_KEY, data.access_token);
    localStorage.setItem(this.USER_KEY, JSON.stringify(data.user));
  }

  /**
   * Guarda el usuario en localStorage
   */
  private setUser(user: AuthResponse["user"]): void {
    if (typeof window === "undefined") return;
    localStorage.setItem(this.USER_KEY, JSON.stringify(user));
  }

  /**
   * Obtiene el token de autenticación
   */
  getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(this.TOKEN_KEY);
  }

  /**
   * Obtiene el usuario almacenado
   */
  getUser(): AuthResponse["user"] | null {
    if (typeof window === "undefined") return null;

    const userStr = localStorage.getItem(this.USER_KEY);
    if (!userStr) return null;

    try {
      return JSON.parse(userStr);
    } catch {
      return null;
    }
  }

  /**
   * Cierra la sesión
   */
  logout(): void {
    if (typeof window === "undefined") return;

    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
  }

  /**
   * Verifica si hay una sesión activa
   */
  isAuthenticated(): boolean {
    return !!this.getToken();
  }
}

export const authService = new AuthService();
