'use client'

import { useEffect, useMemo, useState } from 'react'
import type React from 'react'
import { Search, Plus, Filter, Package, AlertTriangle, XCircle, Edit2, Trash2, MoreHorizontal, X } from 'lucide-react'
import { api, type AdminData, type ApiProduct, type ApiStockItem, type CategoryPayload, type ProductPayload } from '@/lib/api'
import { cn } from '@/lib/utils'

type StatusFilter = 'all' | 'active' | 'low_stock' | 'out_of_stock'

const emptyProduct = (categoryId = 0): ProductPayload => ({
  category_id: categoryId,
  title: '',
  title_i18n: {},
  description: '',
  description_i18n: {},
  important_info: '',
  important_info_i18n: {},
  price: '0',
  warranty_label: '',
  sort_order: 0,
})

function statusFor(product: ApiProduct): Exclude<StatusFilter, 'all'> {
  if (product.stock_count === 0) return 'out_of_stock'
  if (product.stock_count <= 3) return 'low_stock'
  return 'active'
}

function Modal({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl bg-card border border-border shadow-2xl shadow-black/50">
        <div className="sticky top-0 bg-card/95 backdrop-blur border-b border-border px-5 py-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-foreground">{title}</h3>
          <button onClick={onClose} className="w-8 h-8 rounded-lg hover:bg-white/10 flex items-center justify-center">
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-xs text-muted-foreground">{label}</span>
      <div className="mt-1">{children}</div>
    </label>
  )
}

const inputClass = 'w-full bg-surface-raised border border-border rounded-xl px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-neon/30'

export default function AssortmentTab({ data, onRefresh }: { data: AdminData; onRefresh: () => Promise<void> }) {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [catFilter, setCatFilter] = useState('Все')
  const [editing, setEditing] = useState<ApiProduct | 'new' | null>(null)
  const [productForm, setProductForm] = useState<ProductPayload>(emptyProduct(data.categories[0]?.id || 0))
  const [categoryForm, setCategoryForm] = useState<CategoryPayload>({ title: '', premium_emoji_id: '', sort_order: 0 })
  const [showCategoryForm, setShowCategoryForm] = useState(false)
  const [stockProduct, setStockProduct] = useState<ApiProduct | null>(null)
  const [stockItems, setStockItems] = useState<ApiStockItem[]>([])
  const [keys, setKeys] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  const categories = useMemo(() => ['Все', ...data.categories.map((category) => category.title)], [data.categories])
  const filtered = data.products.filter((product) => {
    const matchesSearch = product.title.toLowerCase().includes(search.toLowerCase())
    const matchesStatus = statusFilter === 'all' || statusFor(product) === statusFilter
    const matchesCat = catFilter === 'Все' || product.category_title === catFilter
    return matchesSearch && matchesStatus && matchesCat
  })

  useEffect(() => {
    if (editing && editing !== 'new') {
      setProductForm({
        category_id: editing.category_id,
        title: editing.title,
        title_i18n: editing.title_i18n,
        description: editing.description,
        description_i18n: editing.description_i18n,
        important_info: editing.important_info,
        important_info_i18n: editing.important_info_i18n,
        price: String(editing.price_cents / 100),
        warranty_label: editing.warranty_label,
        sort_order: editing.sort_order,
      })
    }
    if (editing === 'new') {
      setProductForm(emptyProduct(data.categories[0]?.id || 0))
    }
  }, [editing, data.categories])

  const saveProduct = async (event: React.FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setMessage('')
    try {
      if (editing === 'new') {
        await api.createProduct(productForm)
      } else if (editing) {
        await api.updateProduct(editing.id, productForm)
      }
      setEditing(null)
      await onRefresh()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Не удалось сохранить товар')
    } finally {
      setBusy(false)
    }
  }

  const saveCategory = async (event: React.FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setMessage('')
    try {
      await api.createCategory(categoryForm)
      setCategoryForm({ title: '', premium_emoji_id: '', sort_order: 0 })
      setShowCategoryForm(false)
      await onRefresh()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Не удалось сохранить категорию')
    } finally {
      setBusy(false)
    }
  }

  const toggleProduct = async (product: ApiProduct) => {
    setBusy(true)
    try {
      await api.toggleProduct(product.id)
      await onRefresh()
    } finally {
      setBusy(false)
    }
  }

  const openStock = async (product: ApiProduct) => {
    setStockProduct(product)
    setKeys('')
    setMessage('')
    const response = await api.stockItems(product.id)
    setStockItems(response.items)
  }

  const addKeys = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!stockProduct) return
    setBusy(true)
    setMessage('')
    try {
      const result = await api.addStock(stockProduct.id, keys)
      setMessage(`Добавлено: ${result.added}, пропущено: ${result.skipped}`)
      setKeys('')
      const response = await api.stockItems(stockProduct.id)
      setStockItems(response.items)
      await onRefresh()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Не удалось добавить ключи')
    } finally {
      setBusy(false)
    }
  }

  const deleteKey = async (item: ApiStockItem) => {
    if (!stockProduct) return
    setBusy(true)
    try {
      await api.deleteStockItem(stockProduct.id, item.id)
      const response = await api.stockItems(stockProduct.id)
      setStockItems(response.items)
      await onRefresh()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Ассортимент</h1>
          <p className="text-sm text-muted-foreground mt-0.5">{data.products.length} товаров в каталоге</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowCategoryForm(true)} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-card border border-border text-muted-foreground text-sm hover:text-foreground transition-colors">
            <Plus className="w-4 h-4" />
            Категория
          </button>
          <button onClick={() => setEditing('new')} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-neon/10 border border-neon/30 text-neon text-sm font-medium hover:bg-neon/20 transition-colors">
            <Plus className="w-4 h-4" />
            Добавить товар
          </button>
        </div>
      </div>

      {message && <div className="rounded-xl border border-neon/20 bg-neon/10 text-neon text-sm px-4 py-3">{message}</div>}

      <div className="flex gap-3 flex-wrap">
        {[
          { label: 'Активных', count: data.products.filter((p) => p.is_active).length, cls: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20' },
          { label: 'Мало на складе', count: data.products.filter((p) => p.stock_count > 0 && p.stock_count <= 3).length, cls: 'text-amber-400 bg-amber-400/10 border-amber-400/20' },
          { label: 'Нет в наличии', count: data.products.filter((p) => p.stock_count === 0).length, cls: 'text-red-400 bg-red-400/10 border-red-400/20' },
        ].map((s) => (
          <div key={s.label} className={cn('px-4 py-2 rounded-xl border text-xs font-medium flex items-center gap-2', s.cls)}>
            <span className="font-bold text-base leading-none">{s.count}</span>
            {s.label}
          </div>
        ))}
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input type="text" placeholder="Поиск товара..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full bg-card border border-border rounded-xl pl-9 pr-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-neon/30 focus:border-neon/40 transition-all" />
        </div>
        <div className="flex items-center gap-1 p-1 rounded-xl bg-card border border-border">
          <Filter className="w-4 h-4 text-muted-foreground ml-2" />
          {(['all', 'active', 'low_stock', 'out_of_stock'] as StatusFilter[]).map((s) => (
            <button key={s} onClick={() => setStatusFilter(s)} className={cn('px-3 py-1.5 rounded-lg text-xs font-medium transition-all', statusFilter === s ? 'bg-neon/15 text-neon' : 'text-muted-foreground hover:text-foreground')}>
              {s === 'all' ? 'Все' : s === 'active' ? 'Активные' : s === 'low_stock' ? 'Мало' : 'Нет'}
            </button>
          ))}
        </div>
      </div>

      <div className="flex gap-1 overflow-x-auto pb-1">
        {categories.map((cat) => (
          <button key={cat} onClick={() => setCatFilter(cat)} className={cn('px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all shrink-0', catFilter === cat ? 'bg-neon/15 text-neon border border-neon/25' : 'text-muted-foreground hover:text-foreground hover:bg-white/5 border border-transparent')}>
            {cat}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4 stagger">
        {filtered.map((product) => {
          const status = statusFor(product)
          const statusConfig = {
            active: { label: product.is_active ? 'Активен' : 'Скрыт', cls: product.is_active ? 'bg-emerald-400/10 text-emerald-400' : 'bg-zinc-500/20 text-zinc-400', icon: null },
            low_stock: { label: 'Мало', cls: 'bg-amber-400/10 text-amber-400', icon: AlertTriangle },
            out_of_stock: { label: 'Нет', cls: 'bg-red-400/10 text-red-400', icon: XCircle },
          }[status]
          const StatusIcon = statusConfig.icon
          return (
            <div key={product.id} className="group rounded-2xl bg-card border border-border p-5 hover:border-white/15 transition-all duration-300 hover:shadow-lg hover:shadow-black/20">
              <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 rounded-xl bg-surface-raised border border-border flex items-center justify-center text-lg font-bold text-neon">
                  {product.title.slice(0, 2).toUpperCase()}
                </div>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button onClick={() => setEditing(product)} className="w-7 h-7 rounded-lg hover:bg-white/10 flex items-center justify-center transition-colors" title="Редактировать">
                    <Edit2 className="w-3.5 h-3.5 text-muted-foreground" />
                  </button>
                  <button onClick={() => openStock(product)} className="w-7 h-7 rounded-lg hover:bg-white/10 flex items-center justify-center transition-colors" title="Ключи">
                    <MoreHorizontal className="w-3.5 h-3.5 text-muted-foreground" />
                  </button>
                  <button disabled={busy} onClick={() => toggleProduct(product)} className="w-7 h-7 rounded-lg hover:bg-red-400/10 flex items-center justify-center transition-colors" title={product.is_active ? 'Скрыть товар' : 'Включить товар'}>
                    <Trash2 className="w-3.5 h-3.5 text-red-400/70" />
                  </button>
                </div>
              </div>
              <h3 className="font-semibold text-sm text-foreground leading-snug mb-1">{product.title}</h3>
              <p className="text-xs text-muted-foreground mb-3">{product.category_title}</p>
              <div className="flex items-center justify-between mb-3">
                <span className="text-lg font-bold text-foreground">{product.price_label}</span>
                <span className={cn('flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full', statusConfig.cls)}>
                  {StatusIcon && <StatusIcon className="w-2.5 h-2.5" />}
                  {statusConfig.label}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs text-muted-foreground border-t border-border pt-3">
                <button onClick={() => openStock(product)} className="flex items-center gap-1 hover:text-neon transition-colors">
                  <Package className="w-3 h-3" />
                  <span>Склад: {product.stock_count}</span>
                </button>
                <div><span className="text-neon font-medium">{product.sold_count}</span> продаж</div>
              </div>
            </div>
          )
        })}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-16 text-muted-foreground">
          <Package className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm">Товары не найдены</p>
        </div>
      )}

      {editing && (
        <Modal title={editing === 'new' ? 'Добавить товар' : 'Редактировать товар'} onClose={() => setEditing(null)}>
          <form onSubmit={saveProduct} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Категория">
                <select value={productForm.category_id} onChange={(e) => setProductForm((form) => ({ ...form, category_id: Number(e.target.value) }))} className={inputClass}>
                  {data.categories.map((category) => <option key={category.id} value={category.id}>{category.title}</option>)}
                </select>
              </Field>
              <Field label="Цена">
                <input value={productForm.price} onChange={(e) => setProductForm((form) => ({ ...form, price: e.target.value }))} className={inputClass} />
              </Field>
            </div>
            <Field label="Название">
              <input value={productForm.title} onChange={(e) => setProductForm((form) => ({ ...form, title: e.target.value, title_i18n: { ru: e.target.value } }))} className={inputClass} />
            </Field>
            <Field label="Описание">
              <textarea value={productForm.description} onChange={(e) => setProductForm((form) => ({ ...form, description: e.target.value, description_i18n: { ru: e.target.value } }))} rows={3} className={inputClass} />
            </Field>
            <Field label="Важная информация">
              <textarea value={productForm.important_info} onChange={(e) => setProductForm((form) => ({ ...form, important_info: e.target.value, important_info_i18n: { ru: e.target.value } }))} rows={3} className={inputClass} />
            </Field>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Гарантия">
                <input value={productForm.warranty_label} onChange={(e) => setProductForm((form) => ({ ...form, warranty_label: e.target.value }))} className={inputClass} />
              </Field>
              <Field label="Сортировка">
                <input type="number" value={productForm.sort_order} onChange={(e) => setProductForm((form) => ({ ...form, sort_order: Number(e.target.value) }))} className={inputClass} />
              </Field>
            </div>
            <button disabled={busy} className="w-full rounded-xl bg-neon/10 border border-neon/30 text-neon text-sm font-medium py-2.5 hover:bg-neon/20 transition-colors disabled:opacity-60">Сохранить</button>
          </form>
        </Modal>
      )}

      {showCategoryForm && (
        <Modal title="Добавить категорию" onClose={() => setShowCategoryForm(false)}>
          <form onSubmit={saveCategory} className="space-y-4">
            <Field label="Название">
              <input value={categoryForm.title} onChange={(e) => setCategoryForm((form) => ({ ...form, title: e.target.value }))} className={inputClass} />
            </Field>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Premium emoji ID">
                <input value={categoryForm.premium_emoji_id} onChange={(e) => setCategoryForm((form) => ({ ...form, premium_emoji_id: e.target.value }))} className={inputClass} />
              </Field>
              <Field label="Сортировка">
                <input type="number" value={categoryForm.sort_order} onChange={(e) => setCategoryForm((form) => ({ ...form, sort_order: Number(e.target.value) }))} className={inputClass} />
              </Field>
            </div>
            <button disabled={busy} className="w-full rounded-xl bg-neon/10 border border-neon/30 text-neon text-sm font-medium py-2.5 hover:bg-neon/20 transition-colors disabled:opacity-60">Создать</button>
          </form>
        </Modal>
      )}

      {stockProduct && (
        <Modal title={`Ключи: ${stockProduct.title}`} onClose={() => setStockProduct(null)}>
          <form onSubmit={addKeys} className="space-y-3 mb-5">
            <Field label="Новые ключи, каждый с новой строки">
              <textarea value={keys} onChange={(e) => setKeys(e.target.value)} rows={5} className={inputClass} />
            </Field>
            <button disabled={busy} className="rounded-xl bg-neon/10 border border-neon/30 text-neon text-sm font-medium px-4 py-2 hover:bg-neon/20 transition-colors disabled:opacity-60">Добавить ключи</button>
          </form>
          <div className="rounded-xl border border-border overflow-hidden">
            <div className="grid grid-cols-[1fr_auto_auto] gap-3 px-3 py-2 text-[11px] uppercase tracking-wide text-muted-foreground border-b border-border">
              <span>Ключ</span><span>Статус</span><span />
            </div>
            <div className="max-h-72 overflow-y-auto divide-y divide-border">
              {stockItems.map((item) => (
                <div key={item.id} className="grid grid-cols-[1fr_auto_auto] gap-3 px-3 py-2 items-center text-xs">
                  <span className="font-mono text-muted-foreground truncate">{item.key_value}</span>
                  <span className="text-foreground">{item.status}</span>
                  <button disabled={!item.can_delete || busy} onClick={() => deleteKey(item)} className="text-red-400 disabled:text-muted-foreground">Удалить</button>
                </div>
              ))}
              {stockItems.length === 0 && <div className="px-3 py-8 text-center text-sm text-muted-foreground">Ключей нет</div>}
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
