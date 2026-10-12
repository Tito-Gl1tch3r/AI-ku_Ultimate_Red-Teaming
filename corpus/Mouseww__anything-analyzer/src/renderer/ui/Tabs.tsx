import React from 'react'
import styles from './Tabs.module.css'

export interface TabItem {
  key: string
  label: React.ReactNode
  icon?: React.ReactNode
  badge?: string | number
  children?: React.ReactNode
}

export interface TabsProps {
  items: TabItem[]
  activeKey: string
  onChange: (key: string) => void
  /** Extra content rendered at the right end of the tab bar */
  extra?: React.ReactNode
  className?: string
  style?: React.CSSProperties
}

export const Tabs: React.FC<TabsProps> = ({
  items,
  activeKey,
  onChange,
  extra,
  className,
  style,
}) => {
  const activeItem = items.find((i) => i.key === activeKey)

  return (
    <div className={`${styles.tabs} ${className ?? ''}`} style={style}>
      <div className={styles.tabBar}>
        {items.map((item) => (
          <button
            key={item.key}
            className={`${styles.tab} ${item.key === activeKey ? styles.active : ''}`}
            onClick={() => onChange(item.key)}
          >
            {item.icon && <span className={styles.tabIcon}>{item.icon}</span>}
            <span>{item.label}</span>
            {item.badge !== undefined && (
              <span className={styles.tabBadge}>{item.badge}</span>
            )}
          </button>
        ))}
        {extra && <div className={styles.tabBarExtra}>{extra}</div>}
      </div>
      <div className={styles.tabContent}>{activeItem?.children}</div>
    </div>
  )
}
