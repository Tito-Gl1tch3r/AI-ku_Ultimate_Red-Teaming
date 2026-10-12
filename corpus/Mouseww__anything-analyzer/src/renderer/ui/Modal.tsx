import React, { useEffect, useCallback } from 'react'
import { createPortal } from 'react-dom'
import styles from './Modal.module.css'

export interface ModalProps {
  open: boolean
  onClose: () => void
  title?: React.ReactNode
  footer?: React.ReactNode
  width?: number | string
  children: React.ReactNode
  /** If true, show a close button in the header */
  closable?: boolean
}

export const Modal: React.FC<ModalProps> = ({
  open,
  onClose,
  title,
  footer,
  width = 520,
  children,
  closable = true,
}) => {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    },
    [onClose]
  )

  useEffect(() => {
    if (open) {
      document.addEventListener('keydown', handleKeyDown)
      return () => document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open, handleKeyDown])

  if (!open) return null

  return createPortal(
    <div className={styles.backdrop} onClick={onClose}>
      <div
        className={styles.modal}
        style={{ width: typeof width === 'number' ? `${width}px` : width }}
        onClick={(e) => e.stopPropagation()}
      >
        {(title || closable) && (
          <div className={styles.header}>
            <span className={styles.title}>{title}</span>
            {closable && (
              <button className={styles.closeBtn} onClick={onClose}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            )}
          </div>
        )}
        <div className={styles.body}>{children}</div>
        {footer !== undefined && <div className={styles.footer}>{footer}</div>}
      </div>
    </div>,
    document.body
  )
}
