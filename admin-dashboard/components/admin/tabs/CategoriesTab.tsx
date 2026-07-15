'use client'

import { useEffect, useState } from 'react'
import { Plus, Edit2, EyeOff, Eye, GripVertical, X, Tag, Trash2 } from 'lucide-react'
import {
  createCategory,
  deleteCategory,
  getCategories,
  reorderCategories,
  toggleCategory,
  updateCategory,
  type Category,
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
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

const CATEGORY_TABLE_COLUMNS = 'grid-cols-[32px_minmax(0,1.6fr)_minmax(180px,0.95fr)_72px_104px]'

// ── Category Modal ────────────────────────────────────────────────────────────
interface CategoryModalProps {
  category?: Category
  onClose: () => void
  onSave: (data: Partial<Category>) => void
}

function CategoryModal({ category, onClose, onSave }: CategoryModalProps) {
  const isEdit = !!category
  const [title, setTitle] = useState(category?.title ?? '')
  const [emojiId, setEmojiId] = useState(category?.premium_emoji_id ?? '')
  const [slug, setSlug] = useState(category?.slug ?? '')

  const handleSave = () => {
    onSave({ title, premium_emoji_id: emojiId, slug: slug || title.toLowerCase().replace(/\s+/g, '-') })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center sm:p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full sm:max-w-md bg-card border border-border rounded-t-3xl sm:rounded-2xl shadow-2xl shadow-black/50 overflow-hidden pb-safe">
        <div className="flex items-center justify-between px-5 sm:px-6 py-4 border-b border-border">
          <h2 className="text-base font-semibold text-foreground">{isEdit ? 'Edit category' : 'Add category'}</h2>
          <button onClick={onClose} className="w-8 h-8 rounded-lg hover:bg-white/10 flex items-center justify-center transition-colors">
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>

        <div className="px-5 sm:px-6 py-5 space-y-4">
          <div>
            <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide mb-1.5 block">
              Category name
            </label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Games"
              className="w-full bg-surface-raised border border-border rounded-xl px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-neon/30"
            />
          </div>

          <div>
            <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide mb-1.5 block">
              Slug
            </label>
            <input
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              placeholder="games"
              className="w-full bg-surface-raised border border-border rounded-xl px-3 py-2 text-sm text-foreground font-mono placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-neon/30"
            />
            <p className="text-[11px] text-muted-foreground mt-1">Used in bot commands and URLs. No spaces.</p>
          </div>

          <div>
            <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide mb-1.5 block">
              Premium Emoji ID
            </label>
            <input
              value={emojiId}
              onChange={(e) => setEmojiId(e.target.value)}
              placeholder="5368324170671202286"
              className="w-full bg-surface-raised border border-border rounded-xl px-3 py-2 text-sm text-foreground font-mono placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-neon/30"
            />
            <p className="text-[11px] text-muted-foreground mt-1">Telegram premium custom emoji ID for the bot menu.</p>
          </div>
        </div>

        <div className="px-5 sm:px-6 py-4 border-t border-border flex items-center justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 rounded-xl text-sm text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors">
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!title.trim()}
            className="px-5 py-2 rounded-xl bg-neon/15 border border-neon/30 text-neon text-sm font-medium hover:bg-neon/25 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isEdit ? 'Save changes' : 'Add category'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Sortable row ──────────────────────────────────────────────────────────────
function SortableCategoryRow({
  category,
  onEdit,
  onToggle,
  onDelete,
}: {
  category: Category
  onEdit: () => void
  onToggle: () => void
  onDelete: () => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: category.id })
  const style = { transform: CSS.Transform.toString(transform), transition }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        `group grid ${CATEGORY_TABLE_COLUMNS} gap-4 items-center px-5 py-4 hover:bg-white/[0.03] transition-colors`,
        isDragging && 'opacity-50 bg-white/5',
        !category.is_active && 'opacity-60',
      )}
    >
      {/* Drag handle */}
      <div
        {...attributes}
        {...listeners}
        style={{ touchAction: 'none' }}
        className="w-6 h-6 flex items-center justify-center cursor-grab active:cursor-grabbing text-muted-foreground/30 hover:text-muted-foreground transition-colors"
      >
        <GripVertical className="w-4 h-4" />
      </div>

      {/* Title + slug */}
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-foreground">{category.title}</span>
          {!category.is_active && (
            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-zinc-500/20 text-zinc-400">Hidden</span>
          )}
        </div>
        <p className="text-xs text-muted-foreground font-mono">{category.slug}</p>
      </div>

      {/* Emoji ID */}
      <div className="min-w-0">
        {category.premium_emoji_id ? (
          <span className="inline-flex max-w-full font-mono text-[11px] text-muted-foreground bg-surface-raised border border-border px-2 py-0.5 rounded-lg">
            {category.premium_emoji_id.length > 12 ? `${category.premium_emoji_id.slice(0, 12)}…` : category.premium_emoji_id}
          </span>
        ) : (
          <span className="text-[11px] text-muted-foreground/40">— no emoji —</span>
        )}
      </div>

      {/* Sort order */}
      <span className="text-xs text-muted-foreground">#{category.sort_order + 1}</span>

      {/* Actions */}
      <div className="flex gap-1 opacity-100 lg:opacity-0 lg:group-hover:opacity-100 transition-opacity">
        <button onClick={onEdit} title="Edit" className="w-7 h-7 rounded-lg hover:bg-white/10 flex items-center justify-center transition-colors">
          <Edit2 className="w-3.5 h-3.5 text-muted-foreground" />
        </button>
        <button onClick={onToggle} title={category.is_active ? 'Hide' : 'Show'} className="w-7 h-7 rounded-lg hover:bg-white/10 flex items-center justify-center transition-colors">
          {category.is_active
            ? <EyeOff className="w-3.5 h-3.5 text-muted-foreground" />
            : <Eye className="w-3.5 h-3.5 text-emerald-400" />}
        </button>
        <button onClick={onDelete} title="Delete" className="w-7 h-7 rounded-lg hover:bg-red-500/10 flex items-center justify-center transition-colors">
          <Trash2 className="w-3.5 h-3.5 text-red-400" />
        </button>
      </div>
    </div>
  )
}

// ── Sortable card (mobile) ───────────────────────────────────────────────────
function SortableCategoryCard({
  category,
  onEdit,
  onToggle,
  onDelete,
}: {
  category: Category
  onEdit: () => void
  onToggle: () => void
  onDelete: () => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: category.id })
  const style = { transform: CSS.Transform.toString(transform), transition }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'flex items-center gap-3 rounded-2xl bg-card border border-border p-3.5 transition-colors',
        isDragging && 'opacity-50 bg-white/5',
        !category.is_active && 'opacity-60',
      )}
    >
      <div
        {...attributes}
        {...listeners}
        style={{ touchAction: 'none' }}
        className="w-9 h-9 -ml-1 shrink-0 flex items-center justify-center text-muted-foreground/40 active:text-muted-foreground transition-colors"
      >
        <GripVertical className="w-4.5 h-4.5" />
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-foreground truncate">{category.title}</span>
          {!category.is_active && (
            <span className="shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-zinc-500/20 text-zinc-400">Hidden</span>
          )}
        </div>
        <p className="text-xs text-muted-foreground font-mono truncate">{category.slug} · #{category.sort_order + 1}</p>
      </div>

      <div className="flex items-center gap-1 shrink-0">
        <button onClick={onEdit} title="Edit" className="w-9 h-9 rounded-lg active:bg-white/10 flex items-center justify-center transition-colors">
          <Edit2 className="w-4 h-4 text-muted-foreground" />
        </button>
        <button onClick={onToggle} title={category.is_active ? 'Hide' : 'Show'} className="w-9 h-9 rounded-lg active:bg-white/10 flex items-center justify-center transition-colors">
          {category.is_active
            ? <EyeOff className="w-4 h-4 text-muted-foreground" />
            : <Eye className="w-4 h-4 text-emerald-400" />}
        </button>
        <button onClick={onDelete} title="Delete" className="w-9 h-9 rounded-lg active:bg-red-500/10 flex items-center justify-center transition-colors">
          <Trash2 className="w-4 h-4 text-red-400" />
        </button>
      </div>
    </div>
  )
}

// ── Main tab ──────────────────────────────────────────────────────────────────
export default function CategoriesTab() {
  const [items, setItems] = useState<Category[]>([])
  const [editCategory, setEditCategory] = useState<Category | null | 'new'>(null)
  const [error, setError] = useState('')

  const refresh = async () => {
    setItems(await getCategories())
  }

  useEffect(() => {
    refresh().catch((err) => setError(err instanceof Error ? err.message : 'Failed to load categories'))
  }, [])

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (over && active.id !== over.id) {
      const previous = items
      const oldIndex = previous.findIndex((c) => c.id === active.id)
      const newIndex = previous.findIndex((c) => c.id === over.id)
      const next = arrayMove(previous, oldIndex, newIndex).map((c, i) => ({ ...c, sort_order: i }))
      setItems(next)
      reorderCategories(next.map((category) => category.id)).catch((err) => {
        setItems(previous)
        setError(err instanceof Error ? err.message : 'Failed to reorder categories')
      })
    }
  }

  const toggleVisibility = async (id: string) => {
    try {
      const updated = await toggleCategory(id)
      setItems((prev) => prev.map((c) => c.id === id ? updated : c))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle category')
    }
  }

  const handleSave = async (data: Partial<Category>) => {
    try {
      if (editCategory === 'new') {
        const created = await createCategory({ ...data, sort_order: items.length })
        setItems((prev) => [...prev, created])
      } else if (editCategory) {
        const updated = await updateCategory(editCategory.id, { ...editCategory, ...data })
        setItems((prev) => prev.map((c) => c.id === editCategory.id ? updated : c))
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save category')
    }
  }

  const handleDelete = async (category: Category) => {
    const confirmed = window.confirm(`Delete category "${category.title}"?`)
    if (!confirmed) return
    try {
      await deleteCategory(category.id)
      setItems((prev) => prev.filter((item) => item.id !== category.id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete category')
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {error && <div className="rounded-xl border border-red-400/20 bg-red-400/10 text-red-400 text-sm px-4 py-3">{error}</div>}
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Categories</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {items.length} categories · {items.filter((c) => c.is_active).length} visible
          </p>
        </div>
        <button
          onClick={() => setEditCategory('new')}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-neon/10 border border-neon/30 text-neon text-sm font-medium hover:bg-neon/20 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add category
        </button>
      </div>

      {/* Info banner */}
      <div className="flex items-start gap-3 px-4 py-3.5 rounded-xl bg-neon/5 border border-neon/15 text-xs text-muted-foreground">
        <Tag className="w-3.5 h-3.5 text-neon shrink-0 mt-0.5" />
        <span>Drag rows to reorder categories. The order here determines the order shown to users in the bot.</span>
      </div>

      {/* Mobile card list */}
      <div className="md:hidden">
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={items.map((c) => c.id)} strategy={verticalListSortingStrategy}>
            <div className="space-y-2">
              {items.map((cat) => (
                <SortableCategoryCard
                  key={cat.id}
                  category={cat}
                  onEdit={() => setEditCategory(cat)}
                  onToggle={() => toggleVisibility(cat.id)}
                  onDelete={() => handleDelete(cat)}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>

        {items.length === 0 && (
          <div className="text-center py-12 text-muted-foreground rounded-2xl bg-card border border-border">
            <Tag className="w-8 h-8 mx-auto mb-2 opacity-30" />
            <p className="text-sm">No categories yet</p>
          </div>
        )}
      </div>

      {/* Table — desktop */}
      <div className="hidden md:block rounded-2xl bg-card border border-border overflow-x-auto">
        {/* Header */}
        <div className="min-w-[720px]">
          <div className={cn('grid gap-4 px-5 py-3 border-b border-border', CATEGORY_TABLE_COLUMNS)}>
            <span className="w-6" />
            <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Category</span>
            <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Emoji ID</span>
            <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Order</span>
            <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Actions</span>
          </div>

          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={items.map((c) => c.id)} strategy={verticalListSortingStrategy}>
              <div className="divide-y divide-border">
                {items.map((cat) => (
                  <SortableCategoryRow
                    key={cat.id}
                    category={cat}
                    onEdit={() => setEditCategory(cat)}
                    onToggle={() => toggleVisibility(cat.id)}
                    onDelete={() => handleDelete(cat)}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>

          {items.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              <Tag className="w-8 h-8 mx-auto mb-2 opacity-30" />
              <p className="text-sm">No categories yet</p>
            </div>
          )}
        </div>
      </div>

      {/* Modal */}
      {editCategory !== null && (
        <CategoryModal
          category={editCategory === 'new' ? undefined : editCategory}
          onClose={() => setEditCategory(null)}
          onSave={handleSave}
        />
      )}
    </div>
  )
}
