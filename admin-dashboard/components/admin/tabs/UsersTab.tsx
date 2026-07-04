'use client'

import { useEffect, useState } from 'react'
import {
  Search, Users, UserCheck, UserX, UserPlus, ChevronUp, ChevronDown,
  ExternalLink, X, Shield, ChevronsUpDown,
} from 'lucide-react'
import { adjustUserBalance, getUsers, type User } from '@/lib/api'
import { cn } from '@/lib/utils'

const fmt = (cents: number) => `$${(cents / 100).toFixed(2)}`

// ── Status config ─────────────────────────────────────────────────────────────
const statusConfig: Record<User['status'], { label: string; cls: string }> = {
  active:   { label: 'Active',    cls: 'bg-emerald-400/10 text-emerald-400' },
  new:      { label: 'New',       cls: 'bg-indigo-400/10 text-indigo-400' },
  inactive: { label: 'Inactive',  cls: 'bg-zinc-500/20 text-zinc-400' },
  admin:    { label: 'Admin',     cls: 'bg-neon/10 text-neon' },
}

// ── Sort helpers ──────────────────────────────────────────────────────────────
type SortKey = 'id' | 'full_name' | 'status' | 'orders' | 'total_spent_cents' | 'created_at'
type SortDir = 'asc' | 'desc'

function SortBtn({ col, sortKey, sortDir, onClick }: { col: SortKey; sortKey: SortKey; sortDir: SortDir; onClick: () => void }) {
  const active = col === sortKey
  return (
    <button
      onClick={onClick}
      className={cn('flex items-center gap-0.5 text-left text-[11px] font-semibold uppercase tracking-wide transition-colors', active ? 'text-neon' : 'text-muted-foreground hover:text-foreground')}
    >
      {active
        ? (sortDir === 'asc' ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)
        : <ChevronsUpDown className="w-3 h-3 opacity-40" />}
    </button>
  )
}

// ── User detail modal ─────────────────────────────────────────────────────────
function UserModal({ user, onClose, onAdjustBalance }: { user: User; onClose: () => void; onAdjustBalance: (user: User, delta: string) => void }) {
  const [balanceDelta, setBalanceDelta] = useState('')
  const status = statusConfig[user.status]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-lg bg-card border border-border rounded-2xl shadow-2xl shadow-black/50 overflow-hidden max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between px-6 py-4 border-b border-border shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-neon/10 border border-neon/20 flex items-center justify-center text-sm font-bold text-neon">
              {user.avatar}
            </div>
            <div>
              <p className="text-sm font-semibold text-foreground">{user.full_name}</p>
              <p className="text-xs text-muted-foreground">{user.username ? `@${user.username}` : '— no username —'}</p>
            </div>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-lg hover:bg-white/10 flex items-center justify-center transition-colors mt-0.5">
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>

        <div className="overflow-y-auto flex-1 px-6 py-5 space-y-5">
          {/* Status + admin badge */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className={cn('text-xs font-medium px-2.5 py-1 rounded-full', status.cls)}>{status.label}</span>
            {user.is_admin && (
              <span className="flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full bg-neon/10 text-neon border border-neon/20">
                <Shield className="w-3 h-3" /> Administrator
              </span>
            )}
            {user.language_code && (
              <span className="text-xs text-muted-foreground px-2.5 py-1 rounded-full bg-surface-raised border border-border uppercase">
                {user.language_code}
              </span>
            )}
          </div>

          {/* Key info grid */}
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'ID',              value: String(user.id) },
              { label: 'Telegram ID',     value: String(user.tg_id) },
              { label: 'Balance',         value: fmt(user.balance_cents) },
              { label: 'Total deposited', value: fmt(user.total_deposited_cents) },
              { label: 'Total spent',     value: fmt(user.total_spent_cents) },
              { label: 'Referral earned', value: fmt(user.referral_earned_cents) },
              { label: 'Referral balance',value: fmt(user.referral_balance_cents) },
              { label: 'Referrer ID',     value: user.referrer_user_id ? String(user.referrer_user_id) : '—' },
              { label: 'Orders',          value: String(user.orders) },
              { label: 'Registered',      value: new Date(user.created_at).toLocaleDateString('en', { day: '2-digit', month: 'short', year: 'numeric' }) },
              { label: 'Last active',     value: new Date(user.lastActive).toLocaleDateString('en', { day: '2-digit', month: 'short', year: 'numeric' }) },
            ].map((row) => (
              <div key={row.label} className="bg-surface-raised border border-border rounded-xl px-4 py-3">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wide">{row.label}</p>
                <p className="text-sm font-semibold text-foreground mt-0.5">{row.value}</p>
              </div>
            ))}
          </div>

          {/* Adjust balance */}
          <div className="p-4 rounded-xl bg-surface-raised border border-border">
            <p className="text-xs font-semibold text-foreground mb-2">Adjust balance</p>
            <div className="flex gap-2">
              <input
                type="number"
                step="0.01"
                placeholder="e.g. +5.00 or -2.50"
                value={balanceDelta}
                onChange={(e) => setBalanceDelta(e.target.value)}
                className="flex-1 bg-card border border-border rounded-xl px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-neon/30"
              />
              <button
                onClick={() => {
                  onAdjustBalance(user, balanceDelta)
                  setBalanceDelta('')
                }}
                disabled={!balanceDelta}
                className="px-4 py-2 rounded-xl bg-neon/15 border border-neon/30 text-neon text-sm font-medium hover:bg-neon/25 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Apply
              </button>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1.5">USD value — will be converted to cents automatically.</p>
          </div>

          <div className="flex gap-2 flex-wrap">
            {user.username && (
              <a
                href={`https://t.me/${user.username}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-card border border-border text-muted-foreground text-xs font-medium hover:text-foreground hover:border-white/15 transition-all"
              >
                <ExternalLink className="w-3.5 h-3.5" /> Open in Telegram
              </a>
            )}
          </div>
        </div>

        <div className="px-6 py-4 border-t border-border flex justify-end shrink-0">
          <button onClick={onClose} className="px-4 py-2 rounded-xl text-sm text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors">
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main tab ──────────────────────────────────────────────────────────────────
export default function UsersTab() {
  const [items, setItems] = useState<User[]>([])
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | User['status']>('all')
  const [sortKey, setSortKey] = useState<SortKey>('total_spent_cents')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [error, setError] = useState('')

  const refresh = async () => {
    const result = await getUsers({ search })
    setItems(result.users)
  }

  useEffect(() => {
    refresh().catch((err) => setError(err instanceof Error ? err.message : 'Failed to load users'))
  }, [])

  const handleAdjustBalance = async (user: User, delta: string) => {
    try {
      const cents = Math.round(parseFloat(delta || '0') * 100)
      if (cents <= 0) return
      await adjustUserBalance(user.tg_id, cents)
      await refresh()
      setSelectedUser(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to adjust balance')
    }
  }

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortKey(key); setSortDir('desc') }
  }

  const filtered = items
    .filter((u) => {
      const q = search.toLowerCase()
      const matchSearch =
        u.full_name.toLowerCase().includes(q) ||
        (u.username ?? '').toLowerCase().includes(q) ||
        String(u.tg_id).includes(q) ||
        String(u.id).includes(q)
      const matchStatus = statusFilter === 'all' || u.status === statusFilter
      return matchSearch && matchStatus
    })
    .sort((a, b) => {
      let av: number | string = a[sortKey] as number | string
      let bv: number | string = b[sortKey] as number | string
      if (sortKey === 'full_name' || sortKey === 'status' || sortKey === 'created_at') {
        av = String(av).toLowerCase()
        bv = String(bv).toLowerCase()
        return sortDir === 'asc' ? (av < bv ? -1 : av > bv ? 1 : 0) : (av > bv ? -1 : av < bv ? 1 : 0)
      }
      return sortDir === 'asc' ? (av as number) - (bv as number) : (bv as number) - (av as number)
    })

  const colHdr = (label: string, key: SortKey) => (
    <div className="flex items-center gap-1">
      <span>{label}</span>
      <SortBtn col={key} sortKey={sortKey} sortDir={sortDir} onClick={() => handleSort(key)} />
    </div>
  )

  const statCards = [
    { label: 'Total users', value: String(items.length), icon: Users, color: 'text-neon', bg: 'bg-neon/10', border: 'border-neon/20' },
    { label: 'Active', value: String(items.filter((user) => user.status === 'active').length), icon: UserCheck, color: 'text-emerald-400', bg: 'bg-emerald-400/10', border: 'border-emerald-400/20' },
    { label: 'Inactive', value: String(items.filter((user) => user.status === 'inactive').length), icon: UserX, color: 'text-zinc-400', bg: 'bg-zinc-500/20', border: 'border-zinc-500/20' },
    { label: 'New', value: String(items.filter((user) => user.status === 'new').length), icon: UserPlus, color: 'text-indigo-400', bg: 'bg-indigo-400/10', border: 'border-indigo-400/20' },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      {error && <div className="rounded-xl border border-red-400/20 bg-red-400/10 text-red-400 text-sm px-4 py-3">{error}</div>}
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Пользователи</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Telegram bot user management</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 stagger">
        {statCards.map((card) => {
          const Icon = card.icon
          return (
            <div key={card.label} className={cn('rounded-2xl bg-card border p-4', card.border)}>
              <div className={cn('w-9 h-9 rounded-xl flex items-center justify-center mb-3 border', card.bg, card.border)}>
                <Icon className={cn('w-4 h-4', card.color)} />
              </div>
              <p className="text-xl font-bold text-foreground">{card.value}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{card.label}</p>
            </div>
          )
        })}
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Name, @username or Telegram ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-card border border-border rounded-xl pl-9 pr-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-neon/30 focus:border-neon/40 transition-all"
          />
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {(['all', 'active', 'new', 'inactive', 'admin'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={cn(
                'px-3 py-2 rounded-xl text-xs font-medium transition-all',
                statusFilter === s
                  ? 'bg-neon/15 text-neon border border-neon/25'
                  : 'bg-card border border-border text-muted-foreground hover:text-foreground',
              )}
            >
              {s === 'all' ? 'All' : statusConfig[s as User['status']].label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="rounded-2xl bg-card border border-border overflow-x-auto">
        {/* Table header */}
        <div className="min-w-[700px] grid grid-cols-[60px_50px_2fr_1fr_1fr_1fr_1fr_44px] gap-3 px-5 py-3 border-b border-border">
          {colHdr('ID', 'id')}
          <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">TG ID</span>
          {colHdr('User', 'full_name')}
          {colHdr('Status', 'status')}
          {colHdr('Orders', 'orders')}
          {colHdr('Spent', 'total_spent_cents')}
          {colHdr('Registered', 'created_at')}
          <span />
        </div>

        {/* Rows */}
        <div className="min-w-[700px] divide-y divide-border">
          {filtered.map((user) => {
            const status = statusConfig[user.status]
            return (
              <div
                key={user.id}
                onClick={() => setSelectedUser(user)}
                className="grid grid-cols-[60px_50px_2fr_1fr_1fr_1fr_1fr_44px] gap-3 px-5 py-3.5 items-center hover:bg-white/[0.03] transition-colors cursor-pointer group"
              >
                {/* ID */}
                <span className="text-xs font-mono text-muted-foreground">#{user.id}</span>

                {/* TG ID (shortened) */}
                <span className="text-[11px] font-mono text-muted-foreground truncate" title={String(user.tg_id)}>
                  {String(user.tg_id).slice(0, 6)}…
                </span>

                {/* User */}
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="w-8 h-8 rounded-lg bg-neon/10 border border-neon/20 flex items-center justify-center text-[11px] font-bold text-neon shrink-0">
                    {user.avatar}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-foreground truncate flex items-center gap-1">
                      {user.full_name}
                      {user.is_admin && <Shield className="w-3 h-3 text-neon shrink-0" />}
                    </p>
                    <p className="text-xs text-muted-foreground truncate">
                      {user.username ? `@${user.username}` : '—'}
                    </p>
                  </div>
                </div>

                {/* Status */}
                <span className={cn('text-[11px] font-medium px-2 py-0.5 rounded-full w-fit', status.cls)}>
                  {status.label}
                </span>

                {/* Orders */}
                <span className="text-sm font-medium text-foreground">{user.orders}</span>

                {/* Spent */}
                <span className="text-sm font-semibold text-neon">{fmt(user.total_spent_cents)}</span>

                {/* Registered */}
                <span className="text-xs text-muted-foreground">
                  {new Date(user.created_at).toLocaleDateString('en', { day: '2-digit', month: 'short', year: '2-digit' })}
                </span>

                {/* Action */}
                <div className="flex justify-end">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-white/10">
                    <ExternalLink className="w-3.5 h-3.5 text-muted-foreground" />
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {filtered.length === 0 && (
          <div className="text-center py-12 text-muted-foreground min-w-[700px]">
            <Users className="w-8 h-8 mx-auto mb-2 opacity-30" />
            <p className="text-sm">No users found</p>
          </div>
        )}
      </div>

      {/* Pagination stub */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>Showing {filtered.length} of {items.length}</span>
      </div>

      {/* User detail modal */}
      {selectedUser && <UserModal user={selectedUser} onClose={() => setSelectedUser(null)} onAdjustBalance={handleAdjustBalance} />}
    </div>
  )
}
