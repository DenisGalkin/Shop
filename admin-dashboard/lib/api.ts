'use client'

export type ApiCategory = {
  id: number
  slug: string
  title: string
  premium_emoji_id: string
  sort_order: number
  is_active: boolean
  products_count: number
  active_products_count: number
  stock_total: number
}

export type ApiProduct = {
  id: number
  category_id: number
  category_title: string
  title: string
  title_i18n: Record<string, string>
  description: string
  description_i18n: Record<string, string>
  important_info: string
  important_info_i18n: Record<string, string>
  price_cents: number
  price_label: string
  warranty_label: string
  sort_order: number
  stock_count: number
  sold_count: number
  is_active: boolean
}

export type ApiUser = {
  id: number
  tg_id: number
  username: string
  full_name: string
  balance_cents: number
  balance_label: string
  total_deposited_cents: number
  total_deposited_label: string
  total_spent_cents: number
  total_spent_label: string
  orders_count: number
  referral_balance_cents: number
  referral_balance_label: string
  created_at: string
  created_label: string
  is_admin: boolean
}

export type ApiOrder = {
  id: number
  product_title: string
  buyer_name: string
  buyer_tg_id: number
  amount_cents: number
  amount_label: string
  status: string
  payment_method: string
  created_at: string
  created_label: string
}

export type ApiPayment = {
  id: number
  buyer_name: string
  buyer_tg_id: number
  amount_cents: number
  amount_label: string
  currency: string
  status: string
  purpose: string
  product_title?: string | null
  payment_type: string
  provider_status: string
  provider_payment_id?: string | null
  provider_invoice_id?: number | null
  provider_invoice_url?: string | null
  created_at: string
  created_label: string
}

export type ApiStockItem = {
  id: number
  product_id: number
  key_value: string
  status: string
  order_id?: number | null
  reserved_payment_id?: string | null
  reserved_until?: string | null
  reserved_until_label: string
  created_at: string
  created_label: string
  sold_at?: string | null
  sold_label: string
  can_delete: boolean
}

export type DashboardData = {
  stats: Record<string, number | string>
  series: Array<{ day: string; orders_count: number; revenue_cents: number; revenue_label: string }>
  recent_orders: ApiOrder[]
  recent_payments: ApiPayment[]
  active_buyers: Array<{
    id: number
    tg_id: number
    username: string
    full_name: string
    orders_count: number
    total_spent_cents: number
    total_spent_label: string
    last_order_at?: string | null
    last_order_label: string
  }>
  low_stock: ApiProduct[]
  out_of_stock: ApiProduct[]
  hidden_stocked_products: ApiProduct[]
  empty_categories: ApiCategory[]
}

export type AdminData = {
  dashboard: DashboardData
  categories: ApiCategory[]
  products: ApiProduct[]
  users: ApiUser[]
  orders: ApiOrder[]
  payments: ApiPayment[]
}

export type ProductPayload = {
  category_id: number
  title: string
  title_i18n?: Record<string, string>
  description: string
  description_i18n?: Record<string, string>
  important_info: string
  important_info_i18n?: Record<string, string>
  price: string
  warranty_label: string
  sort_order: number
}

export type CategoryPayload = {
  title: string
  premium_emoji_id?: string
  sort_order: number
}

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/admin/api${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers || {}),
    },
  })
  const contentType = response.headers.get('content-type') || ''
  const body = contentType.includes('application/json') ? await response.json() : null
  if (!response.ok || body?.ok === false) {
    throw new ApiError(body?.error || response.statusText || 'API error', response.status)
  }
  return body as T
}

export const api = {
  session: () => request<{ ok: true; authenticated: boolean; session: { username: string; expires_at: string } | null }>('/session'),
  login: (username: string, password: string) =>
    request<{ ok: true }>('/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  logout: () => request<{ ok: true }>('/logout', { method: 'POST', body: JSON.stringify({}) }),
  dashboard: () => request<{ ok: true } & DashboardData>('/dashboard'),
  categories: () => request<{ ok: true; items: ApiCategory[] }>('/categories'),
  createCategory: (payload: CategoryPayload) =>
    request<{ ok: true; item: ApiCategory }>('/categories', { method: 'POST', body: JSON.stringify(payload) }),
  updateCategory: (id: number, payload: CategoryPayload) =>
    request<{ ok: true; item: ApiCategory }>(`/categories/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  toggleCategory: (id: number) =>
    request<{ ok: true; item: ApiCategory }>(`/categories/${id}/toggle`, { method: 'POST', body: JSON.stringify({}) }),
  products: () => request<{ ok: true; items: ApiProduct[]; categories: ApiCategory[] }>('/products'),
  createProduct: (payload: ProductPayload) =>
    request<{ ok: true; item: ApiProduct }>('/products', { method: 'POST', body: JSON.stringify(payload) }),
  updateProduct: (id: number, payload: ProductPayload) =>
    request<{ ok: true; item: ApiProduct }>(`/products/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  toggleProduct: (id: number) =>
    request<{ ok: true; item: ApiProduct }>(`/products/${id}/toggle`, { method: 'POST', body: JSON.stringify({}) }),
  addStock: (productId: number, keys: string) =>
    request<{ ok: true; added: number; skipped: number; item: ApiProduct }>(`/products/${productId}/stock`, {
      method: 'POST',
      body: JSON.stringify({ keys }),
    }),
  stockItems: (productId: number) =>
    request<{ ok: true; product: ApiProduct; items: ApiStockItem[] }>(`/products/${productId}/stock-items`),
  deleteStockItem: (productId: number, stockItemId: number) =>
    request<{ ok: true; item: ApiProduct }>(`/products/${productId}/stock-items/${stockItemId}`, { method: 'DELETE' }),
  users: (search = '') => request<{ ok: true; items: ApiUser[] }>(`/users${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  addBalance: (tgId: number, amount: string) =>
    request<{ ok: true; item: ApiUser; amount_label: string }>(`/users/${tgId}/balance`, {
      method: 'POST',
      body: JSON.stringify({ amount }),
    }),
  orders: (limit = 100) => request<{ ok: true; items: ApiOrder[] }>(`/orders?limit=${limit}`),
  payments: (limit = 100) => request<{ ok: true; items: ApiPayment[] }>(`/payments?limit=${limit}`),
}

export async function loadAdminData(): Promise<AdminData> {
  const [dashboard, products, users, orders, payments] = await Promise.all([
    api.dashboard(),
    api.products(),
    api.users(),
    api.orders(),
    api.payments(),
  ])
  return {
    dashboard,
    categories: products.categories,
    products: products.items,
    users: users.items,
    orders: orders.items,
    payments: payments.items,
  }
}

export const moneyFromCents = (value: number) => `$ ${(value / 100).toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

export const dayLabel = (isoDay: string) =>
  new Date(`${isoDay}T00:00:00`).toLocaleDateString('ru-RU', { day: '2-digit', month: 'short' })

export const initials = (name: string, username = '') => {
  const source = name.trim() || username.trim() || 'AD'
  const words = source.replace('@', '').split(/\s+/).filter(Boolean)
  return words.slice(0, 2).map((word) => word[0]?.toUpperCase()).join('') || 'U'
}
