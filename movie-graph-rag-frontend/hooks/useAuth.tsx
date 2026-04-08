"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { authService, type AuthResponse } from "@/services/auth.service";
import { toast } from "sonner";

interface AuthContextType {
  user: AuthResponse["user"] | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // Read localStorage synchronously so the initial state is correct on first render.
  // If there is no token we know immediately that the user is not authenticated
  // (isLoading stays false). If there is a token we still need to verify it
  // with the backend, so isLoading starts true.
  const [user, setUser] = useState<AuthResponse["user"] | null>(() => authService.getUser());
  const [isLoading, setIsLoading] = useState<boolean>(() => authService.isAuthenticated());
  const router = useRouter();

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
    toast.info("Sesión cerrada");
    router.push("/login");
  }, [router]);

  useEffect(() => {
    // Verificar si hay un usuario en el almacenamiento local
    const initAuth = async () => {
      const storedUser = authService.getUser();
      const token = authService.getToken();

      if (storedUser && token) {
        setUser(storedUser);
        
        // Verificar token con el backend
        try {
          const profile = await authService.getProfile();
          setUser(profile);
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        } catch (error) {
          // Si el token es inválido, cerrar sesión
          logout();
        }
      }
      
      setIsLoading(false);
    };

    initAuth();
  }, [logout]);

  const login = async (email: string, password: string) => {
    try {
      const response = await authService.login({ email, password });
      setUser(response.user);
      toast.success("Inicio de sesión exitoso");
      router.push("/");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Error al iniciar sesión";
      toast.error(message);
      throw error;
    }
  };

  const register = async (name: string, email: string, password: string) => {
    try {
      const response = await authService.register({ name, email, password });
      setUser(response.user);
      toast.success("Registro exitoso");
      router.push("/");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Error al registrarse";
      toast.error(message);
      throw error;
    }
  };

  const refreshProfile = async () => {
    try {
      const profile = await authService.getProfile();
      setUser(profile);
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    } catch (error) {
      logout();
    }
  };

  const value = {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    refreshProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth debe usarse dentro de un AuthProvider");
  }
  return context;
}