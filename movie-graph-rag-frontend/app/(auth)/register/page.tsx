"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { Mail, Lock, User, Loader2, Sparkles } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";

function validatePassword(pw: string) {
  if (pw.length < 8) return "Minimum 8 characters";
  if (!/[A-Z]/.test(pw)) return "Must have at least one uppercase letter";
  if (!/[a-z]/.test(pw)) return "Must have at least one lowercase letter";
  if (!/[0-9]/.test(pw)) return "Must have at least one number";
  return "";
}

export default function RegisterPage() {
  const { register } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({ name: "", email: "", password: "", confirmPassword: "" });
  const [errors, setErrors] = useState({ password: "", confirmPassword: "" });

  const handleNameChange = useCallback((name: string) => {
    setFormData((f) => ({ ...f, name }));
  }, []);

  const handleEmailChange = useCallback((email: string) => {
    setFormData((f) => ({ ...f, email }));
  }, []);

  const handlePasswordChange = useCallback((password: string) => {
    setFormData((f) => ({ ...f, password }));
    setErrors((e) => ({ ...e, password: validatePassword(password) }));
  }, []);

  const handleConfirmChange = useCallback((confirmPassword: string) => {
    setFormData((f) => ({
      ...f,
      confirmPassword,
      // Validate against the formData that will be updated
    }));
    // Use the new confirmPassword value for comparison with current formData.password
    setErrors((e) => ({ 
      ...e, 
      confirmPassword: confirmPassword !== formData.password ? "Passwords don't match" : "" 
    }));
  }, [formData.password]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (errors.password || errors.confirmPassword) {
      toast.error("Fix form errors");
      return;
    }
    setIsLoading(true);
    try {
      await register(formData.name, formData.email, formData.password);
    } catch (error) {
      console.error("Registration error:", error);
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-4">
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-150 h-100 bg-teal/5 rounded-full blur-3xl" />
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
            <h1 className="font-display text-2xl text-text">Create account</h1>
            <p className="text-sm text-muted mt-1">Complete the form to get started</p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="name" className="text-xs font-medium text-muted uppercase tracking-wider">Full name</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
                <Input id="name" type="text" variant="default" placeholder="John Doe" className="pl-9"
                  value={formData.name} onChange={(e) => handleNameChange(e.target.value)}
                  required disabled={isLoading} />
              </div>
            </div>

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
                <Input id="password" type="password" variant="default" placeholder="••••••••" 
                  className={cn("pl-9", errors.password && "border-red-600/60")}
                  value={formData.password} onChange={(e) => handlePasswordChange(e.target.value)}
                  required disabled={isLoading} />
              </div>
              {errors.password && <p className="text-xs text-red-400">{errors.password}</p>}
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="confirmPassword" className="text-xs font-medium text-muted uppercase tracking-wider">Confirm password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
                <Input id="confirmPassword" type="password" variant="default" placeholder="••••••••"
                  className={cn("pl-9", errors.confirmPassword && "border-red-600/60")}
                  value={formData.confirmPassword} onChange={(e) => handleConfirmChange(e.target.value)}
                  required disabled={isLoading} />
              </div>
              {errors.confirmPassword && <p className="text-xs text-red-400">{errors.confirmPassword}</p>}
            </div>

            <Button type="submit" variant="primary" disabled={isLoading} className="w-full mt-2">
              {isLoading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Creating account…</>
                : <><Sparkles className="w-4 h-4 mr-2" />Create account</>}
            </Button>
          </form>

          <p className="text-sm text-muted text-center mt-6">
            Already have an account?{" "}
            <Link href="/login" className="text-accent hover:text-accent/80 font-medium transition-colors">
              Sign in here
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
