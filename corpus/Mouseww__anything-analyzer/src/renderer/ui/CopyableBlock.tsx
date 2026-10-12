import React, { useState, useCallback } from 'react'
import styles from './CopyableBlock.module.css'
import { IconCheck } from './Icons'

interface CopyableBlockProps {
  content: string
  label?: string
  maxHeight?: number
}

export const CopyableBlock: React.FC<CopyableBlockProps> = ({ content, label, maxHeight = 400 }) => {
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // fallback
    }
  }, [content])

  return (
    <div className={styles.container}>
      {label && <div className={styles.label}>{label}</div>}
      <div className={styles.block} style={{ maxHeight }}>
        <pre className={styles.content}>{content}</pre>
        <button className={styles.copyBtn} onClick={handleCopy} title="Copy">
          {copied ? (
            <IconCheck size={12} />
          ) : (
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
            </svg>
          )}
        </button>
      </div>
    </div>
  )
}
