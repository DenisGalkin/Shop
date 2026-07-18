'use client'

import { Bell, Calendar, LogOut } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { getDashboard, type DashboardData } from '@/lib/api'
import type { TabId } from './Sidebar'
import { cn } from '@/lib/utils'

const tabTitles: Record<TabId, string> = {
  overview: 'Overview',
  products: 'Products',
  categories: 'Categories',
  users: 'Users',
  orders: 'Orders',
  payments: 'Payments',
  settings: 'Settings',
}

type NotificationItem = {
  id: string
  title: string
  meta: string
  badge: string
  tone: 'warn' | 'danger' | 'info'
  tab: TabId
}

const toneClasses: Record<NotificationItem['tone'], string> = {
  warn: 'border-amber-400/20 bg-amber-400/5 text-amber-300',
  danger: 'border-red-400/20 bg-red-400/5 text-red-300',
  info: 'border-neon/20 bg-neon/5 text-neon',
}

function buildNotifications(data: DashboardData): NotificationItem[] {
  const items: NotificationItem[] = []

  data.outOfStock.forEach((item) => {
    items.push({
      id: `out-${item.id}`,
      title: `${item.title} is out of stock`,
      meta: `${item.category} · ${item.stock} keys left`,
      badge: 'Stock',
      tone: 'danger',
      tab: 'products',
    })
  })

  data.lowStock
    .filter((item) => item.stock > 0)
    .forEach((item) => {
      items.push({
        id: `low-${item.id}`,
        title: `${item.title} is running low`,
        meta: `${item.category} · ${item.stock} keys left`,
        badge: 'Stock',
        tone: 'warn',
        tab: 'products',
      })
    })

  data.emptyCategories.forEach((category) => {
    items.push({
      id: `cat-${category.id}`,
      title: `${category.title} has no products`,
      meta: 'Add items or hide the category.',
      badge: 'Catalog',
      tone: 'info',
      tab: 'categories',
    })
  })

  const pending = Number(data.stats.payments_pending_total || 0)
  if (pending > 0) {
    items.push({
      id: 'payments-pending',
      title: `${pending} payment${pending === 1 ? '' : 's'} pending`,
      meta: 'Review invoice and provider statuses.',
      badge: 'Payments',
      tone: 'warn',
      tab: 'payments',
    })
  }

  const errors = Number(data.stats.payment_errors_total || 0)
  if (errors > 0) {
    items.push({
      id: 'payments-errors',
      title: `${errors} payment${errors === 1 ? '' : 's'} with errors`,
      meta: 'Failed or unfulfilled payments need attention.',
      badge: 'Payments',
      tone: 'danger',
      tab: 'payments',
    })
  }

  return items.slice(0, 8)
}

interface HeaderProps {
  activeTab: TabId
  onLogout: () => void
  onChangeTab: (tab: TabId) => void
}

export default function Header({ activeTab, onLogout, onChangeTab }: HeaderProps) {
  const [notifOpen, setNotifOpen] = useState(false)
  const [dashboard, setDashboard] = useState<DashboardData | null>(null)

  useEffect(() => {
    let active = true

    const load = async () => {
      try {
        const data = await getDashboard()
        if (active) setDashboard(data)
      } catch {
        if (active) setDashboard(null)
      }
    }

    load()
    const timer = window.setInterval(load, 60000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [])

  const now = new Date()
  const dateStr = now.toLocaleDateString('en', { weekday: 'long', day: 'numeric', month: 'long' })
  const notifications = useMemo(() => (dashboard ? buildNotifications(dashboard) : []), [dashboard])

  return (
    <header className="sticky top-0 z-20 flex items-center justify-between px-4 py-4 sm:px-8 sm:py-5 lg:px-10 bg-background/80 backdrop-blur-xl border-b border-border pt-safe min-h-[64px] sm:min-h-[76px]">
      <div className="flex items-center gap-2.5 min-w-0">
        <span className="hidden sm:inline text-muted-foreground text-sm">VEXND SHOP</span>
        <span className="hidden sm:inline text-muted-foreground/40 text-sm">/</span>
        <span className="text-lg sm:text-base font-semibold sm:font-medium text-foreground truncate">{tabTitles[activeTab]}</span>
      </div>

      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-card border border-border text-xs text-muted-foreground">
          <Calendar className="w-3.5 h-3.5" />
          <span>{dateStr}</span>
        </div>

        <div className="relative">
          <button
            onClick={() => setNotifOpen(!notifOpen)}
            className="relative w-10 h-10 sm:w-9 sm:h-9 rounded-xl hover:bg-card active:bg-card border border-transparent hover:border-border flex items-center justify-center transition-all"
            title="Notifications"
          >
            <Bell className="w-4 h-4 text-muted-foreground" />
            {notifications.length > 0 && (
              <span className="absolute right-2 top-2 sm:right-1.5 sm:top-1.5 flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-400" />
              </span>
            )}
          </button>

          {notifOpen && (
            <>
              <button
                aria-label="Close notifications"
                className="fixed inset-0 z-40 sm:hidden"
                onClick={() => setNotifOpen(false)}
              />
              <div className="fixed left-4 right-4 top-20 sm:absolute sm:left-auto sm:right-0 sm:top-12 sm:w-80 rounded-2xl bg-card border border-border shadow-2xl shadow-black/40 overflow-hidden z-50 animate-fade-in">
                <div className="px-4 py-3 border-b border-border flex items-center justify-between">
                  <p className="text-sm font-semibold text-foreground">Notifications</p>
                  <span className="text-[10px] font-medium bg-neon/15 text-neon px-2 py-0.5 rounded-full">
                    {notifications.length} open
                  </span>
                </div>

                {notifications.length > 0 ? (
                  <div className="max-h-96 overflow-y-auto p-3 space-y-2">
                    {notifications.map((item) => (
                      <button
                        key={item.id}
                        onClick={() => {
                          onChangeTab(item.tab)
                          setNotifOpen(false)
                        }}
                        className={cn(
                          'w-full rounded-xl border px-3 py-3 text-left transition-colors hover:border-white/15 hover:bg-white/[0.03]',
                          toneClasses[item.tone],
                        )}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-medium text-foreground">{item.title}</p>
                            <p className="text-xs text-muted-foreground mt-1">{item.meta}</p>
                          </div>
                          <span className="shrink-0 rounded-full bg-white/5 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                            {item.badge}
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="px-4 py-5 text-center text-xs text-muted-foreground">No new notifications</div>
                )}
              </div>
            </>
          )}
        </div>

        <button onClick={onLogout} className="hidden lg:flex w-8 h-8 rounded-xl bg-neon/10 border border-neon/25 items-center justify-center text-xs font-bold text-neon cursor-pointer hover:bg-neon/20 transition-colors" title="Log out">
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  )
}
