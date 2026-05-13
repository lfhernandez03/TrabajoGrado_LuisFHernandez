import type { Metadata } from "next";
import { Toaster } from "@/components/ui/sonner";
import { Providers } from "@/components/shared/Providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "Moviq — Intelligent Movie Recommendations",
  description: "Movie recommendation system powered by knowledge graphs and generative AI.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased bg-bg text-text">
        <Providers>
          {children}
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}
