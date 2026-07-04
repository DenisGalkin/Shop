'use client'

import { useMemo, useState } from 'react'
import { CreditCard, CheckCircle2, Clock, XCircle, RotateCcw, Search, TrendingUp, Copy, ExternalLink } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { dayLabel, moneyFromCents, type AdminData, type ApiPayment } from '@/lib/api'
import { cn } from '@/lib/utils'

const normalizeStatus = (status: string): 'confirmed' | 'pending' | 'failed' | 'refunded' => {
  if (status === 'paid' || status === 'completed' || status === 'processed') return 'confirmed'
  if (status === 'failed' || status === 'canceled' || status === 'cancelled' || status === 'expired') return 'failed'
  if (status === 'refunded') return 'refunded'
  return 'pending'
}

const statusConfig = {
  confirmed: { label: 'Подтверждён', cls: 'bg-emerald-400/10 text-emerald-400', icon: CheckCircle2 },
  pending: { label: 'Ожидание', cls: 'bg-amber-400/10 text-amber-400', icon: Clock },
  failed: { label: 'Ошибка', cls: 'bg-red-400/10 text-red-400', icon: XCircle },
  refunded: { label: 'Возврат', cls: 'bg-indigo-400/10 text-indigo-400', icon: RotateCcw },
}

function groupByProvider(payments: ApiPayment[]) {
  const grouped = new Map<string, number>()
  for (const payment of payments) {
    grouped.set(payment.payment_type, (grouped.get(payment.payment_type) || 0) + payment.amount_cents)
  }
  return Array.from(grouped.entries()).sort((a, b) => b[1] - a[1]).slice(0, 3)
}

export default function PaymentsTab({ data }: { data: AdminData }) {
  const [search, setSearch] = useState('')
  const [copied, setCopied] = useState<string | null>(null)

  const handleCopy = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text)
    setCopied(id)
    setTimeout(() => setCopied(null), 1500)
  }

  const filtered = useMemo(() => data.payments.filter((payment) => {
    const q = search.toLowerCase()
    return (
      String(payment.id).includes(q) ||
      payment.buyer_name.toLowerCase().includes(q) ||
      String(payment.buyer_tg_id).includes(q) ||
      String(payment.provider_payment_id || payment.provider_invoice_id || '').toLowerCase().includes(q)
    )
  }), [data.payments, search])

  const monthlyFlow = data.dashboard.series.map((row) => ({
    date: dayLabel(row.day),
    revenue: row.revenue_cents,
  }))

  const providerCards = groupByProvider(data.payments)
  const palette = [
    { symbol: '$', cls: 'border-blue-400/20 bg-blue-400/5', accentCls: 'text-blue-400' },
    { symbol: '#', cls: 'border-emerald-400/20 bg-emerald-400/5', accentCls: 'text-emerald-400' },
    { symbol: '*', cls: 'border-amber-400/20 bg-amber-400/5', accentCls: 'text-amber-400' },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Платежи</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Финансовые операции и статусы провайдеров</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 stagger">
        {(providerCards.length ? providerCards : [['payments', 0] as [string, number]]).map(([provider, amount], index) => {
          const style = palette[index % palette.length]
          return (
            <div key={provider} className={cn('rounded-2xl border p-5 transition-all hover:border-white/20', style.cls)}>
              <div className="flex items-start justify-between mb-3">
                <div className={cn('text-2xl font-bold', style.accentCls)}>{style.symbol}</div>
                <span className="text-xs font-medium text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-full flex items-center gap-1">
                  <TrendingUp className="w-3 h-3" />
                  live
                </span>
              </div>
              <p className={cn('text-xl font-bold', style.accentCls)}>{moneyFromCents(amount)}</p>
              <p className="text-xs text-muted-foreground mt-1">Поступления в выборке</p>
              <p className="text-sm font-medium text-foreground mt-0.5">{provider}</p>
            </div>
          )
        })}
      </div>

      <div className="rounded-2xl bg-card border border-border p-5">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="text-sm font-semibold text-foreground">Поступления по дням</h3>
            <p className="text-xs text-muted-foreground">По завершенным заказам</p>
          </div>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-neon" />Выручка</span>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={monthlyFlow} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="oklch(1 0 0 / 5%)" />
            <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'oklch(0.55 0.01 264)' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 10, fill: 'oklch(0.55 0.01 264)' }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ background: 'oklch(0.13 0.008 264)', border: '1px solid oklch(1 0 0 / 8%)', borderRadius: '10px', fontSize: '12px', color: 'oklch(0.95 0.005 264)' }} formatter={(v: number) => moneyFromCents(v)} />
            <Area type="monotone" dataKey="revenue" stroke="oklch(0.72 0.18 195)" strokeWidth={2} fill="oklch(0.72 0.18 195 / 20%)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="rounded-2xl bg-card border border-border overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h3 className="text-sm font-semibold text-foreground">Транзакции</h3>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
            <input type="text" placeholder="Поиск..." value={search} onChange={(e) => setSearch(e.target.value)} className="bg-surface-raised border border-border rounded-lg pl-8 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-neon/30 w-48" />
          </div>
        </div>

        <div className="grid grid-cols-[auto_1fr_1fr_1fr_1fr_auto] gap-4 px-5 py-3 border-b border-border text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          <span>Статус</span><span>ID</span><span>Пользователь</span><span>Метод</span><span>Сумма</span><span>Провайдер</span>
        </div>

        <div className="divide-y divide-border">
          {filtered.map((tx) => {
            const status = statusConfig[normalizeStatus(tx.status)]
            const StatusIcon = status.icon
            const providerId = String(tx.provider_payment_id || tx.provider_invoice_id || '')
            return (
              <div key={tx.id} className="grid grid-cols-[auto_1fr_1fr_1fr_1fr_auto] gap-4 px-5 py-3.5 items-center hover:bg-white/[0.02] transition-colors">
                <span className={cn('flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-full', status.cls)}>
                  <StatusIcon className="w-3 h-3" />
                  {status.label}
                </span>
                <span className="font-mono text-xs text-muted-foreground">#{tx.id}</span>
                <span className="text-xs text-foreground">{tx.buyer_name}</span>
                <span className="text-xs font-medium text-foreground">{tx.payment_type}</span>
                <div>
                  <p className="text-xs font-semibold text-foreground">{tx.amount_label}</p>
                  <p className="text-[10px] text-muted-foreground">{tx.purpose}</p>
                </div>
                <div className="flex items-center gap-1 justify-end">
                  {providerId ? (
                    <>
                      <span className="font-mono text-[10px] text-muted-foreground max-w-24 truncate">{providerId}</span>
                      <button onClick={() => handleCopy(providerId, String(tx.id))} className="w-6 h-6 rounded flex items-center justify-center hover:bg-white/10 transition-colors" title="Копировать">
                        <Copy className={cn('w-3 h-3 transition-colors', copied === String(tx.id) ? 'text-neon' : 'text-muted-foreground')} />
                      </button>
                    </>
                  ) : <span className="text-[10px] text-muted-foreground">-</span>}
                  {tx.provider_invoice_url && (
                    <a href={tx.provider_invoice_url} target="_blank" rel="noopener noreferrer" className="w-6 h-6 rounded flex items-center justify-center hover:bg-white/10 transition-colors" title="Открыть invoice">
                      <ExternalLink className="w-3 h-3 text-muted-foreground" />
                    </a>
                  )}
                </div>
              </div>
            )
          })}
          {filtered.length === 0 && <div className="px-5 py-12 text-center text-sm text-muted-foreground">Платежи не найдены</div>}
        </div>
      </div>
    </div>
  )
}
