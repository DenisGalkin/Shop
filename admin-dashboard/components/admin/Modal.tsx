'use client'

import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { cn } from '@/lib/utils'

interface ModalProps {
  onClose: () => void
  children: React.ReactNode
  /** Extra classes for the modal panel (e.g. max-width) */
  className?: string
}

/**
 * Renders its children into a portal at document.body, as a true
 * viewport-fixed overlay:
 * - always sits on top of the whole app (not clipped/scrolled by a parent)
 * - freezes background scroll while open
 * - closes on click/tap outside the panel
 * - closes on Escape
 */
export default function Modal({ onClose, children, className }: ModalProps) {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)

    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [onClose])

  if (!mounted) return null

  return createPortal(
    <div
      className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center sm:p-4 bg-black/70 backdrop-blur-sm animate-fade-in"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div
        className={cn(
          'w-full bg-card border border-border rounded-t-3xl sm:rounded-2xl shadow-2xl shadow-black/50 overflow-hidden flex flex-col max-h-[94vh] sm:max-h-[90vh] pb-safe',
          className,
        )}
        onMouseDown={(event) => event.stopPropagation()}
      >
        {children}
      </div>
    </div>,
    document.body,
  )
}
