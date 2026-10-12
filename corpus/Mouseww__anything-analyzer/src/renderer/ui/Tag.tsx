import React from 'react'
import styles from './Tag.module.css'

export type TagColor = 'default' | 'success' | 'info' | 'warning' | 'error' | 'purple' | 'orange'

export interface TagProps {
  color?: TagColor
  /** Custom inline color (hex). Overrides color variant. */
  customColor?: string
  onClick?: () => void
  className?: string
  style?: React.CSSProperties
  children: React.ReactNode
}

export const Tag: React.FC<TagProps> = ({
  color = 'default',
  customColor,
  onClick,
  className,
  style,
  children,
}) => {
  const cls = [
    styles.tag,
    !customColor && styles[color],
    onClick && styles.clickable,
    className,
  ]
    .filter(Boolean)
    .join(' ')

  const customStyle: React.CSSProperties | undefined = customColor
    ? {
        background: `${customColor}14`,
        color: customColor,
        border: `1px solid ${customColor}26`,
        ...style,
      }
    : style

  return (
    <span className={cls} style={customStyle} onClick={onClick}>
      {children}
    </span>
  )
}
