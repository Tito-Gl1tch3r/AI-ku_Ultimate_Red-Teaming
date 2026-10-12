import React, { useState, useRef, useEffect } from 'react'
import { Button } from './Button'
import styles from './Popconfirm.module.css'

export interface PopconfirmProps {
  title: string
  onConfirm: () => void
  onCancel?: () => void
  okText?: string
  cancelText?: string
  /** Horizontal alignment of the popover. Default: 'center' */
  align?: 'center' | 'end'
  children: React.ReactNode
}

export const Popconfirm: React.FC<PopconfirmProps> = ({
  title,
  onConfirm,
  onCancel,
  okText = 'OK',
  cancelText = 'Cancel',
  align = 'center',
  children,
}) => {
  const [open, setOpen] = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const handleClickOutside = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  const handleConfirm = () => {
    setOpen(false)
    onConfirm()
  }

  const handleCancel = () => {
    setOpen(false)
    onCancel?.()
  }

  return (
    <div ref={wrapperRef} className={styles.wrapper}>
      <div
        onClick={(e: React.MouseEvent) => {
          e.stopPropagation()
          setOpen(!open)
        }}
      >
        {children}
      </div>
      {open && (
        <div className={`${styles.popover} ${align === 'end' ? styles.popoverEnd : ''}`}>
          <div className={styles.message}>{title}</div>
          <div className={styles.actions}>
            <Button size="sm" onClick={handleCancel}>
              {cancelText}
            </Button>
            <Button size="sm" variant="danger" onClick={handleConfirm}>
              {okText}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
