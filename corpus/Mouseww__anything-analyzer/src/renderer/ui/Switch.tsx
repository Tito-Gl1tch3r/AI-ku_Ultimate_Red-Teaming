import React from 'react'
import styles from './Switch.module.css'

export interface SwitchProps {
  checked?: boolean
  defaultChecked?: boolean
  onChange?: (checked: boolean) => void
  disabled?: boolean
  className?: string
}

export const Switch: React.FC<SwitchProps> = ({
  checked: controlledChecked,
  defaultChecked = false,
  onChange,
  disabled = false,
  className,
}) => {
  const [internalChecked, setInternalChecked] = React.useState(defaultChecked)
  const isChecked = controlledChecked !== undefined ? controlledChecked : internalChecked

  const toggle = () => {
    if (disabled) return
    const next = !isChecked
    if (controlledChecked === undefined) {
      setInternalChecked(next)
    }
    onChange?.(next)
  }

  return (
    <button
      type="button"
      role="switch"
      aria-checked={isChecked}
      className={`${styles.switch} ${isChecked ? styles.checked : ''} ${className ?? ''}`}
      disabled={disabled}
      onClick={toggle}
    >
      <span className={styles.knob} />
    </button>
  )
}
