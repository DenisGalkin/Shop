'use client'

import { useCallback, useEffect, useState } from 'react'
import type React from 'react'
import Sidebar, { type TabId } from './Sidebar'
import Header from './Header'
import OverviewTab from './tabs/OverviewTab'
import AssortmentTab from './tabs/AssortmentTab'
import UsersTab from './tabs/UsersTab'
import OrdersTab from './tabs/OrdersTab'
import PaymentsTab from './tabs/PaymentsTab'
import SettingsTab from './tabs/SettingsTab'
import { ApiError, api, loadAdminData, type AdminData } from '@/lib/api'

function LoginScreen({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      await api.login(username, password)
      onLogin()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось войти')
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
  const [data, setData] = useState<AdminData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    setError('')
    const nextData = await loadAdminData()
    setData(nextData)
  }, [])

  const boot = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const session = await api.session()
      setAuthenticated(session.authenticated)
      if (session.authenticated) {
        await refresh()
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setAuthenticated(false)
      } else {
        setError(err instanceof Error ? err.message : 'Не удалось загрузить панель')
      }
    } finally {
      setLoading(false)
    }
  }, [refresh])

  useEffect(() => {
    boot()
  }, [boot])

  const logout = async () => {
    await api.logout()
    setAuthenticated(false)
    setData(null)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center text-sm text-muted-foreground">
        Загрузка панели...
      </div>
    )
  }

  if (!authenticated) {
    return <LoginScreen onLogin={boot} />
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-background flex flex-col gap-3 items-center justify-center text-sm text-muted-foreground">
        <p>{error || 'Данные не загружены'}</p>
        <button onClick={boot} className="px-4 py-2 rounded-xl bg-neon/10 border border-neon/30 text-neon">
          Повторить
        </button>
      </div>
    )
  }

  const renderTab = () => {
    switch (activeTab) {
      case 'overview':
        return <OverviewTab data={data} onOpenTab={setActiveTab} />
      case 'assortment':
        return <AssortmentTab data={data} onRefresh={refresh} />
      case 'users':
        return <UsersTab data={data} onRefresh={refresh} />
      case 'orders':
        return <OrdersTab data={data} />
      case 'payments':
        return <PaymentsTab data={data} />
      case 'settings':
        return <SettingsTab />
    }
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <Sidebar active={activeTab} onChange={setActiveTab} />

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header activeTab={activeTab} data={data} onRefresh={refresh} onLogout={logout} />
        <main className="flex-1 overflow-y-auto p-6">
          {error && (
            <div className="mb-4 rounded-xl border border-red-400/20 bg-red-400/10 text-red-400 text-sm px-4 py-3">
              {error}
            </div>
          )}
          {renderTab()}
        </main>
      </div>
    </div>
  )
}
