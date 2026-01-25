import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3001/";

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  name: string;
  email: string;
  password: string;
}

export interface AuthResponse {
  user: {
    id: string;
    name: string;
    email: string;
  };
  access_token: string;
}

class AuthService {
  /**
   * Iniciar sesión
   */
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await axios.post<AuthResponse>(
      `${API_URL}/auth/login`,
      credentials
    );
    
    if (response.data.access_token) {
      this.setToken(response.data.access_token);
      this.setUser(response.data.user);
    }
    
    return response.data;
  }

  /**
   * Registrar nuevo usuario
   */
  async register(data: RegisterData): Promise<AuthResponse> {
    const response = await axios.post<AuthResponse>(
      `${API_URL}/auth/register`,
      data
    );
    
    if (response.data.access_token) {
      this.setToken(response.data.access_token);
      this.setUser(response.data.user);
    }
    
    return response.data;
  }

  /**
   * Cerrar sesión
   */
  logout(): void {
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
    }
  }

  /**
   * Obtener el token almacenado
   */
  getToken(): string | null {
    if (typeof window !== "undefined") {
      return localStorage.getItem("token");
    }
    return null;
  }

  /**
   * Guardar el token
   */
  private setToken(token: string): void {
    if (typeof window !== "undefined") {
      localStorage.setItem("token", token);
    }
  }

  /**
   * Obtener el usuario almacenado
   */
  getUser(): AuthResponse["user"] | null {
    if (typeof window !== "undefined") {
      const userStr = localStorage.getItem("user");
      return userStr ? JSON.parse(userStr) : null;
    }
    return null;
  }

  /**
   * Guardar el usuario
   */
  private setUser(user: AuthResponse["user"]): void {
    if (typeof window !== "undefined") {
      localStorage.setItem("user", JSON.stringify(user));
    }
  }

  /**
   * Verificar si el usuario está autenticado
   */
  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  /**
   * Obtener perfil del usuario actual
   */
  async getProfile(): Promise<AuthResponse["user"]> {
    const token = this.getToken();
    const response = await axios.get<AuthResponse["user"]>(
      `${API_URL}/auth/profile`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );
    
    this.setUser(response.data);
    return response.data;
  }
}

export const authService = new AuthService();
