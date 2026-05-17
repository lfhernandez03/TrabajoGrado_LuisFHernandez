'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useState, useEffect, useTransition } from 'react'
import { MessageSquare, Compass, Home, Heart, LogOut, User, Menu, X } from 'lucide-react'
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
  { href: '/', label: 'Home', icon: Home },
  { href: '/search', label: 'Explore', icon: Compass },
  { href: '/chat', label: 'AI Chat', icon: MessageSquare },
  { href: '/favorites', label: 'Favorites', icon: Heart },
]

export function Navbar() {
  const { user, isAuthenticated, logout } = useAuth()
  const pathname = usePathname()
  const router = useRouter()
  const [isPending, startTransition] = useTransition()
  const [mobileOpen, setMobileOpen] = useState(false)

  // Navigate with idempotency: skip if already on the page or a transition is in flight.
  // Also closes the mobile drawer on navigation.
  const navigate = (href: string) => {
    setMobileOpen(false)
    if (pathname === href || isPending) return
    startTransition(() => { router.push(href) })
  }

  // Prevent body scroll when mobile drawer is open
  useEffect(() => {
    document.body.style.overflow = mobileOpen ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [mobileOpen])

  const getInitials = (name: string) =>
    name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)

  const navLinkClass = (active: boolean) => cn(
    'flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium transition-all duration-200 cursor-pointer',
    active ? 'bg-surface2 text-accent' : 'text-muted hover:text-text hover:bg-surface2/60',
    isPending && 'opacity-60 pointer-events-none'
  )

  const mobileNavLinkClass = (active: boolean) => cn(
    'flex items-center justify-center gap-3 px-4 py-3 rounded-md text-sm font-medium transition-all duration-200 cursor-pointer w-full',
    active ? 'bg-surface2 text-accent' : 'text-muted hover:text-text hover:bg-surface2/60',
    isPending && 'opacity-60 pointer-events-none'
  )

  return (
    <>
      <nav className="sticky top-0 z-50 bg-surface/80 backdrop-blur-md border-b border-border">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex h-16 items-center justify-between">

            {/* Logo */}
            <button onClick={() => navigate('/')} className="flex items-center gap-1 shrink-0">
              <span className="font-display text-2xl tracking-widest text-text">MOV</span>
              <span className="font-display text-2xl tracking-widest text-accent">IQ</span>
            </button>

            {/* Nav links — desktop */}
            <div className="hidden md:flex items-center gap-1">
              {NAV_LINKS.map(({ href, label, icon: Icon }) => (
                <button
                  key={href}
                  onClick={() => navigate(href)}
                  className={navLinkClass(pathname === href)}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </button>
              ))}
            </div>

            {/* Right side */}
            <div className="flex items-center gap-2">
              {/* Auth — desktop only */}
              {isAuthenticated && user ? (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button
                      aria-label="User menu"
                      className="hidden md:block rounded-full focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                    >
                      <Avatar className="h-9 w-9 border-2 border-border2 hover:border-accent transition-colors">
                        <AvatarFallback className="bg-surface2 text-accent text-xs font-semibold">
                          {getInitials(user.name)}
                        </AvatarFallback>
                      </Avatar>
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56 bg-surface border-border2 shadow-xl p-1">
                    {/* User header */}
                    <div className="flex items-center gap-3 px-2 py-2.5">
                      <Avatar className="h-8 w-8 shrink-0 border border-border2">
                        <AvatarFallback className="bg-surface2 text-accent text-xs font-semibold">
                          {getInitials(user.name)}
                        </AvatarFallback>
                      </Avatar>
                      <div className="min-w-0">
                        <p className="text-text font-semibold text-sm leading-tight truncate">{user.name}</p>
                        <p className="text-muted text-xs truncate">{user.email}</p>
                      </div>
                    </div>
                    <DropdownMenuSeparator className="bg-border my-1" />
                    <DropdownMenuItem
                      onClick={() => navigate('/profile')}
                      className="flex items-center gap-2 text-sm text-muted hover:text-text cursor-pointer rounded-md px-2 py-2 focus:bg-surface2 focus:text-text"
                    >
                      <User className="w-4 h-4 shrink-0" />
                      My profile
                    </DropdownMenuItem>
                    <DropdownMenuSeparator className="bg-border my-1" />
                    <DropdownMenuItem
                      onClick={logout}
                      className="flex items-center gap-2 text-sm text-red-400 hover:text-red-300 cursor-pointer rounded-md px-2 py-2 focus:bg-red-500/10 focus:text-red-300"
                    >
                      <LogOut className="w-4 h-4 shrink-0" />
                      Sign out
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              ) : (
                <div className="hidden md:flex items-center gap-2">
                  <Button variant="ghost" size="sm" asChild>
                    <Link href="/login">Sign in</Link>
                  </Button>
                  <Button variant="primary" size="sm" asChild>
                    <Link href="/register">Sign up</Link>
                  </Button>
                </div>
              )}

              {/* Hamburger — mobile only */}
              <button
                onClick={() => setMobileOpen((prev) => !prev)}
                aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
                className="md:hidden p-2 rounded-md text-muted hover:text-text hover:bg-surface2/60 transition-colors"
              >
                {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </button>
            </div>

          </div>
        </div>
      </nav>

      {/* Mobile drawer overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Mobile drawer */}
      <div
        className={cn(
          'fixed top-16 left-0 right-0 z-40 bg-surface border-b border-border md:hidden transition-all duration-200 ease-in-out',
          mobileOpen ? 'translate-y-0 opacity-100 pointer-events-auto' : '-translate-y-4 opacity-0 pointer-events-none'
        )}
      >
        <div className="max-w-7xl mx-auto px-6 py-4 flex flex-col gap-1">
          {NAV_LINKS.map(({ href, label, icon: Icon }) => (
            <button
              key={href}
              onClick={() => navigate(href)}
              className={mobileNavLinkClass(pathname === href)}
            >
              <Icon className="w-5 h-5" />
              {label}
            </button>
          ))}

          {/* Auth section in mobile menu */}
          <div className="mt-2 pt-3 border-t border-border">
            {isAuthenticated && user ? (
              <>
                <div className="flex flex-col items-center gap-1 py-2 mb-1">
                  <Avatar className="h-10 w-10 border-2 border-border2">
                    <AvatarFallback className="bg-surface2 text-accent text-sm font-semibold">
                      {getInitials(user.name)}
                    </AvatarFallback>
                  </Avatar>
                  <p className="text-sm font-semibold text-text">{user.name}</p>
                  <p className="text-xs text-muted">{user.email}</p>
                </div>
                <button
                  onClick={() => navigate('/profile')}
                  className="flex items-center justify-center gap-3 px-4 py-3 rounded-md text-sm font-medium text-muted hover:text-text hover:bg-surface2/60 transition-all duration-200 w-full"
                >
                  <User className="w-5 h-5" />
                  My profile
                </button>
                <button
                  onClick={() => { logout(); setMobileOpen(false) }}
                  className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-md text-sm font-medium text-accent2 hover:bg-surface2/60 transition-all duration-200"
                >
                  <LogOut className="w-5 h-5" />
                  Sign out
                </button>
              </>
            ) : (
              <div className="flex flex-col gap-2 px-2">
                <Button variant="ghost" size="sm" asChild className="justify-center">
                  <Link href="/login">Sign in</Link>
                </Button>
                <Button variant="primary" size="sm" asChild>
                  <Link href="/register">Sign up</Link>
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
