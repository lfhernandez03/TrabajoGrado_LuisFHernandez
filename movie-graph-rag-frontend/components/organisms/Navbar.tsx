'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { MessageSquare, Compass, Home, Network, Heart, LogOut, User } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuth } from '@/hooks/useAuth'
import { cn } from '@/lib/utils'

const NAV_LINKS = [
  { href: '/', label: 'Inicio', icon: Home },
  { href: '/search', label: 'Explorar', icon: Compass },
  { href: '/chat', label: 'Chat IA', icon: MessageSquare },
  { href: '/favorites', label: 'Favoritos', icon: Heart },
]

export function Navbar() {
  const { user, isAuthenticated, logout } = useAuth()
  const pathname = usePathname()

  const getInitials = (name: string) =>
    name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)

  return (
    <nav className="sticky top-0 z-50 bg-surface/80 backdrop-blur-md border-b border-border">
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex h-16 items-center justify-between">

          {/* Logo */}
          <Link href="/" className="flex items-center gap-1 shrink-0">
            <span className="font-display text-2xl tracking-widest text-text">CINE</span>
            <span className="font-display text-2xl tracking-widest text-accent">RAPH</span>
          </Link>

          {/* Nav links — desktop */}
          <div className="hidden md:flex items-center gap-1">
            {NAV_LINKS.map(({ href, label, icon: Icon }) => {
              const active = pathname === href
              return (
                <Link
                  key={href}
                  href={href}
                  className={cn(
                    'flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium transition-all duration-200',
                    active
                      ? 'bg-surface2 text-accent'
                      : 'text-muted hover:text-text hover:bg-surface2/60'
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </Link>
              )
            })}
          </div>

          {/* Auth */}
          <div className="flex items-center gap-2">
            {isAuthenticated && user ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    aria-label="Menú de usuario"
                    className="rounded-full focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                  >
                    <Avatar className="h-9 w-9 border-2 border-border2 hover:border-accent transition-colors">
                      <AvatarFallback className="bg-surface2 text-accent text-xs font-semibold">
                        {getInitials(user.name)}
                      </AvatarFallback>
                    </Avatar>
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent
                  align="end"
                  className="w-52 bg-surface border-border2"
                >
                  <DropdownMenuLabel className="text-muted text-xs font-normal">
                    <p className="text-text font-semibold text-sm">{user.name}</p>
                    <p className="text-muted text-xs">{user.email}</p>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator className="bg-border" />
                  <DropdownMenuItem asChild>
                    <Link
                      href="/profile"
                      className="flex items-center gap-2 text-text hover:text-accent cursor-pointer"
                    >
                      <User className="w-4 h-4" />
                      Mi perfil
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={logout}
                    className="flex items-center gap-2 text-accent2 hover:text-accent2 cursor-pointer focus:text-accent2"
                  >
                    <LogOut className="w-4 h-4" />
                    Cerrar sesión
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" asChild>
                  <Link href="/login">Iniciar sesión</Link>
                </Button>
                <Button variant="primary" size="sm" asChild>
                  <Link href="/register">Registrarse</Link>
                </Button>
              </div>
            )}
          </div>

        </div>
      </div>
    </nav>
  )
}
