'use client'

import { useMemo, useState } from 'react'
import { ShoppingCart, CheckCircle2, Clock, XCircle, RotateCcw, Search, Download, ChevronRight, ExternalLink } from 'lucide-react'
import type { AdminData, ApiOrder } from '@/lib/api'
import { cn } from '@/lib/utils'

const normalizeStatus = (status: string): 'completed' | 'pending' | 'failed' | 'refunded' => {
  if (status === 'completed' || status === 'paid') return 'completed'
  if (status === 'failed' || status === 'canceled' || status === 'cancelled') return 'failed'
  if (status === 'refunded') return 'refunded'
  return 'pending'
}

const statusConfig = {
  completed: { label: 'Выполнен', cls: 'bg-emerald-400/10 text-emerald-400 border-emerald-400/20', icon: CheckCircle2, dot: 'bg-emerald-400' },
  pending: { label: 'В обработке', cls: 'bg-amber-400/10 text-amber-400 border-amber-400/20', icon: Clock, dot: 'bg-amber-400' },
  failed: { label: 'Ошибка', cls: 'bg-red-400/10 text-red-400 border-red-400/20', icon: XCircle, dot: 'bg-red-400' },
  refunded: { label: 'Возврат', cls: 'bg-indigo-400/10 text-indigo-400 border-indigo-400/20', icon: RotateCcw, dot: 'bg-indigo-400' },
}

function exportCsv(orders: ApiOrder[]) {
  const rows = [
    ['id', 'product', 'buyer', 'telegram_id', 'amount', 'status', 'payment_method', 'created_at'],
    ...orders.map((order) => [order.id, order.product_title, order.buyer_name, order.buyer_tg_id, order.amount_label, order.status, order.payment_method, order.created_at]),
  ]
  const csv = rows.map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'shop-orders.csv'
  link.click()
  URL.revokeObjectURL(url)
}

export default function OrdersTab({ data }: { data: AdminData }) {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'completed' | 'pending' | 'failed' | 'refunded'>('all')
  const [expanded, setExpanded] = useState<number | null>(null)

  const filtered = useMemo(() => data.orders.filter((order) => {
    const q = search.toLowerCase()
    const matchSearch =
      String(order.id).includes(q) ||
      order.buyer_name.toLowerCase().includes(q) ||
      String(order.buyer_tg_id).includes(q) ||
      order.product_title.toLowerCase().includes(q)
    const matchStatus = statusFilter === 'all' || normalizeStatus(order.status) === statusFilter
    return matchSearch && matchStatus
  }), [data.orders, search, statusFilter])

  const kpis = [
    { label: 'Всего заказов', value: data.orders.length.toLocaleString('ru-RU'), sub: 'в выборке', color: 'text-neon' },
    { label: 'Выполнено', value: data.orders.filter((order) => normalizeStatus(order.status) === 'completed').length.toLocaleString('ru-RU'), sub: 'успешные', color: 'text-emerald-400' },
    { label: 'Ожидают', value: data.orders.filter((order) => normalizeStatus(order.status) === 'pending').length.toLocaleString('ru-RU'), sub: 'в очереди', color: 'text-amber-400' },
    { label: 'Ошибки', value: data.orders.filter((order) => normalizeStatus(order.status) === 'failed').length.toLocaleString('ru-RU'), sub: 'не завершены', color: 'text-red-400' },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Заказы</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Все транзакции и статусы доставки</p>
        </div>
        <button onClick={() => exportCsv(filtered)} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-card border border-border text-muted-foreground text-sm hover:text-foreground hover:border-white/15 transition-all">
          <Download className="w-4 h-4" />
          Экспорт CSV
        </button>
      </div>

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
          <input type="text" placeholder="ID заказа, пользователь или товар..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full bg-card border border-border rounded-xl pl-9 pr-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-neon/30 focus:border-neon/40 transition-all" />
        </div>
        <div className="flex items-center gap-1 p-1 rounded-xl bg-card border border-border overflow-x-auto">
          {(['all', 'completed', 'pending', 'failed', 'refunded'] as const).map((s) => (
            <button key={s} onClick={() => setStatusFilter(s)} className={cn('px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all', statusFilter === s ? 'bg-neon/15 text-neon' : 'text-muted-foreground hover:text-foreground')}>
              {s === 'all' ? 'Все' : s === 'completed' ? 'Выполнены' : s === 'pending' ? 'Ожидают' : s === 'failed' ? 'Ошибки' : 'Возвраты'}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        {filtered.map((order) => {
          const statusKey = normalizeStatus(order.status)
          const status = statusConfig[statusKey]
          const StatusIcon = status.icon
          const isExpanded = expanded === order.id

          return (
            <div key={order.id} className="rounded-2xl bg-card border border-border overflow-hidden transition-all duration-200 hover:border-white/12">
              <div className="flex items-center gap-4 px-5 py-4 cursor-pointer" onClick={() => setExpanded(isExpanded ? null : order.id)}>
                <div className={cn('w-2 h-2 rounded-full shrink-0', status.dot)} />
                <span className="font-mono text-xs font-semibold text-muted-foreground w-24 shrink-0">#{order.id}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">{order.product_title}</p>
                  <p className="text-xs text-muted-foreground">{order.buyer_name} · {order.created_label}</p>
                </div>
                <span className="text-[11px] font-medium px-2 py-0.5 rounded-full hidden sm:inline-flex text-blue-400 bg-blue-400/10">{order.payment_method}</span>
                <span className="text-sm font-bold text-foreground shrink-0">{order.amount_label}</span>
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
                      { label: 'Пользователь', value: order.buyer_name },
                      { label: 'Telegram ID', value: order.buyer_tg_id },
                      { label: 'Способ оплаты', value: order.payment_method },
                      { label: 'Статус', value: order.status },
                    ].map((d) => (
                      <div key={d.label}>
                        <p className="text-[10px] text-muted-foreground uppercase tracking-wide">{d.label}</p>
                        <p className="text-sm font-medium text-foreground mt-0.5">{d.value}</p>
                      </div>
                    ))}
                  </div>
                  <div className="flex gap-2 mt-4">
                    <a href={`tg://user?id=${order.buyer_tg_id}`} className="px-3 py-1.5 rounded-lg bg-card border border-border text-muted-foreground text-xs font-medium hover:text-foreground transition-colors ml-auto flex items-center gap-1">
                      <ExternalLink className="w-3 h-3" />
                      Открыть Telegram
                    </a>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-16 text-muted-foreground">
          <ShoppingCart className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm">Заказы не найдены</p>
        </div>
      )}
    </div>
  )
}
