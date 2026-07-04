'use client'

import { useEffect, useState } from 'react'
import { Plus, Edit2, EyeOff, Eye, GripVertical, X, Tag } from 'lucide-react'
import {
  createCategory,
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md bg-card border border-border rounded-2xl shadow-2xl shadow-black/50 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-base font-semibold text-foreground">{isEdit ? 'Edit category' : 'Add category'}</h2>
          <button onClick={onClose} className="w-8 h-8 rounded-lg hover:bg-white/10 flex items-center justify-center transition-colors">
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>

        <div className="px-6 py-5 space-y-4">
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

        <div className="px-6 py-4 border-t border-border flex items-center justify-end gap-3">
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
}: {
  category: Category
  onEdit: () => void
  onToggle: () => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: category.id })
  const style = { transform: CSS.Transform.toString(transform), transition }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'group grid grid-cols-[auto_1fr_auto_auto_auto] gap-4 items-center px-5 py-4 hover:bg-white/[0.03] transition-colors',
        isDragging && 'opacity-50 bg-white/5',
        !category.is_active && 'opacity-60',
      )}
    >
      {/* Drag handle */}
      <div
        {...attributes}
        {...listeners}
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
      <div className="hidden sm:block text-right">
        {category.premium_emoji_id ? (
          <span className="font-mono text-[11px] text-muted-foreground bg-surface-raised border border-border px-2 py-0.5 rounded-lg">
            {category.premium_emoji_id.length > 12 ? `${category.premium_emoji_id.slice(0, 12)}…` : category.premium_emoji_id}
          </span>
        ) : (
          <span className="text-[11px] text-muted-foreground/40">— no emoji —</span>
        )}
      </div>

      {/* Sort order */}
      <span className="text-xs text-muted-foreground w-8 text-right">#{category.sort_order + 1}</span>

      {/* Actions */}
      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button onClick={onEdit} title="Edit" className="w-7 h-7 rounded-lg hover:bg-white/10 flex items-center justify-center transition-colors">
          <Edit2 className="w-3.5 h-3.5 text-muted-foreground" />
        </button>
        <button onClick={onToggle} title={category.is_active ? 'Hide' : 'Show'} className="w-7 h-7 rounded-lg hover:bg-white/10 flex items-center justify-center transition-colors">
          {category.is_active
            ? <EyeOff className="w-3.5 h-3.5 text-muted-foreground" />
            : <Eye className="w-3.5 h-3.5 text-emerald-400" />}
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
      setItems((prev) => {
        const oldIndex = prev.findIndex((c) => c.id === active.id)
        const newIndex = prev.findIndex((c) => c.id === over.id)
        const next = arrayMove(prev, oldIndex, newIndex).map((c, i) => ({ ...c, sort_order: i }))
        reorderCategories(next.map((category) => category.id)).catch((err) => setError(err instanceof Error ? err.message : 'Failed to reorder categories'))
        return next
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

  return (
    <div className="space-y-6 animate-fade-in">
      {error && <div className="rounded-xl border border-red-400/20 bg-red-400/10 text-red-400 text-sm px-4 py-3">{error}</div>}
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Категории</h1>
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

      {/* Table */}
      <div className="rounded-2xl bg-card border border-border overflow-hidden">
        {/* Header */}
        <div className="grid grid-cols-[auto_1fr_auto_auto_auto] gap-4 px-5 py-3 border-b border-border">
          <span className="w-6" />
          <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Category</span>
          <span className="hidden sm:block text-[11px] font-semibold uppercase tracking-wide text-muted-foreground text-right">Emoji ID</span>
          <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground w-8 text-right">Order</span>
          <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground w-16 text-center">Actions</span>
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
