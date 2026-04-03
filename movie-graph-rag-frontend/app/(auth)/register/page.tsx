"use client";

import { useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { Mail, Lock, User, Loader2, Sparkles } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";

function validatePassword(pw: string) {
  if (pw.length < 8) return "Mínimo 8 caracteres";
  if (!/[A-Z]/.test(pw)) return "Debe tener al menos una mayúscula";
  if (!/[a-z]/.test(pw)) return "Debe tener al menos una minúscula";
  if (!/[0-9]/.test(pw)) return "Debe tener al menos un número";
  return "";
}

export default function RegisterPage() {
  const { register } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({ name: "", email: "", password: "", confirmPassword: "" });
  const [errors, setErrors] = useState({ password: "", confirmPassword: "" });

  const handlePasswordChange = (pw: string) => {
    setFormData((f) => ({ ...f, password: pw }));
    setErrors((e) => ({ ...e, password: validatePassword(pw) }));
  };

  const handleConfirmChange = (cpw: string) => {
    setFormData((f) => ({ ...f, confirmPassword: cpw }));
    setErrors((e) => ({ ...e, confirmPassword: cpw !== formData.password ? "Las contraseñas no coinciden" : "" }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (errors.password || errors.confirmPassword) {
      toast.error("Corrige los errores del formulario");
      return;
    }
    setIsLoading(true);
    try {
      await register(formData.name, formData.email, formData.password);
    } catch (error) {
      console.error("Error en registro:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const Field = ({ id, label, type = "text", icon: Icon, placeholder, value, onChange, error, disabled }: {
    id: string; label: string; type?: string; icon: React.ComponentType<{ className?: string }>;
    placeholder: string; value: string; onChange: (v: string) => void; error?: string; disabled?: boolean;
  }) => (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-xs font-medium text-muted uppercase tracking-wider">{label}</label>
      <div className="relative">
        <Icon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
        <Input id={id} type={type} variant="default" placeholder={placeholder}
          className={cn("pl-9", error && "border-red-600/60")}
          value={value} onChange={(e) => onChange(e.target.value)} required disabled={disabled} />
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-4">
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-teal/5 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-sm animate-fade-in">
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-1">
            <span className="font-display text-4xl tracking-widest text-text">CINE</span>
            <span className="font-display text-4xl tracking-widest text-accent">RAPH</span>
          </Link>
          <p className="text-xs text-muted mt-2">Recomendaciones cinematográficas inteligentes</p>
        </div>

        <div className="bg-surface border border-border2 rounded-2xl p-8">
          <div className="mb-6">
            <h1 className="font-display text-2xl text-text">Crear cuenta</h1>
            <p className="text-sm text-muted mt-1">Completa el formulario para empezar</p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Field id="name" label="Nombre completo" icon={User} placeholder="Juan Pérez"
              value={formData.name} onChange={(v) => setFormData((f) => ({ ...f, name: v }))} disabled={isLoading} />

            <Field id="email" label="Email" type="email" icon={Mail} placeholder="tu@email.com"
              value={formData.email} onChange={(v) => setFormData((f) => ({ ...f, email: v }))} disabled={isLoading} />

            <Field id="password" label="Contraseña" type="password" icon={Lock} placeholder="••••••••"
              value={formData.password} onChange={handlePasswordChange} error={errors.password} disabled={isLoading} />

            <Field id="confirmPassword" label="Confirmar contraseña" type="password" icon={Lock} placeholder="••••••••"
              value={formData.confirmPassword} onChange={handleConfirmChange}
              error={errors.confirmPassword} disabled={isLoading} />

            <Button type="submit" variant="primary" disabled={isLoading} className="w-full mt-2">
              {isLoading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Creando cuenta…</>
                : <><Sparkles className="w-4 h-4 mr-2" />Crear cuenta</>}
            </Button>
          </form>

          <p className="text-sm text-muted text-center mt-6">
            ¿Ya tienes cuenta?{" "}
            <Link href="/login" className="text-accent hover:text-accent/80 font-medium transition-colors">
              Inicia sesión aquí
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
