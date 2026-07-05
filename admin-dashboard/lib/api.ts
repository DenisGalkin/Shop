'use client'

export type I18nText = { en?: string; ru?: string; ua?: string }

export type Category = {
  id: string
  slug: string
  title: string
  premium_emoji_id: string
  sort_order: number
  is_active: boolean
  created_at: string
  products_count?: number
  stock_total?: number
}

export type Product = {
  id: string
  category_id: string
  slug: string
  title: string
  title_i18n: I18nText
  description: string
  description_i18n: I18nText
  important_info: string
  important_info_i18n: I18nText
  price_cents: number
  warranty_label: string
  is_active: boolean
  sort_order: number
  created_at: string
  category: string
  stock: number
  sold: number
  image: string
}

export type User = {
  id: number
  tg_id: number
  username: string | null
  full_name: string
  balance_cents: number
  total_deposited_cents: number
  total_spent_cents: number
  referral_earned_cents: number
  referral_balance_cents: number
  referrer_user_id: number | null
  language_code: string
  is_admin: boolean
  created_at: string
  orders: number
  lastActive: string
  status: 'new' | 'active' | 'inactive' | 'admin'
  avatar: string
}

export type Order = {
  id: number
  user_id: number
  product_id: string
  stock_item_id: number | null
  amount_cents: number
  status: 'pending' | 'completed' | 'failed' | 'refunded'
  payment_method: string
  payment_status: string
  created_at: string
  completed_at: string | null
  user_name: string
  username: string | null
  product_name: string
}

export type Payment = {
  id: number
  user_id: number
  amount_cents: number
  payment_type: string
  status: 'confirmed' | 'pending' | 'failed' | 'refunded'
  currency: string
  purpose: string
  provider_payment_id: string | null
  provider_invoice_id: number | null
  provider_invoice_url: string | null
  provider_status: string
  error_text: string | null
  created_at: string
  processed_at: string | null
  expires_at: string | null
  user_name: string
  username: string | null
  order_id: number | null
  external_amount: string | null
  product_title: string | null
}

export type DashboardData = {
  stats: Record<string, number | string>
  revenueData: Array<{ date: string; revenue: number; orders: number }>
  categoryData: Array<{ name: string; value: number; color: string }>
  weeklyOrders: Array<{ day: string; orders: number }>
  recentOrders: Order[]
  lowStock: Product[]
  outOfStock: Product[]
  hiddenStockedProducts: Product[]
  emptyCategories: Category[]
}

type RevenuePoint = { date: string; revenue: number; orders: number }

export type SessionResponse = {
  ok: true
  authenticated: boolean
  session: { username: string; expires_at: string } | null
}

const chartColors = ['#22d3ee', '#34d399', '#818cf8', '#fbbf24', '#f87171', '#a78bfa']

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function apiFetch<T>(method: 'GET' | 'POST' | 'PATCH' | 'DELETE', path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/admin/api${path}`, {
    method,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  })
  const text = await res.text()
  const json = text ? safeJson(text) : null
  if (!res.ok || json?.ok === false) {
    throw new ApiError(json?.error || text || res.statusText, res.status)
  }
  return json as T
}

function safeJson(text: string): any {
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

const idNum = (id: string | number) => Number(String(id).replace(/^\D+/, ''))

const initials = (name: string, username?: string | null) => {
  const source = name || username || 'U'
  const parts = source.replace('@', '').split(/\s+/).filter(Boolean)
  return parts.slice(0, 2).map((part) => part[0]?.toUpperCase()).join('') || 'U'
}

const dayLabel = (isoDay: string) =>
  new Date(`${isoDay}T00:00:00`).toLocaleDateString('en-US', { day: '2-digit', month: 'short' })

function orderStatus(status: string): Order['status'] {
  if (status === 'completed' || status === 'paid' || status === 'processed') return 'completed'
  if (status === 'failed' || status === 'canceled' || status === 'cancelled' || status === 'expired') return 'failed'
  if (status === 'refunded') return 'refunded'
  return 'pending'
}

function paymentStatus(status: string): Payment['status'] {
  if (status === 'paid' || status === 'completed' || status === 'processed' || status === 'confirmed') return 'confirmed'
  if (status === 'failed' || status === 'canceled' || status === 'cancelled' || status === 'expired') return 'failed'
  if (status === 'refunded') return 'refunded'
  return 'pending'
}

function mapCategory(raw: any): Category {
  return {
    id: String(raw.id),
    slug: raw.slug || String(raw.id),
    title: raw.title || '',
    premium_emoji_id: raw.premium_emoji_id || '',
    sort_order: Number(raw.sort_order || 0),
    is_active: Boolean(raw.is_active),
    created_at: raw.created_at || '',
    products_count: Number(raw.products_count || 0),
    stock_total: Number(raw.stock_total || 0),
  }
}

function mapProduct(raw: any): Product {
  return {
    id: String(raw.id),
    category_id: String(raw.category_id),
    slug: raw.slug || String(raw.id),
    title: raw.title || '',
    title_i18n: raw.title_i18n || {},
    description: raw.description || '',
    description_i18n: raw.description_i18n || {},
    important_info: raw.important_info || '',
    important_info_i18n: raw.important_info_i18n || {},
    price_cents: Number(raw.price_cents || 0),
    warranty_label: raw.warranty_label || '',
    is_active: Boolean(raw.is_active),
    sort_order: Number(raw.sort_order || 0),
    created_at: raw.created_at || '',
    category: raw.category_title || '',
    stock: Number(raw.stock_count || 0),
    sold: Number(raw.sold_count || 0),
    image: '📦',
  }
}

function mapUser(raw: any): User {
  const orders = Number(raw.orders_count || 0)
  return {
    id: Number(raw.id || raw.tg_id),
    tg_id: Number(raw.tg_id || 0),
    username: raw.username || null,
    full_name: raw.full_name || '',
    balance_cents: Number(raw.balance_cents || 0),
    total_deposited_cents: Number(raw.total_deposited_cents || 0),
    total_spent_cents: Number(raw.total_spent_cents || 0),
    referral_earned_cents: Number(raw.referral_earned_cents || 0),
    referral_balance_cents: Number(raw.referral_balance_cents || 0),
    referrer_user_id: raw.referrer_user_id ?? null,
    language_code: raw.language_code || 'ru',
    is_admin: Boolean(raw.is_admin),
    created_at: raw.created_at || '',
    orders,
    lastActive: raw.last_order_at || raw.created_at || '',
    status: raw.is_admin ? 'admin' : orders > 0 ? 'active' : 'new',
    avatar: initials(raw.full_name || '', raw.username),
  }
}

function mapOrder(raw: any): Order {
  return {
    id: Number(raw.id || 0),
    user_id: Number(raw.buyer_tg_id || 0),
    product_id: String(raw.product_id || ''),
    stock_item_id: raw.stock_item_id ?? null,
    amount_cents: Number(raw.amount_cents || 0),
    status: orderStatus(raw.status || ''),
    payment_method: raw.payment_method || '',
    payment_status: raw.payment_status || raw.status || '',
    created_at: raw.created_at || '',
    completed_at: raw.completed_at || null,
    user_name: raw.buyer_name || '',
    username: raw.username || null,
    product_name: raw.product_title || '',
  }
}

function mapPayment(raw: any): Payment {
  return {
    id: Number(raw.id || 0),
    user_id: Number(raw.buyer_tg_id || 0),
    amount_cents: Number(raw.amount_cents || 0),
    payment_type: raw.payment_type || '',
    status: paymentStatus(raw.status || raw.provider_status || ''),
    currency: raw.currency || 'USD',
    purpose: raw.purpose || '',
    provider_payment_id: raw.provider_payment_id || null,
    provider_invoice_id: raw.provider_invoice_id ?? null,
    provider_invoice_url: raw.provider_invoice_url || null,
    provider_status: raw.provider_status || '',
    error_text: raw.error_text || null,
    created_at: raw.created_at || '',
    processed_at: raw.processed_at || null,
    expires_at: raw.expires_at || null,
    user_name: raw.buyer_name || '',
    username: raw.username || null,
    order_id: raw.order_id ?? null,
    external_amount: raw.external_amount || null,
    product_title: raw.product_title || null,
  }
}

function productToPayload(data: Partial<Product>) {
  const title = data.title_i18n?.ru || data.title_i18n?.en || data.title || ''
  const description = data.description_i18n?.ru || data.description_i18n?.en || data.description || ''
  const importantInfo = data.important_info_i18n?.ru || data.important_info_i18n?.en || data.important_info || ''
  return {
    category_id: idNum(data.category_id || 0),
    title,
    title_i18n: data.title_i18n || { ru: title },
    description,
    description_i18n: data.description_i18n || { ru: description },
    important_info: importantInfo,
    important_info_i18n: data.important_info_i18n || { ru: importantInfo },
    price: String((Number(data.price_cents || 0) / 100).toFixed(2)),
    warranty_label: data.warranty_label || '',
    sort_order: Number(data.sort_order || 0),
  }
}

export const session = () => apiFetch<SessionResponse>('GET', '/session')
export const login = (username: string, password: string) => apiFetch<{ ok: true }>('POST', '/login', { username, password })
export const logout = () => apiFetch<{ ok: true }>('POST', '/logout', {})

export async function getCategories(): Promise<Category[]> {
  const res = await apiFetch<{ ok: true; items: any[] }>('GET', '/categories')
  return res.items.map(mapCategory)
}

export async function createCategory(data: Partial<Category>): Promise<Category> {
  const res = await apiFetch<{ ok: true; item: any }>('POST', '/categories', {
    title: data.title || '',
    premium_emoji_id: data.premium_emoji_id || '',
    sort_order: Number(data.sort_order || 0),
  })
  return mapCategory(res.item)
}

export async function updateCategory(id: string, data: Partial<Category>): Promise<Category> {
  const res = await apiFetch<{ ok: true; item: any }>('PATCH', `/categories/${idNum(id)}`, {
    title: data.title || '',
    premium_emoji_id: data.premium_emoji_id || '',
    sort_order: Number(data.sort_order || 0),
  })
  return mapCategory(res.item)
}

export async function toggleCategory(id: string): Promise<Category> {
  const res = await apiFetch<{ ok: true; item: any }>('POST', `/categories/${idNum(id)}/toggle`, {})
  return mapCategory(res.item)
}

export async function deleteCategory(id: string): Promise<void> {
  await apiFetch<{ ok: true }>('DELETE', `/categories/${idNum(id)}`)
}

export async function reorderCategories(ids: string[]): Promise<void> {
  await apiFetch<{ ok: true }>('POST', '/categories/reorder', { ids: ids.map(idNum) })
}

export async function getProducts(): Promise<Product[]> {
  const res = await apiFetch<{ ok: true; items: any[] }>('GET', '/products')
  return res.items.map(mapProduct)
}

export async function createProduct(data: Partial<Product>): Promise<Product> {
  const res = await apiFetch<{ ok: true; item: any }>('POST', '/products', productToPayload(data))
  return mapProduct(res.item)
}

export async function updateProduct(id: string, data: Partial<Product>): Promise<Product> {
  const res = await apiFetch<{ ok: true; item: any }>('PATCH', `/products/${idNum(id)}`, productToPayload(data))
  return mapProduct(res.item)
}

export async function toggleProduct(id: string): Promise<Product> {
  const res = await apiFetch<{ ok: true; item: any }>('POST', `/products/${idNum(id)}/toggle`, {})
  return mapProduct(res.item)
}

export async function deleteProduct(id: string): Promise<void> {
  await apiFetch<{ ok: true }>('DELETE', `/products/${idNum(id)}`)
}

export async function reorderProducts(ids: string[]): Promise<void> {
  await apiFetch<{ ok: true }>('POST', '/products/reorder', { ids: ids.map(idNum) })
}

export async function uploadProductKeys(id: string, keys: string[]): Promise<{ added: number; skipped: number }> {
  const res = await apiFetch<{ ok: true; added: number; skipped: number }>('POST', `/products/${idNum(id)}/stock`, {
    keys: keys.join('\n'),
  })
  return { added: res.added, skipped: res.skipped }
}

export async function getUsers(params?: { search?: string }): Promise<{ users: User[]; total: number }> {
  const qs = params?.search ? `?search=${encodeURIComponent(params.search)}` : ''
  const res = await apiFetch<{ ok: true; items: any[] }>('GET', `/users${qs}`)
  const users = res.items.map(mapUser)
  return { users, total: users.length }
}

export async function adjustUserBalance(tgId: number, delta_cents: number): Promise<{ balance_cents: number }> {
  const res = await apiFetch<{ ok: true; item: any }>('POST', `/users/${tgId}/balance`, {
    amount: String((delta_cents / 100).toFixed(2)),
  })
  return { balance_cents: Number(res.item.balance_cents || 0) }
}

export async function setUserAdmin(id: number, _: boolean): Promise<User> {
  const users = await getUsers()
  const user = users.users.find((item) => item.id === id)
  if (!user) throw new ApiError('User not found', 404)
  return user
}

export async function banUser(_: number): Promise<void> {}

export async function getOrders(): Promise<{ orders: Order[]; total: number }> {
  const res = await apiFetch<{ ok: true; items: any[] }>('GET', '/orders?limit=100')
  const orders = res.items.map(mapOrder)
  return { orders, total: orders.length }
}

export async function updateOrderStatus(id: number, status: Order['status']): Promise<Order> {
  const orders = await getOrders()
  const order = orders.orders.find((item) => item.id === id)
  if (!order) throw new ApiError('Order not found', 404)
  return { ...order, status }
}

export async function refundOrder(id: number): Promise<void> {
  await updateOrderStatus(id, 'refunded')
}

export async function getPayments(): Promise<{ payments: Payment[]; total: number }> {
  const res = await apiFetch<{ ok: true; items: any[] }>('GET', '/payments?limit=100')
  const payments = res.items.map(mapPayment)
  return { payments, total: payments.length }
}

export async function getDashboard(): Promise<DashboardData> {
  const [dashboard, categories] = await Promise.all([
    apiFetch<any>('GET', '/dashboard'),
    getCategories(),
  ])
  const revenueData: RevenuePoint[] = (dashboard.series || []).map((row: any) => ({
    date: dayLabel(row.day),
    revenue: Math.round(Number(row.revenue_cents || 0) / 100),
    orders: Number(row.orders_count || 0),
  }))
  const stockTotal = Math.max(categories.reduce((sum, item) => sum + Number(item.stock_total || 0), 0), 1)
  const categoryData = categories.slice(0, 6).map((category, index) => ({
    name: category.title,
    value: Math.round((Number(category.stock_total || 0) / stockTotal) * 100),
    color: chartColors[index % chartColors.length],
  }))
  const weeklyOrders = revenueData.map((row) => ({ day: row.date, orders: row.orders }))
  return {
    stats: dashboard.stats || {},
    revenueData,
    categoryData,
    weeklyOrders,
    recentOrders: (dashboard.recent_orders || []).map(mapOrder),
    lowStock: (dashboard.low_stock || []).map(mapProduct),
    outOfStock: (dashboard.out_of_stock || []).map(mapProduct),
    hiddenStockedProducts: (dashboard.hidden_stocked_products || []).map(mapProduct),
    emptyCategories: (dashboard.empty_categories || []).map(mapCategory),
  }
}
