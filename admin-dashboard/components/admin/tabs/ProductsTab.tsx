'use client'

import { useEffect, useState } from 'react'
import {
  Search, Plus, AlertTriangle, XCircle, Edit2, Key, EyeOff, Eye,
  GripVertical, X, ChevronDown,
} from 'lucide-react'
import {
  createProduct,
  getCategories,
  getProducts,
  reorderProducts,
  toggleProduct,
  updateProduct,
  uploadProductKeys,
  type Category,
  type Product,
} from '@/lib/api'
import { cn } from '@/lib/utils'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  rectSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

// ── helpers ──────────────────────────────────────────────────────────────────
const fmt = (cents: number) => `$${(cents / 100).toFixed(2)}`

const statusConfig = {
  active:       { label: 'Active',    cls: 'bg-emerald-400/10 text-emerald-400', icon: null },
  low_stock:    { label: 'Low',       cls: 'bg-amber-400/10 text-amber-400',     icon: AlertTriangle },
  out_of_stock: { label: 'No stock',  cls: 'bg-red-400/10 text-red-400',         icon: XCircle },
  hidden:       { label: 'Hidden',    cls: 'bg-zinc-500/20 text-zinc-400',        icon: EyeOff },
}

function getProductStatus(p: Product): keyof typeof statusConfig {
  if (!p.is_active) return 'hidden'
  if (p.stock === 0) return 'out_of_stock'
  if (p.stock < 10) return 'low_stock'
  return 'active'
}

const LANGS = ['EN', 'RU', 'UA'] as const
type Lang = typeof LANGS[number]
const LANG_KEY: Record<Lang, 'en' | 'ru' | 'ua'> = { EN: 'en', RU: 'ru', UA: 'ua' }

// ── empty product template ────────────────────────────────────────────────────
const emptyProduct = (categories: Category[]): Omit<Product, 'id' | 'slug' | 'created_at' | 'sold'> => ({
  category_id: categories[0]?.id ?? '',
  category:    categories[0]?.title ?? '',
  title: '',
  title_i18n:        { en: '', ru: '', ua: '' },
  description: '',
  description_i18n:  { en: '', ru: '', ua: '' },
  important_info: '',
  important_info_i18n: { en: '', ru: '', ua: '' },
  price_cents:    0,
  warranty_label: '',
  is_active:  true,
  sort_order: 0,
  stock: 0,
  image: '📦',
})

// ── Product modal (edit / add) ────────────────────────────────────────────────
interface ProductModalProps {
  product?: Product
  categories: Category[]
  onClose: () => void
  onSave: (p: Partial<Product>) => void
}

function ProductModal({ product, categories, onClose, onSave }: ProductModalProps) {
  const isEdit = !!product
  const [lang, setLang] = useState<Lang>('EN')

  const [form, setForm] = useState<ReturnType<typeof emptyProduct>>(() =>
    product
      ? {
          category_id:         product.category_id,
          category:            product.category,
          title:               product.title,
          title_i18n:          { ...product.title_i18n },
          description:         product.description,
          description_i18n:    { ...product.description_i18n },
          important_info:      product.important_info,
          important_info_i18n: { ...product.important_info_i18n },
          price_cents:         product.price_cents,
          warranty_label:      product.warranty_label,
          is_active:           product.is_active,
          sort_order:          product.sort_order,
          stock:               product.stock,
          image:               product.image,
        }
      : emptyProduct(categories),
  )

  const setI18n = (
    field: 'title_i18n' | 'description_i18n' | 'important_info_i18n',
    val: string,
  ) => {
    const key = LANG_KEY[lang]
    setForm((f) => ({ ...f, [field]: { ...f[field], [key]: val } }))
  }

  const handleSave = () => {
    onSave(form)
    onClose()
  }

  const catObj = categories.find((c) => c.id === form.category_id)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-2xl bg-card border border-border rounded-2xl shadow-2xl shadow-black/50 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
          <h2 className="text-base font-semibold text-foreground">{isEdit ? 'Edit product' : 'Add product'}</h2>
          <button onClick={onClose} className="w-8 h-8 rounded-lg hover:bg-white/10 flex items-center justify-center transition-colors">
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>

        <div className="overflow-y-auto flex-1 px-6 py-5 space-y-5">
          {/* Category + Price + Warranty row */}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide mb-1.5 block">Category</label>
              <div className="relative">
                <select
                  value={form.category_id}
                  onChange={(e) => {
                    const cat = categories.find((c) => c.id === e.target.value)
                    setForm((f) => ({ ...f, category_id: e.target.value, category: cat?.title ?? '' }))
                  }}
                  className="w-full appearance-none bg-surface-raised border border-border rounded-xl px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-neon/30 pr-8"
                >
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>{c.title}</option>
                  ))}
                </select>
                <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground pointer-events-none" />
              </div>
            </div>
            <div>
              <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide mb-1.5 block">Price (USD)</label>
              <input
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                value={form.price_cents / 100 || ''}
                onChange={(e) => setForm((f) => ({ ...f, price_cents: Math.round(parseFloat(e.target.value || '0') * 100) }))}
                className="w-full bg-surface-raised border border-border rounded-xl px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-neon/30"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide mb-1.5 block">Warranty (days)</label>
              <input
                type="number"
                min="0"
                placeholder="30"
                value={form.warranty_label.replace(/\D/g, '') || ''}
                onChange={(e) => setForm((f) => ({ ...f, warranty_label: e.target.value ? `${e.target.value} days` : '' }))}
                className="w-full bg-surface-raised border border-border rounded-xl px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-neon/30"
              />
            </div>
          </div>

          {/* Lang switcher */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide">Localisation</p>
              <div className="flex gap-1 p-0.5 rounded-lg bg-surface-raised border border-border">
                {LANGS.map((l) => (
                  <button
                    key={l}
                    onClick={() => setLang(l)}
                    className={cn(
                      'px-3 py-1 rounded-md text-xs font-semibold transition-all',
                      lang === l ? 'bg-neon/15 text-neon' : 'text-muted-foreground hover:text-foreground',
                    )}
                  >
                    {l}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide mb-1.5 block">
                  Title ({lang})
                </label>
                <input
                  value={form.title_i18n[LANG_KEY[lang]] ?? ''}
                  onChange={(e) => setI18n('title_i18n', e.target.value)}
                  placeholder={`Product name in ${lang}`}
                  className="w-full bg-surface-raised border border-border rounded-xl px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-neon/30"
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide mb-1.5 block">
                  Description ({lang})
                </label>
                <textarea
                  rows={3}
                  value={form.description_i18n[LANG_KEY[lang]] ?? ''}
                  onChange={(e) => setI18n('description_i18n', e.target.value)}
                  placeholder={`Description in ${lang}`}
                  className="w-full bg-surface-raised border border-border rounded-xl px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-neon/30 resize-none"
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide mb-1.5 block">
                  Important info ({lang})
                </label>
                <textarea
                  rows={2}
                  value={form.important_info_i18n[LANG_KEY[lang]] ?? ''}
                  onChange={(e) => setI18n('important_info_i18n', e.target.value)}
                  placeholder={`Important info in ${lang}`}
                  className="w-full bg-surface-raised border border-border rounded-xl px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-neon/30 resize-none"
                />
              </div>
            </div>
          </div>

          {/* Active toggle */}
          <div className="flex items-center justify-between p-4 rounded-xl bg-surface-raised border border-border">
            <div>
              <p className="text-sm font-medium text-foreground">Show product</p>
              <p className="text-xs text-muted-foreground">Hide from catalog without deleting</p>
            </div>
            <button
              onClick={() => setForm((f) => ({ ...f, is_active: !f.is_active }))}
              className={cn(
                'relative w-11 h-6 rounded-full transition-colors duration-200',
                form.is_active ? 'bg-neon' : 'bg-white/10',
              )}
            >
              <span className={cn('absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform duration-200', form.is_active && 'translate-x-5')} />
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-border flex items-center justify-end gap-3 shrink-0">
          <button onClick={onClose} className="px-4 py-2 rounded-xl text-sm text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors">
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-5 py-2 rounded-xl bg-neon/15 border border-neon/30 text-neon text-sm font-medium hover:bg-neon/25 transition-colors"
          >
            {isEdit ? 'Save changes' : 'Add product'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Keys modal ────────────────────────────────────────────────────────────────
function KeysModal({ product, onClose, onUpload }: { product: Product; onClose: () => void; onUpload: (keys: string[]) => void }) {
  const [keys, setKeys] = useState('')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-lg bg-card border border-border rounded-2xl shadow-2xl shadow-black/50 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <h2 className="text-base font-semibold text-foreground">Add keys</h2>
            <p className="text-xs text-muted-foreground mt-0.5">{product.title} · {product.stock} in stock</p>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-lg hover:bg-white/10 flex items-center justify-center transition-colors">
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>

        <div className="px-6 py-5 space-y-4">
          <div>
            <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide mb-1.5 block">
              Keys (one per line)
            </label>
            <textarea
              rows={8}
              value={keys}
              onChange={(e) => setKeys(e.target.value)}
              placeholder={'KEY-XXXX-XXXX-XXXX\nKEY-YYYY-YYYY-YYYY\n...'}
              className="w-full bg-surface-raised border border-border rounded-xl px-3 py-2 text-sm text-foreground font-mono placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-neon/30 resize-none"
            />
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground bg-amber-400/5 border border-amber-400/20 rounded-xl px-4 py-3">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            Keys are unique — duplicates will be skipped on upload.
          </div>
        </div>

        <div className="px-6 py-4 border-t border-border flex items-center justify-between">
          <span className="text-xs text-muted-foreground">
            {keys.split('\n').filter((k) => k.trim()).length} keys to add
          </span>
          <div className="flex gap-3">
            <button onClick={onClose} className="px-4 py-2 rounded-xl text-sm text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors">
              Cancel
            </button>
            <button
              onClick={() => {
                onUpload(keys.split('\n').map((key) => key.trim()).filter(Boolean))
                onClose()
              }}
              className="px-5 py-2 rounded-xl bg-neon/15 border border-neon/30 text-neon text-sm font-medium hover:bg-neon/25 transition-colors"
            >
              Upload keys
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Sortable card ─────────────────────────────────────────────────────────────
function SortableProductCard({
  product,
  onEdit,
  onKeys,
  onToggleVisibility,
}: {
  product: Product
  onEdit: () => void
  onKeys: () => void
  onToggleVisibility: () => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: product.id })
  const style = { transform: CSS.Transform.toString(transform), transition }
  const st = getProductStatus(product)
  const status = statusConfig[st]
  const StatusIcon = status.icon

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'group rounded-2xl bg-card border border-border p-5 transition-all duration-300 hover:border-white/15 hover:shadow-lg hover:shadow-black/20',
        isDragging && 'opacity-50 scale-95 z-50',
        !product.is_active && 'opacity-60',
      )}
    >
      {/* Top row */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2">
          {/* Drag handle */}
          <div
            {...attributes}
            {...listeners}
            className="w-6 h-6 rounded flex items-center justify-center cursor-grab active:cursor-grabbing text-muted-foreground/40 hover:text-muted-foreground transition-colors"
          >
            <GripVertical className="w-4 h-4" />
          </div>
          <div className="w-12 h-12 rounded-xl bg-surface-raised border border-border flex items-center justify-center text-2xl">
            {product.image}
          </div>
        </div>
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {/* Add keys */}
          <button
            onClick={onKeys}
            title="Add keys"
            className="w-7 h-7 rounded-lg hover:bg-neon/10 flex items-center justify-center transition-colors"
          >
            <Key className="w-3.5 h-3.5 text-neon/70" />
          </button>
          {/* Edit */}
          <button
            onClick={onEdit}
            title="Edit"
            className="w-7 h-7 rounded-lg hover:bg-white/10 flex items-center justify-center transition-colors"
          >
            <Edit2 className="w-3.5 h-3.5 text-muted-foreground" />
          </button>
          {/* Hide / Show */}
          <button
            onClick={onToggleVisibility}
            title={product.is_active ? 'Hide' : 'Show'}
            className="w-7 h-7 rounded-lg hover:bg-white/10 flex items-center justify-center transition-colors"
          >
            {product.is_active
              ? <EyeOff className="w-3.5 h-3.5 text-muted-foreground" />
              : <Eye className="w-3.5 h-3.5 text-emerald-400" />}
          </button>
        </div>
      </div>

      <h3 className="font-semibold text-sm text-foreground leading-snug mb-1">{product.title}</h3>
      <p className="text-xs text-muted-foreground mb-3">{product.category}</p>

      <div className="flex items-center justify-between mb-3">
        <span className="text-lg font-bold text-foreground">{fmt(product.price_cents)}</span>
        <span className={cn('flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full', status.cls)}>
          {StatusIcon && <StatusIcon className="w-2.5 h-2.5" />}
          {status.label}
        </span>
      </div>

      <div className="flex items-center justify-between text-xs text-muted-foreground border-t border-border pt-3">
        <div className="flex items-center gap-1">
          <Key className="w-3 h-3" />
          <span>Stock: {product.stock}</span>
        </div>
        <div>
          <span className="text-neon font-medium">{product.sold}</span> sold
        </div>
        {product.warranty_label && (
          <span className="text-xs text-muted-foreground">{product.warranty_label}</span>
        )}
      </div>
    </div>
  )
}

// ── Main tab ─────────────────────────────────────────────────────────────────
type StatusFilter = 'all' | 'active' | 'low_stock' | 'out_of_stock' | 'hidden'

export default function ProductsTab() {
  const [items, setItems] = useState<Product[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [catFilter, setCatFilter] = useState('all')
  const [editProduct, setEditProduct] = useState<Product | null | 'new'>(null)
  const [keysProduct, setKeysProduct] = useState<Product | null>(null)
  const [error, setError] = useState('')

  const refresh = async () => {
    const [nextProducts, nextCategories] = await Promise.all([getProducts(), getCategories()])
    setItems(nextProducts)
    setCategories(nextCategories)
  }

  useEffect(() => {
    refresh().catch((err) => setError(err instanceof Error ? err.message : 'Failed to load products'))
  }, [])

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (over && active.id !== over.id) {
      setItems((prev) => {
        const oldIndex = prev.findIndex((p) => p.id === active.id)
        const newIndex = prev.findIndex((p) => p.id === over.id)
        const next = arrayMove(prev, oldIndex, newIndex).map((p, i) => ({ ...p, sort_order: i }))
        reorderProducts(next.map((product) => product.id)).catch((err) => setError(err instanceof Error ? err.message : 'Failed to reorder products'))
        return next
      })
    }
  }

  const toggleVisibility = async (id: string) => {
    try {
      const updated = await toggleProduct(id)
      setItems((prev) => prev.map((p) => p.id === id ? updated : p))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle product')
    }
  }

  const handleSave = async (data: Partial<Product>) => {
    try {
      if (editProduct === 'new') {
        const created = await createProduct({ ...data, sort_order: items.length })
        setItems((prev) => [...prev, created])
      } else if (editProduct) {
        const updated = await updateProduct(editProduct.id, data)
        setItems((prev) => prev.map((p) => p.id === editProduct.id ? updated : p))
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save product')
    }
  }

  const handleUploadKeys = async (product: Product, keys: string[]) => {
    try {
      await uploadProductKeys(product.id, keys)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload keys')
    }
  }

  const filtered = items.filter((p) => {
    const q = search.toLowerCase()
    const matchSearch = p.title.toLowerCase().includes(q) || p.category.toLowerCase().includes(q)
    const st = getProductStatus(p)
    const matchStatus = statusFilter === 'all' || st === statusFilter
    const matchCat = catFilter === 'all' || p.category_id === catFilter
    return matchSearch && matchStatus && matchCat
  })

  const catOptions = [{ id: 'all', title: 'All' }, ...categories]

  return (
      <div className="space-y-6 animate-fade-in">
      {error && <div className="rounded-xl border border-red-400/20 bg-red-400/10 text-red-400 text-sm px-4 py-3">{error}</div>}
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Товары</h1>
          <p className="text-sm text-muted-foreground mt-0.5">{items.length} products in catalog</p>
        </div>
        <button
          onClick={() => setEditProduct('new')}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-neon/10 border border-neon/30 text-neon text-sm font-medium hover:bg-neon/20 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add product
        </button>
      </div>

      {/* Stat pills */}
      <div className="flex gap-3 flex-wrap">
        {([
          { label: 'Active',     filter: 'active',       count: items.filter((p) => getProductStatus(p) === 'active').length,       cls: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20' },
          { label: 'Low stock',  filter: 'low_stock',    count: items.filter((p) => getProductStatus(p) === 'low_stock').length,    cls: 'text-amber-400 bg-amber-400/10 border-amber-400/20' },
          { label: 'No stock',   filter: 'out_of_stock', count: items.filter((p) => getProductStatus(p) === 'out_of_stock').length, cls: 'text-red-400 bg-red-400/10 border-red-400/20' },
          { label: 'Hidden',     filter: 'hidden',       count: items.filter((p) => !p.is_active).length,                          cls: 'text-zinc-400 bg-zinc-500/20 border-zinc-500/20' },
        ] as const).map((s) => (
          <button
            key={s.label}
            onClick={() => setStatusFilter(statusFilter === s.filter ? 'all' : s.filter)}
            className={cn('px-4 py-2 rounded-xl border text-xs font-medium flex items-center gap-2 transition-all', s.cls, statusFilter === s.filter && 'ring-1 ring-current')}
          >
            <span className="font-bold text-base leading-none">{s.count}</span>
            {s.label}
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search product..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-card border border-border rounded-xl pl-9 pr-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-neon/30 focus:border-neon/40 transition-all"
          />
        </div>
      </div>

      {/* Category tabs */}
      <div className="flex gap-1 overflow-x-auto pb-1">
        {catOptions.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setCatFilter(cat.id)}
            className={cn(
              'px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all shrink-0',
              catFilter === cat.id
                ? 'bg-neon/15 text-neon border border-neon/25'
                : 'text-muted-foreground hover:text-foreground hover:bg-white/5 border border-transparent',
            )}
          >
            {cat.title}
          </button>
        ))}
      </div>

      {/* Drag-sortable grid */}
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={filtered.map((p) => p.id)} strategy={rectSortingStrategy}>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {filtered.map((product) => (
              <SortableProductCard
                key={product.id}
                product={product}
                onEdit={() => setEditProduct(product)}
                onKeys={() => setKeysProduct(product)}
                onToggleVisibility={() => toggleVisibility(product.id)}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      {filtered.length === 0 && (
        <div className="text-center py-16 text-muted-foreground">
          <div className="text-4xl mb-3">📦</div>
          <p className="text-sm">No products found</p>
        </div>
      )}

      {/* Modals */}
      {editProduct !== null && (
        <ProductModal
          product={editProduct === 'new' ? undefined : editProduct}
          categories={categories}
          onClose={() => setEditProduct(null)}
          onSave={handleSave}
        />
      )}
      {keysProduct && (
        <KeysModal product={keysProduct} onClose={() => setKeysProduct(null)} onUpload={(keys) => handleUploadKeys(keysProduct, keys)} />
      )}
    </div>
  )
}
