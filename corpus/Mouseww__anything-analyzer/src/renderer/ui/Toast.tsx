import React, { createContext, useContext, useState, useCallback, useRef } from 'react'
import { createPortal } from 'react-dom'
import styles from './Toast.module.css'

type ToastType = 'success' | 'error' | 'warning' | 'info'

interface ToastItem {
  id: number
  type: ToastType
  message: string
  exiting?: boolean
}

interface ToastContextValue {
  success: (message: string) => void
  error: (message: string) => void
  warning: (message: string) => void
  info: (message: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

const TOAST_ICONS: Record<ToastType, string> = {
  success: '\u2713',
  error: '\u2717',
  warning: '\u26A0',
  info: '\u2139',
}

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const counterRef = useRef(0)

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, exiting: true } : t)))
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 200)
  }, [])

  const addToast = useCallback(
    (type: ToastType, message: string) => {
      const id = ++counterRef.current
      setToasts((prev) => [...prev, { id, type, message }])
      setTimeout(() => removeToast(id), 3000)
    },
    [removeToast]
  )

  const contextValue: ToastContextValue = {
    success: useCallback((msg: string) => addToast('success', msg), [addToast]),
    error: useCallback((msg: string) => addToast('error', msg), [addToast]),
    warning: useCallback((msg: string) => addToast('warning', msg), [addToast]),
    info: useCallback((msg: string) => addToast('info', msg), [addToast]),
  }

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      {createPortal(
        <div className={styles.container}>
          {toasts.map((toast) => (
            <div
              key={toast.id}
              className={`${styles.toast} ${styles[toast.type]} ${toast.exiting ? styles.exiting : ''}`}
            >
              <span className={styles.icon}>{TOAST_ICONS[toast.type]}</span>
              <span className={styles.text}>{toast.message}</span>
              <button className={styles.closeBtn} onClick={() => removeToast(toast.id)}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
          ))}
        </div>,
        document.body
      )}
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return ctx
}
