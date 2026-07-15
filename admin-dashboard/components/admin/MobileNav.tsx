'use client'

import { useEffect, useState } from 'react'
import {
  LayoutDashboard,
  Package,
  ShoppingCart,
  Users,
  Menu,
  Tag,
  CreditCard,
  Settings,
  LogOut,
  X,
} from 'lucide-react'
import type { TabId } from './Sidebar'
import { cn } from '@/lib/utils'

const primaryItems: { id: TabId; label: string; icon: React.ElementType }[] = [
  { id: 'overview', label: 'Home', icon: LayoutDashboard },
  { id: 'products', label: 'Products', icon: Package },
  { id: 'orders', label: 'Orders', icon: ShoppingCart },
  { id: 'users', label: 'Users', icon: Users },
]

const overflowItems: { id: TabId; label: string; icon: React.ElementType }[] = [
  { id: 'categories', label: 'Categories', icon: Tag },
  { id: 'payments', label: 'Payments', icon: CreditCard },
  { id: 'settings', label: 'Settings', icon: Settings },
]

interface MobileNavProps {
  active: TabId
  onChange: (id: TabId) => void
  onLogout: () => void
}

export default function MobileNav({ active, onChange, onLogout }: MobileNavProps) {
  const [moreOpen, setMoreOpen] = useState(false)
  const isOverflowActive = overflowItems.some((item) => item.id === active)

  useEffect(() => {
    if (!moreOpen) return
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
    }
  }, [moreOpen])

  return (
    <>
      {/* Bottom tab bar — mobile & tablet only */}
      <nav
        className="lg:hidden fixed bottom-0 inset-x-0 z-30 bg-background/90 backdrop-blur-xl border-t border-border pb-safe"
        aria-label="Primary"
      >
        <div className="grid grid-cols-5 h-16">
          {primaryItems.map((item) => {
            const Icon = item.icon
            const isActive = active === item.id
            return (
              <button
                key={item.id}
                onClick={() => onChange(item.id)}
                className={cn(
                  'flex flex-col items-center justify-center gap-1 min-w-0 transition-colors',
                  isActive ? 'text-neon' : 'text-muted-foreground active:text-foreground',
                )}
              >
                <Icon className={cn('w-5 h-5 shrink-0', isActive && 'drop-shadow-[0_0_6px_oklch(0.72_0.18_195_/_50%)]')} />
                <span className="text-[10px] font-medium leading-none">{item.label}</span>
              </button>
            )
          })}
          <button
            onClick={() => setMoreOpen(true)}
            className={cn(
              'flex flex-col items-center justify-center gap-1 min-w-0 transition-colors',
              isOverflowActive || moreOpen ? 'text-neon' : 'text-muted-foreground active:text-foreground',
            )}
          >
            <Menu className="w-5 h-5 shrink-0" />
            <span className="text-[10px] font-medium leading-none">More</span>
          </button>
        </div>
      </nav>

      {/* Overflow sheet */}
      {moreOpen && (
        <div className="lg:hidden fixed inset-0 z-40">
          <button
            aria-label="Close menu"
            className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-fade-in"
            onClick={() => setMoreOpen(false)}
          />
          <div className="absolute bottom-0 inset-x-0 bg-card border-t border-border rounded-t-3xl shadow-2xl shadow-black/50 pb-safe animate-fade-in">
            <div className="flex items-center justify-between px-5 pt-4 pb-2">
              <p className="text-sm font-semibold text-foreground">More</p>
              <button
                onClick={() => setMoreOpen(false)}
                className="w-8 h-8 rounded-lg hover:bg-white/10 flex items-center justify-center transition-colors"
              >
                <X className="w-4 h-4 text-muted-foreground" />
              </button>
            </div>
            <div className="px-3 pb-2 space-y-0.5">
              {overflowItems.map((item) => {
                const Icon = item.icon
                const isActive = active === item.id
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      onChange(item.id)
                      setMoreOpen(false)
                    }}
                    className={cn(
                      'w-full flex items-center gap-3 px-4 py-3.5 rounded-xl text-sm transition-colors',
                      isActive
                        ? 'bg-neon/10 text-neon font-medium'
                        : 'text-foreground/80 active:bg-white/5',
                    )}
                  >
                    <Icon className={cn('w-4.5 h-4.5 shrink-0', isActive ? 'text-neon' : 'text-muted-foreground')} />
                    {item.label}
                  </button>
                )
              })}
            </div>
            <div className="border-t border-border mx-3" />
            <div className="px-3 py-2">
              <button
                onClick={() => {
                  setMoreOpen(false)
                  onLogout()
                }}
                className="w-full flex items-center gap-3 px-4 py-3.5 rounded-xl text-sm text-red-400 active:bg-red-500/10 transition-colors"
              >
                <LogOut className="w-4 h-4 shrink-0" />
                Log out
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
