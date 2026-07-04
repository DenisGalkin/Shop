'use client'

import { useMemo, useState } from 'react'
import type React from 'react'
import { Search, Users, Crown, UserCheck, UserPlus, ChevronDown, ExternalLink, Wallet, X } from 'lucide-react'
import { api, initials, type AdminData, type ApiUser } from '@/lib/api'
import { cn } from '@/lib/utils'

const inputClass = 'w-full bg-surface-raised border border-border rounded-xl px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-neon/30'

function userStatus(user: ApiUser) {
  if (user.is_admin) return { id: 'admin', label: 'Админ', cls: 'bg-neon/10 text-neon' }
  if (user.total_spent_cents >= 50000) return { id: 'vip', label: 'VIP', cls: 'bg-amber-400/10 text-amber-400' }
  if (user.orders_count > 0) return { id: 'active', label: 'Активен', cls: 'bg-emerald-400/10 text-emerald-400' }
  return { id: 'new', label: 'Новый', cls: 'bg-indigo-400/10 text-indigo-400' }
}

export default function UsersTab({ data, onRefresh }: { data: AdminData; onRefresh: () => Promise<void> }) {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'vip' | 'new' | 'admin'>('all')
  const [sortBy, setSortBy] = useState<'spent' | 'orders' | 'joined'>('spent')
  const [balanceUser, setBalanceUser] = useState<ApiUser | null>(null)
  const [amount, setAmount] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  const filtered = useMemo(() => data.users
    .filter((user) => {
      const q = search.toLowerCase()
      const username = user.username ? `@${user.username}` : ''
      const matchSearch = user.full_name.toLowerCase().includes(q) || username.toLowerCase().includes(q) || String(user.tg_id).includes(q)
      const matchStatus = statusFilter === 'all' || userStatus(user).id === statusFilter
      return matchSearch && matchStatus
    })
    .sort((a, b) => {
      if (sortBy === 'spent') return b.total_spent_cents - a.total_spent_cents
      if (sortBy === 'orders') return b.orders_count - a.orders_count
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    }), [data.users, search, statusFilter, sortBy])

  const addBalance = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!balanceUser) return
    setBusy(true)
    setMessage('')
    try {
      const result = await api.addBalance(balanceUser.tg_id, amount)
      setMessage(`Баланс ${result.item.full_name} пополнен на ${result.amount_label}`)
      setBalanceUser(null)
      setAmount('')
      await onRefresh()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Не удалось пополнить баланс')
    } finally {
      setBusy(false)
    }
  }

  const statCards = [
    { label: 'Всего пользователей', value: data.users.length.toLocaleString('ru-RU'), icon: Users, color: 'text-neon', bg: 'bg-neon/10', border: 'border-neon/20' },
    { label: 'VIP клиентов', value: data.users.filter((user) => userStatus(user).id === 'vip').length.toLocaleString('ru-RU'), icon: Crown, color: 'text-amber-400', bg: 'bg-amber-400/10', border: 'border-amber-400/20' },
    { label: 'С заказами', value: data.users.filter((user) => user.orders_count > 0).length.toLocaleString('ru-RU'), icon: UserCheck, color: 'text-emerald-400', bg: 'bg-emerald-400/10', border: 'border-emerald-400/20' },
    { label: 'Без заказов', value: data.users.filter((user) => user.orders_count === 0).length.toLocaleString('ru-RU'), icon: UserPlus, color: 'text-indigo-400', bg: 'bg-indigo-400/10', border: 'border-indigo-400/20' },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Пользователи</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Управление аудиторией Telegram-бота</p>
      </div>

      {message && <div className="rounded-xl border border-neon/20 bg-neon/10 text-neon text-sm px-4 py-3">{message}</div>}

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 stagger">
        {statCards.map((card) => {
          const Icon = card.icon
          return (
            <div key={card.label} className={cn('rounded-2xl bg-card border p-4', card.border)}>
              <div className={cn('w-9 h-9 rounded-xl flex items-center justify-center mb-3', card.bg, `border ${card.border}`)}>
                <Icon className={cn('w-4 h-4', card.color)} />
              </div>
              <p className="text-xl font-bold text-foreground">{card.value}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{card.label}</p>
            </div>
          )
        })}
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input type="text" placeholder="Имя, @username или Telegram ID..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full bg-card border border-border rounded-xl pl-9 pr-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-neon/30 focus:border-neon/40 transition-all" />
        </div>
        <div className="flex gap-1.5 overflow-x-auto">
          {(['all', 'active', 'vip', 'new', 'admin'] as const).map((s) => (
            <button key={s} onClick={() => setStatusFilter(s)} className={cn('px-3 py-2 rounded-xl text-xs font-medium transition-all whitespace-nowrap', statusFilter === s ? 'bg-neon/15 text-neon border border-neon/25' : 'bg-card border border-border text-muted-foreground hover:text-foreground')}>
              {s === 'all' ? 'Все' : s === 'active' ? 'Активные' : s === 'vip' ? 'VIP' : s === 'new' ? 'Новые' : 'Админы'}
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-2xl bg-card border border-border overflow-hidden">
        <div className="grid grid-cols-[2fr_1fr_1fr_1fr_1fr_auto] gap-4 px-5 py-3 border-b border-border">
          {[
            { label: 'Пользователь', key: null },
            { label: 'Статус', key: null },
            { label: 'Заказы', key: 'orders' },
            { label: 'Потрачено', key: 'spent' },
            { label: 'Регистрация', key: 'joined' },
            { label: '', key: null },
          ].map((col) => (
            <button key={col.label} onClick={() => col.key && setSortBy(col.key as any)} className={cn('text-left text-[11px] font-semibold uppercase tracking-wide transition-colors flex items-center gap-1', col.key && sortBy === col.key ? 'text-neon' : 'text-muted-foreground hover:text-foreground', !col.key && 'cursor-default')}>
              {col.label}
              {col.key && <ChevronDown className="w-3 h-3" />}
            </button>
          ))}
        </div>

        <div className="divide-y divide-border">
          {filtered.map((user) => {
            const status = userStatus(user)
            const username = user.username ? `@${user.username}` : `ID ${user.tg_id}`
            return (
              <div key={user.id} className="grid grid-cols-[2fr_1fr_1fr_1fr_1fr_auto] gap-4 px-5 py-4 items-center hover:bg-white/[0.03] transition-colors group">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 rounded-xl bg-neon/10 border border-neon/20 flex items-center justify-center text-xs font-bold text-neon shrink-0">
                    {initials(user.full_name, user.username)}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">
                      {user.full_name}
                      {status.id === 'vip' && <Crown className="inline w-3 h-3 text-amber-400 ml-1 mb-0.5" />}
                    </p>
                    <p className="text-xs text-muted-foreground">{username}</p>
                  </div>
                </div>
                <span className={cn('text-[11px] font-medium px-2 py-1 rounded-full w-fit', status.cls)}>{status.label}</span>
                <span className="text-sm font-medium text-foreground">{user.orders_count}</span>
                <span className="text-sm font-semibold text-neon">{user.total_spent_label}</span>
                <span className="text-xs text-muted-foreground">{user.created_label}</span>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button onClick={() => setBalanceUser(user)} className="w-7 h-7 rounded-lg hover:bg-white/10 flex items-center justify-center transition-colors" title="Пополнить баланс">
                    <Wallet className="w-3.5 h-3.5 text-muted-foreground" />
                  </button>
                  {user.username && (
                    <a href={`https://t.me/${user.username}`} target="_blank" rel="noopener noreferrer" className="w-7 h-7 rounded-lg hover:bg-white/10 flex items-center justify-center transition-colors" title="Открыть Telegram">
                      <ExternalLink className="w-3.5 h-3.5 text-muted-foreground" />
                    </a>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {filtered.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            <Users className="w-8 h-8 mx-auto mb-2 opacity-30" />
            <p className="text-sm">Пользователи не найдены</p>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>Показано {filtered.length} из {data.users.length}</span>
      </div>

      {balanceUser && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <form onSubmit={addBalance} className="w-full max-w-sm rounded-2xl bg-card border border-border p-5 shadow-2xl shadow-black/50">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold text-foreground">Пополнить баланс</h3>
                <p className="text-xs text-muted-foreground">{balanceUser.full_name} · {balanceUser.balance_label}</p>
              </div>
              <button type="button" onClick={() => setBalanceUser(null)} className="w-8 h-8 rounded-lg hover:bg-white/10 flex items-center justify-center">
                <X className="w-4 h-4 text-muted-foreground" />
              </button>
            </div>
            <input value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="10.00" className={inputClass} />
            <button disabled={busy} className="mt-4 w-full rounded-xl bg-neon/10 border border-neon/30 text-neon text-sm font-medium py-2.5 hover:bg-neon/20 transition-colors disabled:opacity-60">Пополнить</button>
          </form>
        </div>
      )}
    </div>
  )
}
