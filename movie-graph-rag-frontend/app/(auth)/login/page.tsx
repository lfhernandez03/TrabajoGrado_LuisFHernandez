"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { Mail, Lock, Loader2, Sparkles } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";

export default function LoginPage() {
  const { login } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({ email: "", password: "" });

  const handleEmailChange = useCallback((email: string) => {
    setFormData((f) => ({ ...f, email }));
  }, []);

  const handlePasswordChange = useCallback((password: string) => {
    setFormData((f) => ({ ...f, password }));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await login(formData.email, formData.password);
    } catch (error) {
      console.error("Login error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-4">
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-accent/5 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-sm animate-fade-in">
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-1">
            <span className="font-display text-4xl tracking-widest text-text">CINE</span>
            <span className="font-display text-4xl tracking-widest text-accent">RAPH</span>
          </Link>
          <p className="text-xs text-muted mt-2">Intelligent movie recommendations</p>
        </div>

        <div className="bg-surface border border-border2 rounded-2xl p-8">
          <div className="mb-6">
            <h1 className="font-display text-2xl text-text">Sign in</h1>
            <p className="text-sm text-muted mt-1">Enter your credentials to continue</p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="email" className="text-xs font-medium text-muted uppercase tracking-wider">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
                <Input id="email" type="email" variant="default" placeholder="you@email.com" className="pl-9"
                  value={formData.email} onChange={(e) => handleEmailChange(e.target.value)}
                  required disabled={isLoading} />
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="password" className="text-xs font-medium text-muted uppercase tracking-wider">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
                <Input id="password" type="password" variant="default" placeholder="••••••••" className="pl-9"
                  value={formData.password} onChange={(e) => handlePasswordChange(e.target.value)}
                  required disabled={isLoading} />
              </div>
            </div>

            <Button type="submit" variant="primary" disabled={isLoading} className="w-full mt-2">
              {isLoading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Signing in…</>
                : <><Sparkles className="w-4 h-4 mr-2" />Sign in</>}
            </Button>
          </form>

          <p className="text-sm text-muted text-center mt-6">
            Don't have an account?{" "}
            <Link href="/register" className="text-accent hover:text-accent/80 font-medium transition-colors">
              Sign up here
            </Link>
          </p>
        </div>

        <p className="text-center text-[11px] text-muted/50 mt-6">
          Trabajo de grado · Universidad del Valle · 2025
        </p>
      </div>
    </div>
  );
}
