import api from "@/lib/api";
import { AxiosError } from "axios";

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

  async login(credentials: LoginDto): Promise<AuthResponse> {
    try {
      const response = await api.post<AuthResponse>("/auth/login", credentials);

      this.setSession(response.data);
      return response.data;
    } catch (error) {
      if (error instanceof AxiosError) {
        const message =
          error.response?.data?.detail ||
          error.response?.data?.message ||
          "Login error";
        throw new Error(message);
      }
      throw new Error("Connection error");
    }
  }

  async register(userData: RegisterDto): Promise<AuthResponse> {
    try {
      const response = await api.post<AuthResponse>("/auth/register", userData);

      this.setSession(response.data);
      return response.data;
    } catch (error) {
      if (error instanceof AxiosError) {
        const message =
          error.response?.data?.detail ||
          error.response?.data?.message ||
          "Registration error";
        throw new Error(message);
      }
      throw new Error("Connection error");
    }
  }

  async getProfile(): Promise<AuthResponse["user"]> {
    const token = this.getToken();
    if (!token) {
      throw new Error("No active session");
    }

    try {
      const response = await api.get<AuthResponse["user"]>("/auth/me");

      this.setUser(response.data);
      return response.data;
    } catch (error) {
      this.logout();
      throw error;
    }
  }

  private setSession(data: AuthResponse): void {
    if (typeof window === "undefined") return;

    localStorage.setItem(this.TOKEN_KEY, data.access_token);
    localStorage.setItem(this.USER_KEY, JSON.stringify(data.user));
  }

  private setUser(user: AuthResponse["user"]): void {
    if (typeof window === "undefined") return;
    localStorage.setItem(this.USER_KEY, JSON.stringify(user));
  }

  getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(this.TOKEN_KEY);
  }

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

  logout(): void {
    if (typeof window === "undefined") return;

    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }
}

export const authService = new AuthService();
