'use client'

import {
  TrendingUp,
  TrendingDown,
  ShoppingCart,
  Users,
  CreditCard,
  Package,
  ArrowUpRight,
  Zap,
} from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import type { TabId } from '../Sidebar'
import { dayLabel, initials, moneyFromCents, type AdminData } from '@/lib/api'

const chartColors = ['#22d3ee', '#34d399', '#818cf8', '#fbbf24', '#f87171', '#a78bfa']

const statusLabel = (status: string) => {
  if (status === 'completed' || status === 'paid') return 'Выполнен'
  if (status === 'pending') return 'Ожидание'
  if (status === 'failed' || status === 'canceled') return 'Ошибка'
  return status
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-card border border-border rounded-xl px-4 py-3 shadow-xl">
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      {payload.map((entry: any) => (
        <p key={entry.name} className="text-sm font-semibold" style={{ color: entry.color }}>
          {entry.name === 'revenue' ? moneyFromCents(Number(entry.value)) : `${entry.value} заказов`}
        </p>
      ))}
    </div>
  )
}

export default function OverviewTab({ data, onOpenTab }: { data: AdminData; onOpenTab: (tab: TabId) => void }) {
  const stats = data.dashboard.stats
  const series = data.dashboard.series.map((row) => ({
    date: dayLabel(row.day),
    revenue: row.revenue_cents,
    orders: row.orders_count,
  }))
  const categoryTotal = Math.max(data.categories.reduce((sum, category) => sum + category.stock_total, 0), 1)
  const categoryData = data.categories.slice(0, 6).map((category, index) => ({
    name: category.title,
    value: Math.round((category.stock_total / categoryTotal) * 100),
    color: chartColors[index % chartColors.length],
  }))
  const kpis = [
    {
      label: 'Выручка всего',
      value: String(stats.revenue_label || moneyFromCents(Number(stats.revenue_total || 0))),
      change: String(stats.revenue_today_label || moneyFromCents(Number(stats.revenue_today || 0))),
      up: true,
      icon: CreditCard,
      color: 'text-neon',
      bg: 'bg-neon/10',
      border: 'border-neon/20',
    },
    {
      label: 'Заказов',
      value: Number(stats.orders_total || 0).toLocaleString('ru-RU'),
      change: `${Number(stats.orders_today || 0)} сегодня`,
      up: true,
      icon: ShoppingCart,
      color: 'text-emerald-400',
      bg: 'bg-emerald-400/10',
      border: 'border-emerald-400/20',
    },
    {
      label: 'Пользователей',
      value: Number(stats.users_total || 0).toLocaleString('ru-RU'),
      change: `${Number(stats.users_today || 0)} сегодня`,
      up: true,
      icon: Users,
      color: 'text-indigo-400',
      bg: 'bg-indigo-400/10',
      border: 'border-indigo-400/20',
    },
    {
      label: 'Товаров',
      value: Number(stats.products_total || data.products.length).toLocaleString('ru-RU'),
      change: `${Number(stats.products_without_keys_total || 0)} без ключей`,
      up: Number(stats.products_without_keys_total || 0) === 0,
      icon: Package,
      color: 'text-amber-400',
      bg: 'bg-amber-400/10',
      border: 'border-amber-400/20',
    },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Обзор</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Реальная статистика магазина</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-neon/10 border border-neon/25 text-neon text-xs font-medium">
          <Zap className="w-3.5 h-3.5" />
          Live данные
        </div>
      </div>

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 stagger">
        {kpis.map((kpi) => {
          const Icon = kpi.icon
          return (
            <div key={kpi.label} className="rounded-2xl bg-card border border-border p-5 hover:border-white/15 transition-all duration-300 group">
              <div className="flex items-start justify-between mb-4">
                <div className={`w-10 h-10 rounded-xl ${kpi.bg} border ${kpi.border} flex items-center justify-center`}>
                  <Icon className={`w-5 h-5 ${kpi.color}`} />
                </div>
                <span className={`flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${kpi.up ? 'text-emerald-400 bg-emerald-400/10' : 'text-red-400 bg-red-400/10'}`}>
                  {kpi.up ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                  {kpi.change}
                </span>
              </div>
              <p className="text-2xl font-bold text-foreground tracking-tight">{kpi.value}</p>
              <p className="text-xs text-muted-foreground mt-1">{kpi.label}</p>
            </div>
          )
        })}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2 rounded-2xl bg-card border border-border p-5">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Выручка & заказы</h3>
              <p className="text-xs text-muted-foreground">За последние 7 дней</p>
            </div>
            <ArrowUpRight className="w-4 h-4 text-neon" />
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={series} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="oklch(1 0 0 / 5%)" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'oklch(0.55 0.01 264)' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: 'oklch(0.55 0.01 264)' }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="revenue" name="revenue" stroke="oklch(0.72 0.18 195)" strokeWidth={2} fill="oklch(0.72 0.18 195 / 18%)" />
              <Area type="monotone" dataKey="orders" name="orders" stroke="oklch(0.65 0.16 155)" strokeWidth={2} fill="oklch(0.65 0.16 155 / 14%)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-2xl bg-card border border-border p-5">
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-foreground">По категориям</h3>
            <p className="text-xs text-muted-foreground">Доля ключей на складе</p>
          </div>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie data={categoryData} cx="50%" cy="50%" innerRadius={50} outerRadius={75} paddingAngle={3} dataKey="value" strokeWidth={0}>
                {categoryData.map((entry) => <Cell key={entry.name} fill={entry.color} opacity={0.9} />)}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="w-full space-y-1.5 mt-2">
            {categoryData.map((cat) => (
              <div key={cat.name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="w-2 h-2 rounded-full shrink-0" style={{ background: cat.color }} />
                  <span className="text-muted-foreground truncate">{cat.name}</span>
                </div>
                <span className="font-medium text-foreground">{cat.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="rounded-2xl bg-card border border-border p-5">
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-foreground">Заказы по дням</h3>
            <p className="text-xs text-muted-foreground">Текущая неделя</p>
          </div>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={series} barSize={20} margin={{ top: 0, right: 0, left: -30, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="oklch(1 0 0 / 5%)" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'oklch(0.55 0.01 264)' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: 'oklch(0.55 0.01 264)' }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: 'oklch(0.13 0.008 264)', border: '1px solid oklch(1 0 0 / 8%)', borderRadius: '10px', fontSize: '12px', color: 'oklch(0.95 0.005 264)' }} />
              <Bar dataKey="orders" fill="oklch(0.72 0.18 195)" radius={[6, 6, 0, 0]} opacity={0.85} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="xl:col-span-2 rounded-2xl bg-card border border-border p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-foreground">Последние заказы</h3>
            <button onClick={() => onOpenTab('orders')} className="text-xs text-neon cursor-pointer hover:underline">Все заказы</button>
          </div>
          <div className="space-y-2">
            {data.dashboard.recent_orders.slice(0, 5).map((order) => (
              <div key={order.id} className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/5 transition-colors">
                <div className="w-8 h-8 rounded-lg bg-surface-raised flex items-center justify-center text-xs font-bold text-muted-foreground shrink-0">
                  {initials(order.buyer_name)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-foreground truncate">{order.product_title}</p>
                  <p className="text-[10px] text-muted-foreground">{order.buyer_name} · {order.created_label}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-xs font-semibold text-foreground">{order.amount_label}</p>
                  <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-emerald-400/10 text-emerald-400">
                    {statusLabel(order.status)}
                  </span>
                </div>
              </div>
            ))}
            {data.dashboard.recent_orders.length === 0 && <p className="text-sm text-muted-foreground py-6 text-center">Заказов пока нет</p>}
          </div>
        </div>
      </div>
    </div>
  )
}
