'use client'

import { useEffect, useMemo, useState } from 'react'
import {
  CreditCard, CheckCircle2, Clock, XCircle, RotateCcw,
  Search, TrendingUp, Copy,
} from 'lucide-react'
import { getPayments, type Payment } from '@/lib/api'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { cn } from '@/lib/utils'

const fmt = (cents: number) => `$${(cents / 100).toFixed(2)}`

const statusConfig: Record<Payment['status'], { label: string; cls: string; icon: React.ElementType }> = {
  confirmed: { label: 'Confirmed', cls: 'bg-emerald-400/10 text-emerald-400', icon: CheckCircle2 },
  pending: { label: 'Pending', cls: 'bg-amber-400/10 text-amber-400', icon: Clock },
  failed: { label: 'Failed', cls: 'bg-red-400/10 text-red-400', icon: XCircle },
  refunded: { label: 'Refunded', cls: 'bg-indigo-400/10 text-indigo-400', icon: RotateCcw },
}

const methodMeta: Record<string, { label: string; symbol: string; cls: string; accentCls: string; key: string }> = {
  ton: { label: 'TON', symbol: '◈', cls: 'border-blue-400/20 bg-blue-400/5', accentCls: 'text-blue-400', key: 'ton' },
  heleket: { label: 'Heleket', symbol: '₮', cls: 'border-emerald-400/20 bg-emerald-400/5', accentCls: 'text-emerald-400', key: 'heleket' },
  cryptobot: { label: 'CryptoBot', symbol: '₿', cls: 'border-amber-400/20 bg-amber-400/5', accentCls: 'text-amber-400', key: 'cryptobot' },
  lolz: { label: 'Lolzteam', symbol: 'L', cls: 'border-indigo-400/20 bg-indigo-400/5', accentCls: 'text-indigo-400', key: 'lolz' },
  balance: { label: 'Balance', symbol: '$', cls: 'border-neon/20 bg-neon/5', accentCls: 'text-neon', key: 'balance' },
}

function dayKey(value: string) {
  return value ? new Date(value).toISOString().slice(5, 10) : ''
}

export default function PaymentsTab() {
  const [payments, setPayments] = useState<Payment[]>([])
  const [search, setSearch] = useState('')
  const [copied, setCopied] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    setLoading(true)
    getPayments()
      .then((res) => {
        if (!alive) return
        setPayments(res.payments)
        setError(null)
      })
      .catch((err) => alive && setError(err instanceof Error ? err.message : 'Failed to load payments'))
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
  }, [])

  const handleCopy = (text: string, id: number) => {
    navigator.clipboard.writeText(text)
    setCopied(id)
    setTimeout(() => setCopied(null), 1500)
  }

  const filtered = useMemo(() => payments.filter((p) => {
    const q = search.toLowerCase()
    return (
      String(p.id).includes(q) ||
      (p.username ?? '').toLowerCase().includes(q) ||
      p.user_name.toLowerCase().includes(q) ||
      (p.provider_payment_id ?? '').toLowerCase().includes(q) ||
      (p.order_id ? String(p.order_id).includes(q) : false)
    )
  }), [payments, search])

  const cryptoCards = useMemo(() => {
    const confirmed = payments.filter((p) => p.status === 'confirmed')
    const totals = confirmed.reduce<Record<string, number>>((acc, payment) => {
      const key = (payment.payment_type || 'balance').toLowerCase()
      acc[key] = (acc[key] || 0) + payment.amount_cents
      return acc
    }, {})
    return Object.entries(totals)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([key, cents]) => {
        const meta = methodMeta[key] ?? { label: key || 'Other', symbol: key.slice(0, 1).toUpperCase() || '$', cls: 'border-white/10 bg-white/5', accentCls: 'text-muted-foreground', key }
        return { ...meta, amount: fmt(cents), count: confirmed.filter((p) => (p.payment_type || 'balance').toLowerCase() === key).length }
      })
  }, [payments])

  const monthlyFlow = useMemo(() => {
    const buckets = payments
      .filter((p) => p.status === 'confirmed')
      .reduce<Record<string, Record<string, number>>>((acc, payment) => {
        const date = dayKey(payment.created_at)
        if (!date) return acc
        const key = (payment.payment_type || 'balance').toLowerCase()
        acc[date] = acc[date] || { date }
        acc[date][key] = (acc[date][key] || 0) + Math.round(payment.amount_cents / 100)
        return acc
      }, {})
    return Object.values(buckets).sort((a, b) => a.date.localeCompare(b.date)).slice(-10)
  }, [payments])

  const chartKeys = useMemo(() => {
    const keys = Array.from(new Set(monthlyFlow.flatMap((row) => Object.keys(row).filter((key) => key !== 'date'))))
    return keys.slice(0, 3)
  }, [monthlyFlow])

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Платежи</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Financial operations and payment records</p>
      </div>

      {error && (
        <div className="rounded-xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 stagger">
        {(cryptoCards.length ? cryptoCards : [{ label: 'Payments', symbol: '$', amount: '$0.00', count: 0, cls: 'border-white/10 bg-white/5', accentCls: 'text-muted-foreground', key: 'empty' }]).map((card) => (
          <div key={card.key} className={cn('rounded-2xl border p-5 transition-all hover:border-white/20', card.cls)}>
            <div className="flex items-start justify-between mb-3">
              <div className={cn('text-2xl font-bold', card.accentCls)}>{card.symbol}</div>
              <span className="text-xs font-medium text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-full flex items-center gap-1">
                <TrendingUp className="w-3 h-3" />{card.count}
              </span>
            </div>
            <p className={cn('text-xl font-bold', card.accentCls)}>{card.amount}</p>
            <p className="text-xs text-muted-foreground mt-1">confirmed payments</p>
            <p className="text-sm font-medium text-foreground mt-0.5">{card.label}</p>
          </div>
        ))}
      </div>

      <div className="rounded-2xl bg-card border border-border p-5">
        <div className="flex items-center justify-between mb-5 flex-wrap gap-2">
          <div>
            <h3 className="text-sm font-semibold text-foreground">Daily inflow (USD)</h3>
            <p className="text-xs text-muted-foreground">Breakdown by payment method</p>
          </div>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            {chartKeys.map((key, index) => (
              <span key={key} className="flex items-center gap-1.5">
                <span className={cn('w-2 h-2 rounded-full', ['bg-blue-400', 'bg-emerald-400', 'bg-amber-400'][index])} />{methodMeta[key]?.label ?? key}
              </span>
            ))}
          </div>
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={monthlyFlow} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
            <defs>
              {[{ id: 'm0', color: 'oklch(0.65 0.18 255)' }, { id: 'm1', color: 'oklch(0.65 0.16 155)' }, { id: 'm2', color: 'oklch(0.75 0.17 85)' }].map((g) => (
                <linearGradient key={g.id} id={`grad-${g.id}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={g.color} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={g.color} stopOpacity={0} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="oklch(1 0 0 / 5%)" />
            <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'oklch(0.55 0.01 264)' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 10, fill: 'oklch(0.55 0.01 264)' }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v}`} />
            <Tooltip
              contentStyle={{ background: 'oklch(0.13 0.008 264)', border: '1px solid oklch(1 0 0 / 8%)', borderRadius: '10px', fontSize: '12px', color: 'oklch(0.95 0.005 264)' }}
              formatter={(v) => `$${v}`}
            />
            {chartKeys.map((key, index) => (
              <Area
                key={key}
                type="monotone"
                dataKey={key}
                stroke={['oklch(0.65 0.18 255)', 'oklch(0.65 0.16 155)', 'oklch(0.75 0.17 85)'][index]}
                strokeWidth={2}
                fill={`url(#grad-m${index})`}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="rounded-2xl bg-card border border-border overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h3 className="text-sm font-semibold text-foreground">Transactions</h3>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-surface-raised border border-border rounded-lg pl-8 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-neon/30 w-44"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px] text-xs">
            <thead>
              <tr className="border-b border-border">
                {[
                  { label: 'Status', w: 'w-[130px]' },
                  { label: 'ID', w: 'w-[50px]' },
                  { label: 'Order', w: 'w-[70px]' },
                  { label: 'User', w: 'w-[160px]' },
                  { label: 'Type', w: 'w-[80px]' },
                  { label: 'Purpose', w: 'w-[80px]' },
                  { label: 'Amount', w: 'w-[100px]' },
                  { label: 'Ext. amount', w: 'w-[110px]' },
                  { label: 'Provider ID', w: 'w-[140px]' },
                  { label: 'Created', w: 'w-[120px]' },
                ].map((col) => (
                  <th key={col.label} className={cn('px-4 py-3 text-left font-semibold uppercase tracking-wide text-muted-foreground', col.w)}>
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered.map((tx) => {
                const status = statusConfig[tx.status]
                const StatusIcon = status.icon
                return (
                  <tr key={tx.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-3.5">
                      <span className={cn('inline-flex items-center gap-1.5 font-medium px-2 py-1 rounded-full', status.cls)}>
                        <StatusIcon className="w-3 h-3" />{status.label}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 font-mono text-muted-foreground">#{tx.id}</td>
                    <td className="px-4 py-3.5 font-mono text-muted-foreground">
                      {tx.order_id ? `#${tx.order_id}` : <span className="opacity-40">—</span>}
                    </td>
                    <td className="px-4 py-3.5 text-foreground">
                      <p className="font-medium truncate max-w-[140px]">{tx.user_name || `ID ${tx.user_id}`}</p>
                      {tx.username && <p className="text-muted-foreground text-[10px]">@{tx.username}</p>}
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="uppercase font-semibold text-foreground">{tx.payment_type || '—'}</span>
                    </td>
                    <td className="px-4 py-3.5 text-muted-foreground capitalize">{tx.purpose || '—'}</td>
                    <td className="px-4 py-3.5 font-semibold text-foreground">{fmt(tx.amount_cents)}</td>
                    <td className="px-4 py-3.5 text-muted-foreground font-mono text-[11px]">
                      {tx.external_amount ?? <span className="opacity-40">—</span>}
                    </td>
                    <td className="px-4 py-3.5">
                      {tx.provider_payment_id ? (
                        <div className="flex items-center gap-1">
                          <span className="font-mono text-[10px] text-muted-foreground truncate max-w-[90px]">{tx.provider_payment_id}</span>
                          <button
                            onClick={() => handleCopy(tx.provider_payment_id!, tx.id)}
                            className="w-5 h-5 rounded flex items-center justify-center hover:bg-white/10 transition-colors shrink-0"
                          >
                            <Copy className={cn('w-3 h-3', copied === tx.id ? 'text-neon' : 'text-muted-foreground')} />
                          </button>
                        </div>
                      ) : <span className="opacity-40">—</span>}
                    </td>
                    <td className="px-4 py-3.5 text-muted-foreground whitespace-nowrap">
                      {tx.created_at ? new Date(tx.created_at).toLocaleString('en', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>

          {(filtered.length === 0 || loading) && (
            <div className="text-center py-12 text-muted-foreground">
              <CreditCard className="w-8 h-8 mx-auto mb-2 opacity-30" />
              <p className="text-sm">{loading ? 'Loading payments...' : 'No transactions found'}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
