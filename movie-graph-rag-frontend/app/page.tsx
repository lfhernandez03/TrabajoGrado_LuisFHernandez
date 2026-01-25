import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Navbar } from "@/components/shared/Navbar";
import { Film, Search, Sparkles } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex flex-col items-center gap-4 py-8">
          <div className="flex items-center gap-2">
            <Film className="h-8 w-8 text-primary" />
            <h1 className="text-4xl font-bold">Movie Graph RAG</h1>
          </div>
          <p className="text-center text-muted-foreground max-w-2xl">
            Sistema de recomendación de películas potenciado por grafos de conocimiento y IA
          </p>
        </div>

        {/* Search Section */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="h-5 w-5" />
              Buscar Películas
            </CardTitle>
            <CardDescription>
              Ingresa tu consulta para obtener recomendaciones personalizadas
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Input 
                placeholder="Ej: Películas de ciencia ficción con viajes en el tiempo..." 
                className="flex-1"
              />
              <Button>
                <Sparkles className="mr-2 h-4 w-4" />
                Buscar
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Example Movies */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex justify-between items-start">
                <CardTitle>Inception</CardTitle>
                <Badge>Sci-Fi</Badge>
              </div>
              <CardDescription>Christopher Nolan • 2010</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Un ladrón que roba secretos corporativos mediante tecnología de sueños compartidos.
              </p>
              <div className="flex gap-2 mt-4">
                <Button variant="outline" size="sm">Ver detalles</Button>
                <Button size="sm">Recomendar similares</Button>
              </div>
            </CardContent>
          </Card>

          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex justify-between items-start">
                <CardTitle>The Matrix</CardTitle>
                <Badge variant="secondary">Acción</Badge>
              </div>
              <CardDescription>Wachowski • 1999</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Un hacker descubre que la realidad que conoce es una simulación controlada por máquinas.
              </p>
              <div className="flex gap-2 mt-4">
                <Button variant="outline" size="sm">Ver detalles</Button>
                <Button size="sm">Recomendar similares</Button>
              </div>
            </CardContent>
          </Card>

          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex justify-between items-start">
                <CardTitle>Interstellar</CardTitle>
                <Badge>Aventura</Badge>
              </div>
              <CardDescription>Christopher Nolan • 2014</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Un equipo de astronautas viaja a través de un agujero de gusano en busca de un nuevo hogar.
              </p>
              <div className="flex gap-2 mt-4">
                <Button variant="outline" size="sm">Ver detalles</Button>
                <Button size="sm">Recomendar similares</Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Features */}
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">🎬 Base de Conocimiento</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Grafos semánticos con ontologías enriquecidas
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">🤖 IA Generativa</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Recomendaciones contextuales impulsadas por LLMs
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">🔍 RAG Avanzado</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Recuperación aumentada sobre grafos de conocimiento
              </p>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
