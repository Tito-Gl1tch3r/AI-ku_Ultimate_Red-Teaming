import React, { useState, useCallback, useRef } from 'react'
import { createPortal } from 'react-dom'
import { Button } from '../ui'

/**
 * useConfirm — lightweight confirmation dialog rendered via Portal.
 * Cross-platform safe (no window.confirm dependency).
 */
export function useConfirm() {
  const [state, setState] = useState<{
    message: string
    okText?: string
    cancelText?: string
  } | null>(null)

  const resolveRef = useRef<((ok: boolean) => void) | null>(null)

  const confirm = useCallback(
    (message: string, opts?: { okText?: string; cancelText?: string }): Promise<boolean> => {
      return new Promise((resolve) => {
        resolveRef.current = resolve
        setState({ message, ...opts })
      })
    },
    [],
  )

  const handleOk = useCallback(() => {
    resolveRef.current?.(true)
    resolveRef.current = null
    setState(null)
  }, [])

  const handleCancel = useCallback(() => {
    resolveRef.current?.(false)
    resolveRef.current = null
    setState(null)
  }, [])

  const ConfirmDialog = state
    ? createPortal(
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 9999,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(0,0,0,0.35)',
          }}
          onClick={handleCancel}
        >
          <div
            style={{
              background: 'var(--color-frame)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-lg)',
              boxShadow: 'var(--shadow-lg)',
              padding: '20px 24px',
              minWidth: 280,
              maxWidth: 400,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              style={{
                fontSize: 'var(--font-size-base)',
                color: 'var(--text-secondary)',
                lineHeight: 'var(--line-height-normal)',
                marginBottom: 16,
              }}
            >
              {state.message}
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <Button size="sm" onClick={handleCancel}>
                {state.cancelText || 'Cancel'}
              </Button>
              <Button size="sm" variant="danger" onClick={handleOk}>
                {state.okText || 'OK'}
              </Button>
            </div>
          </div>
        </div>,
        document.body,
      )
    : null

  return { confirm, ConfirmDialog }
}
