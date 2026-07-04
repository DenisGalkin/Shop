'use client'

import { Bell, Calendar, LogOut } from 'lucide-react'
import { useState } from 'react'
import type { TabId } from './Sidebar'

const tabTitles: Record<TabId, string> = {
  overview:    'Обзор',
  products:    'Товары',
  categories:  'Категории',
  users:       'Пользователи',
  orders:      'Заказы',
  payments:    'Платежи',
  settings:    'Настройки',
}

interface HeaderProps {
  activeTab: TabId
  onLogout: () => void
}

export default function Header({ activeTab, onLogout }: HeaderProps) {
  const [notifOpen, setNotifOpen] = useState(false)

  const now = new Date()
  const dateStr = now.toLocaleDateString('en', { weekday: 'long', day: 'numeric', month: 'long' })

  return (
    <header className="sticky top-0 z-20 flex items-center justify-between px-6 py-3.5 bg-background/80 backdrop-blur-xl border-b border-border">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground text-sm">ShopBot</span>
        <span className="text-muted-foreground/40 text-sm">/</span>
        <span className="text-sm font-medium text-foreground">{tabTitles[activeTab]}</span>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-card border border-border text-xs text-muted-foreground">
          <Calendar className="w-3.5 h-3.5" />
          <span>{dateStr}</span>
        </div>

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setNotifOpen(!notifOpen)}
            className="relative w-9 h-9 rounded-xl hover:bg-card border border-transparent hover:border-border flex items-center justify-center transition-all"
          >
            <Bell className="w-4 h-4 text-muted-foreground" />
          </button>

          {notifOpen && (
            <div className="absolute right-0 top-11 w-80 rounded-2xl bg-card border border-border shadow-2xl shadow-black/40 overflow-hidden z-50 animate-fade-in">
              <div className="px-4 py-3 border-b border-border flex items-center justify-between">
                <p className="text-sm font-semibold text-foreground">Notifications</p>
                <span className="text-[10px] font-medium bg-neon/15 text-neon px-2 py-0.5 rounded-full">
                  live
                </span>
              </div>
              <div className="px-4 py-5 text-center text-xs text-muted-foreground">Нет новых уведомлений</div>
              <div className="px-4 py-2.5 border-t border-border text-center">
                <button onClick={() => setNotifOpen(false)} className="text-xs text-neon hover:underline">Закрыть</button>
              </div>
            </div>
          )}
        </div>

        <button onClick={onLogout} className="w-8 h-8 rounded-xl bg-neon/10 border border-neon/25 flex items-center justify-center text-xs font-bold text-neon cursor-pointer hover:bg-neon/20 transition-colors" title="Выйти">
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  )
}
