'use client'

import { Bell, Calendar, LogOut, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import type { TabId } from './Sidebar'
import type { AdminData } from '@/lib/api'

const tabTitles: Record<TabId, string> = {
  overview: 'Обзор',
  assortment: 'Ассортимент',
  users: 'Пользователи',
  orders: 'Заказы',
  payments: 'Платежи',
  settings: 'Настройки',
}

interface HeaderProps {
  activeTab: TabId
  data: AdminData
  onRefresh: () => Promise<void>
  onLogout: () => void
}

export default function Header({ activeTab, data, onRefresh, onLogout }: HeaderProps) {
  const [notifOpen, setNotifOpen] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  const now = new Date()
  const dateStr = now.toLocaleDateString('ru', { weekday: 'long', day: 'numeric', month: 'long' })
  const notifications = [
    ...data.dashboard.low_stock.slice(0, 3).map((product) => ({
      id: `stock-${product.id}`,
      text: `Мало товара: ${product.title} (${product.stock_count} шт)`,
      time: product.stock_count === 0 ? 'нет ключей' : 'низкий остаток',
      type: 'warning',
    })),
    ...data.dashboard.recent_orders.slice(0, 3).map((order) => ({
      id: `order-${order.id}`,
      text: `Заказ #${order.id}: ${order.product_title}`,
      time: order.created_label,
      type: 'order',
    })),
  ].slice(0, 5)

  const refresh = async () => {
    setRefreshing(true)
    try {
      await onRefresh()
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <header className="sticky top-0 z-20 flex items-center justify-between px-6 py-3.5 bg-background/80 backdrop-blur-xl border-b border-border">
      {/* Left: breadcrumb */}
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground text-sm">ShopBot</span>
        <span className="text-muted-foreground/40 text-sm">/</span>
        <span className="text-sm font-medium text-foreground">{tabTitles[activeTab]}</span>
      </div>

      {/* Right: actions */}
      <div className="flex items-center gap-2">
        {/* Date */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-card border border-border text-xs text-muted-foreground">
          <Calendar className="w-3.5 h-3.5" />
          <span className="capitalize">{dateStr}</span>
        </div>

        {/* Notifications */}
        <button
          onClick={refresh}
          className="w-9 h-9 rounded-xl hover:bg-card border border-transparent hover:border-border flex items-center justify-center transition-all"
          title="Обновить данные"
        >
          <RefreshCw className={`w-4 h-4 text-muted-foreground ${refreshing ? 'animate-spin' : ''}`} />
        </button>

        <div className="relative">
          <button
            onClick={() => setNotifOpen(!notifOpen)}
            className="relative w-9 h-9 rounded-xl hover:bg-card border border-transparent hover:border-border flex items-center justify-center transition-all"
          >
            <Bell className="w-4 h-4 text-muted-foreground" />
            {notifications.length > 0 && <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-neon animate-pulse-neon" />}
          </button>

          {notifOpen && (
            <div className="absolute right-0 top-11 w-80 rounded-2xl bg-card border border-border shadow-2xl shadow-black/40 overflow-hidden z-50 animate-fade-in">
              <div className="px-4 py-3 border-b border-border flex items-center justify-between">
                <p className="text-sm font-semibold text-foreground">Уведомления</p>
                <span className="text-[10px] font-medium bg-neon/15 text-neon px-2 py-0.5 rounded-full">
                  {notifications.length} важных
                </span>
              </div>
              <div className="divide-y divide-border">
                {notifications.map((n) => (
                  <div key={n.id} className="flex items-start gap-3 px-4 py-3 hover:bg-white/[0.03] transition-colors">
                    <div
                      className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
                        n.type === 'order'
                          ? 'bg-neon'
                          : n.type === 'warning'
                          ? 'bg-amber-400'
                          : 'bg-indigo-400'
                      }`}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-foreground leading-relaxed">{n.text}</p>
                      <p className="text-[10px] text-muted-foreground mt-0.5">{n.time}</p>
                    </div>
                  </div>
                ))}
                {notifications.length === 0 && (
                  <div className="px-4 py-5 text-center text-xs text-muted-foreground">Сейчас нет важных событий</div>
                )}
              </div>
              <div className="px-4 py-2.5 border-t border-border text-center">
                <button onClick={() => setNotifOpen(false)} className="text-xs text-neon hover:underline">Закрыть</button>
              </div>
            </div>
          )}
        </div>

        {/* Avatar */}
        <button
          onClick={onLogout}
          className="w-8 h-8 rounded-xl bg-neon/10 border border-neon/25 flex items-center justify-center text-xs font-bold text-neon cursor-pointer hover:bg-neon/20 transition-colors"
          title="Выйти"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  )
}
