import type { Metadata } from "next";
import { Toaster } from "@/components/ui/sonner";
import { Providers } from "@/components/shared/Providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "CineGraph — Recomendaciones cinematográficas inteligentes",
  description: "Sistema de recomendación de películas potenciado por grafos de conocimiento y IA generativa.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body className="antialiased bg-bg text-text">
        <Providers>
          {children}
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}
