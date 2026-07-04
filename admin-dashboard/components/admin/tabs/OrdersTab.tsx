'use client'

import { useEffect, useMemo, useState } from 'react'
import {
  ShoppingCart, CheckCircle2, Clock, XCircle, RotateCcw,
  Search, Download, ChevronRight,
} from 'lucide-react'
import { getOrders, type Order } from '@/lib/api'
import { cn } from '@/lib/utils'

const fmt = (cents: number) => `$${(cents / 100).toFixed(2)}`

const statusConfig: Record<Order['status'], { label: string; cls: string; icon: React.ElementType; dot: string }> = {
  completed: { label: 'Completed', cls: 'bg-emerald-400/10 text-emerald-400 border-emerald-400/20', icon: CheckCircle2, dot: 'bg-emerald-400' },
  pending: { label: 'Pending', cls: 'bg-amber-400/10 text-amber-400 border-amber-400/20', icon: Clock, dot: 'bg-amber-400' },
  failed: { label: 'Failed', cls: 'bg-red-400/10 text-red-400 border-red-400/20', icon: XCircle, dot: 'bg-red-400' },
  refunded: { label: 'Refunded', cls: 'bg-indigo-400/10 text-indigo-400 border-indigo-400/20', icon: RotateCcw, dot: 'bg-indigo-400' },
}

const methodCls: Record<string, string> = {
  TON: 'text-blue-400 bg-blue-400/10',
  Stars: 'text-amber-400 bg-amber-400/10',
  USDT: 'text-emerald-400 bg-emerald-400/10',
  balance: 'text-neon bg-neon/10',
}

function exportCsv(data: Order[]) {
  const headers = ['id', 'user_id', 'user_name', 'username', 'product_id', 'product_name', 'stock_item_id', 'amount_cents', 'amount_usd', 'status', 'payment_method', 'payment_status', 'created_at', 'completed_at']
  const rows = data.map((o) => [
    o.id, o.user_id, `"${o.user_name}"`, o.username ?? '', o.product_id, `"${o.product_name}"`,
    o.stock_item_id ?? '', o.amount_cents, (o.amount_cents / 100).toFixed(2),
    o.status, o.payment_method, o.payment_status,
    o.created_at, o.completed_at ?? '',
  ])
  const csv = [headers, ...rows].map((r) => r.join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `orders_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

type StatusFilter = 'all' | Order['status']

export default function OrdersTab() {
  const [orders, setOrders] = useState<Order[]>([])
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [expanded, setExpanded] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    setLoading(true)
    getOrders()
      .then((res) => {
        if (!alive) return
        setOrders(res.orders)
        setError(null)
      })
      .catch((err) => alive && setError(err instanceof Error ? err.message : 'Failed to load orders'))
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
  }, [])

  const filtered = useMemo(() => orders.filter((o) => {
    const q = search.toLowerCase()
    const matchSearch =
      String(o.id).includes(q) ||
      o.user_name.toLowerCase().includes(q) ||
      (o.username ?? '').toLowerCase().includes(q) ||
      o.product_name.toLowerCase().includes(q)
    const matchStatus = statusFilter === 'all' || o.status === statusFilter
    return matchSearch && matchStatus
  }), [orders, search, statusFilter])

  const kpis = useMemo(() => {
    const total = orders.length
    const completed = orders.filter((o) => o.status === 'completed').length
    const pending = orders.filter((o) => o.status === 'pending').length
    const refunded = orders.filter((o) => o.status === 'refunded').length
    return [
      { label: 'Total orders', value: String(total), sub: 'loaded from API', color: 'text-neon' },
      { label: 'Completed', value: String(completed), sub: total ? `${Math.round((completed / total) * 100)}%` : '0%', color: 'text-emerald-400' },
      { label: 'Pending', value: String(pending), sub: 'in queue', color: 'text-amber-400' },
      { label: 'Refunded', value: String(refunded), sub: total ? `${Math.round((refunded / total) * 100)}%` : '0%', color: 'text-indigo-400' },
    ]
  }, [orders])

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Заказы</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Orders and delivery status</p>
        </div>
        <button
          onClick={() => exportCsv(filtered)}
          disabled={filtered.length === 0}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-card border border-border text-muted-foreground text-sm hover:text-foreground hover:border-white/15 transition-all disabled:opacity-40 disabled:pointer-events-none"
        >
          <Download className="w-4 h-4" />
          Export CSV
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 stagger">
        {kpis.map((k) => (
          <div key={k.label} className="rounded-2xl bg-card border border-border p-4">
            <p className={cn('text-2xl font-bold', k.color)}>{k.value}</p>
            <p className="text-sm text-foreground mt-0.5">{k.label}</p>
            <p className="text-xs text-muted-foreground">{k.sub}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Order ID, user or product..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-card border border-border rounded-xl pl-9 pr-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-neon/30 focus:border-neon/40 transition-all"
          />
        </div>
        <div className="flex items-center gap-1 p-1 rounded-xl bg-card border border-border overflow-x-auto">
          {(['all', 'completed', 'pending', 'failed', 'refunded'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all',
                statusFilter === s ? 'bg-neon/15 text-neon' : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {s === 'all' ? 'All' : statusConfig[s].label}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        {filtered.map((order) => {
          const status = statusConfig[order.status]
          const StatusIcon = status.icon
          const isExpanded = expanded === order.id
          const mCls = methodCls[order.payment_method] ?? 'text-muted-foreground bg-white/5'

          return (
            <div key={order.id} className="rounded-2xl bg-card border border-border overflow-hidden transition-all duration-200 hover:border-white/12">
              <div
                className="flex items-center gap-4 px-5 py-4 cursor-pointer"
                onClick={() => setExpanded(isExpanded ? null : order.id)}
              >
                <div className={cn('w-2 h-2 rounded-full shrink-0', status.dot)} />
                <span className="font-mono text-xs font-semibold text-muted-foreground w-16 shrink-0">
                  #{order.id}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">{order.product_name || 'Order'}</p>
                  <p className="text-xs text-muted-foreground">
                    {order.username ? `@${order.username}` : order.user_name || `ID ${order.user_id}`} · {order.created_at ? new Date(order.created_at).toLocaleString('en', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}
                  </p>
                </div>
                <span className={cn('text-[11px] font-medium px-2 py-0.5 rounded-full hidden sm:inline-flex', mCls)}>
                  {order.payment_method || '—'}
                </span>
                <span className="text-sm font-bold text-foreground shrink-0">{fmt(order.amount_cents)}</span>
                <span className={cn('flex items-center gap-1 text-[11px] font-medium px-2 py-1 rounded-full border shrink-0 hidden md:flex', status.cls)}>
                  <StatusIcon className="w-3 h-3" />
                  {status.label}
                </span>
                <ChevronRight className={cn('w-4 h-4 text-muted-foreground transition-transform shrink-0', isExpanded && 'rotate-90')} />
              </div>

              {isExpanded && (
                <div className="px-5 pb-4 pt-0 border-t border-border animate-fade-in">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-3">
                    {[
                      { label: 'Order ID', value: `#${order.id}` },
                      { label: 'User ID', value: String(order.user_id) },
                      { label: 'User', value: order.user_name || '—' },
                      { label: 'Username', value: order.username ? `@${order.username}` : '—' },
                      { label: 'Product', value: order.product_name || '—' },
                      { label: 'Stock item ID', value: order.stock_item_id ? String(order.stock_item_id) : '—' },
                      { label: 'Amount', value: fmt(order.amount_cents) },
                      { label: 'Payment method', value: order.payment_method || '—' },
                      { label: 'Payment status', value: order.payment_status || '—' },
                      { label: 'Created', value: order.created_at ? new Date(order.created_at).toLocaleString('en') : '—' },
                      { label: 'Completed', value: order.completed_at ? new Date(order.completed_at).toLocaleString('en') : '—' },
                    ].map((d) => (
                      <div key={d.label}>
                        <p className="text-[10px] text-muted-foreground uppercase tracking-wide">{d.label}</p>
                        <p className="text-xs font-medium text-foreground mt-0.5 break-all">{d.value}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {(filtered.length === 0 || loading) && (
        <div className="text-center py-16 text-muted-foreground">
          <ShoppingCart className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm">{loading ? 'Loading orders...' : 'No orders found'}</p>
        </div>
      )}
    </div>
  )
}
