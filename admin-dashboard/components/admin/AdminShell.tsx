'use client'

import { useCallback, useEffect, useState } from 'react'
import type React from 'react'
import Sidebar, { type TabId } from './Sidebar'
import Header from './Header'
import OverviewTab from './tabs/OverviewTab'
import ProductsTab from './tabs/ProductsTab'
import CategoriesTab from './tabs/CategoriesTab'
import UsersTab from './tabs/UsersTab'
import OrdersTab from './tabs/OrdersTab'
import PaymentsTab from './tabs/PaymentsTab'
import SettingsTab from './tabs/SettingsTab'
import { login, logout, session } from '@/lib/api'

function LoginScreen({ onReady }: { onReady: () => void }) {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      await login(username, password)
      await onReady()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6">
      <form onSubmit={submit} className="w-full max-w-sm rounded-2xl bg-card border border-border p-6 shadow-2xl shadow-black/30">
        <div className="mb-6">
          <p className="text-2xl font-bold text-foreground">ShopBot</p>
          <p className="text-sm text-muted-foreground mt-1">Вход в панель управления</p>
        </div>
        <label className="block text-xs text-muted-foreground mb-1.5">Логин</label>
        <input
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          className="w-full bg-surface-raised border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-neon/30 mb-4"
          autoComplete="username"
        />
        <label className="block text-xs text-muted-foreground mb-1.5">Пароль</label>
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="w-full bg-surface-raised border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-neon/30"
          autoComplete="current-password"
        />
        {error && <p className="mt-3 text-xs text-red-400">{error}</p>}
        <button
          disabled={loading}
          className="mt-5 w-full rounded-xl bg-neon/15 border border-neon/30 text-neon text-sm font-medium py-2.5 hover:bg-neon/25 transition-colors disabled:opacity-60"
        >
          {loading ? 'Проверяю...' : 'Войти'}
        </button>
      </form>
    </div>
  )
}

export default function AdminShell() {
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [authenticated, setAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)

  const refreshSession = useCallback(async () => {
    setLoading(true)
    try {
      const data = await session()
      setAuthenticated(data.authenticated)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refreshSession()
  }, [refreshSession])

  const handleLogout = async () => {
    await logout()
    setAuthenticated(false)
  }

  if (loading) {
    return <div className="min-h-screen bg-background flex items-center justify-center text-sm text-muted-foreground">Загрузка панели...</div>
  }

  if (!authenticated) {
    return <LoginScreen onReady={refreshSession} />
  }

  const renderTab = () => {
    switch (activeTab) {
      case 'overview':    return <OverviewTab />
      case 'products':    return <ProductsTab />
      case 'categories':  return <CategoriesTab />
      case 'users':       return <UsersTab />
      case 'orders':      return <OrdersTab />
      case 'payments':    return <PaymentsTab />
      case 'settings':    return <SettingsTab />
    }
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar active={activeTab} onChange={setActiveTab} />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header activeTab={activeTab} onLogout={handleLogout} />
        <main className="flex-1 overflow-y-auto p-6">
          {renderTab()}
        </main>
      </div>
    </div>
  )
}
