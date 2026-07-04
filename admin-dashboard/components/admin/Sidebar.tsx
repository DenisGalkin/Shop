'use client'

import {
  LayoutDashboard,
  Package,
  Users,
  ShoppingCart,
  CreditCard,
  Settings,
  Bot,
  ChevronRight,
  Activity,
} from 'lucide-react'
import { cn } from '@/lib/utils'

export type TabId = 'overview' | 'assortment' | 'users' | 'orders' | 'payments' | 'settings'

const navItems: { id: TabId; label: string; icon: React.ElementType }[] = [
  { id: 'overview', label: 'Обзор', icon: LayoutDashboard },
  { id: 'assortment', label: 'Ассортимент', icon: Package },
  { id: 'users', label: 'Пользователи', icon: Users },
  { id: 'orders', label: 'Заказы', icon: ShoppingCart },
  { id: 'payments', label: 'Платежи', icon: CreditCard },
  { id: 'settings', label: 'Настройки', icon: Settings },
]

interface SidebarProps {
  active: TabId
  onChange: (id: TabId) => void
}

export default function Sidebar({ active, onChange }: SidebarProps) {
  return (
    <aside className="flex flex-col w-64 shrink-0 h-screen bg-sidebar border-r border-sidebar-border sticky top-0">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-sidebar-border">
        <div className="w-9 h-9 rounded-xl bg-neon/10 border border-neon/30 flex items-center justify-center animate-pulse-neon">
          <Bot className="w-5 h-5 text-neon" />
        </div>
        <div>
          <p className="text-sm font-semibold text-foreground leading-none">ShopBot</p>
          <p className="text-xs text-muted-foreground mt-0.5">Admin Panel</p>
        </div>
      </div>

      {/* Bot status */}
      <div className="px-4 py-3 border-b border-sidebar-border">
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-surface-raised/50">
          <span className="relative flex w-2 h-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-400" />
          </span>
          <span className="text-xs text-muted-foreground">Бот онлайн</span>
          <span className="ml-auto text-xs text-muted-foreground flex items-center gap-1">
            <Activity className="w-3 h-3" />
            99.8%
          </span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60 px-3 pb-2 pt-1">
          Навигация
        </p>
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = active === item.id
          return (
            <button
              key={item.id}
              onClick={() => onChange(item.id)}
              className={cn(
                'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 group',
                isActive
                  ? 'bg-sidebar-accent text-sidebar-accent-foreground font-medium'
                  : 'text-sidebar-foreground/70 hover:bg-sidebar-accent/40 hover:text-sidebar-foreground',
              )}
            >
              <Icon
                className={cn(
                  'w-4 h-4 shrink-0 transition-colors',
                  isActive ? 'text-neon' : 'text-muted-foreground group-hover:text-foreground',
                )}
              />
              <span className="flex-1 text-left">{item.label}</span>
              {isActive && (
                <ChevronRight className="w-3 h-3 text-neon/60 shrink-0" />
              )}
            </button>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-sidebar-border">
        <div className="flex items-center gap-3 px-1">
          <div className="w-8 h-8 rounded-lg bg-neon/10 border border-neon/20 flex items-center justify-center text-xs font-bold text-neon">
            AD
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-foreground truncate">Администратор</p>
            <p className="text-[10px] text-muted-foreground">Полный доступ</p>
          </div>
        </div>
      </div>
    </aside>
  )
}
