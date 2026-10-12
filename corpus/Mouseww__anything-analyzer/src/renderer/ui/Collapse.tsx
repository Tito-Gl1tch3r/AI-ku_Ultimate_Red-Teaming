import React, { useState } from 'react'
import styles from './Collapse.module.css'

interface CollapseItem {
  key: string
  label: React.ReactNode
  children: React.ReactNode
}

interface CollapseProps {
  items: CollapseItem[]
  defaultActiveKey?: string[]
  className?: string
}

export const Collapse: React.FC<CollapseProps> = ({ items, defaultActiveKey = [], className }) => {
  const [activeKeys, setActiveKeys] = useState<Set<string>>(new Set(defaultActiveKey))

  const toggle = (key: string) => {
    setActiveKeys((prev) => {
      const next = new Set(prev)
      if (next.has(key)) {
        next.delete(key)
      } else {
        next.add(key)
      }
      return next
    })
  }

  return (
    <div className={`${styles.collapse} ${className ?? ''}`}>
      {items.map((item) => {
        const isOpen = activeKeys.has(item.key)
        return (
          <div key={item.key} className={styles.panel}>
            <div className={styles.header} onClick={() => toggle(item.key)}>
              <svg
                className={`${styles.arrow} ${isOpen ? styles.arrowOpen : ''}`}
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <polyline points="9 18 15 12 9 6" />
              </svg>
              <span className={styles.label}>{item.label}</span>
            </div>
            {isOpen && <div className={styles.content}>{item.children}</div>}
          </div>
        )
      })}
    </div>
  )
}
