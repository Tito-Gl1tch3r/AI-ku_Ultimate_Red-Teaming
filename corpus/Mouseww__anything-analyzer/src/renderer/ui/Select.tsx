import React, { useState, useRef, useEffect } from 'react'
import styles from './Select.module.css'

export interface SelectOption {
  label: string
  value: string
  disabled?: boolean
}

export interface SelectProps {
  options: SelectOption[]
  value?: string
  defaultValue?: string
  onChange?: (value: string) => void
  placeholder?: string
  disabled?: boolean
  className?: string
  style?: React.CSSProperties
}

export const Select: React.FC<SelectProps> = ({
  options,
  value: controlledValue,
  defaultValue,
  onChange,
  placeholder = 'Select...',
  disabled = false,
  className,
  style,
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [internalValue, setInternalValue] = useState(defaultValue ?? '')
  const wrapperRef = useRef<HTMLDivElement>(null)

  const value = controlledValue !== undefined ? controlledValue : internalValue
  const selectedOption = options.find((o) => o.value === value)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  const handleSelect = (opt: SelectOption) => {
    if (opt.disabled) return
    if (controlledValue === undefined) {
      setInternalValue(opt.value)
    }
    onChange?.(opt.value)
    setIsOpen(false)
  }

  return (
    <div ref={wrapperRef} className={`${styles.wrapper} ${className ?? ''}`} style={style}>
      <button
        type="button"
        className={`${styles.trigger} ${isOpen ? styles.open : ''}`}
        disabled={disabled}
        onClick={() => !disabled && setIsOpen(!isOpen)}
      >
        {selectedOption ? (
          <span>{selectedOption.label}</span>
        ) : (
          <span className={styles.placeholder}>{placeholder}</span>
        )}
        <svg
          className={`${styles.arrow} ${isOpen ? styles.up : ''}`}
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {isOpen && (
        <div className={styles.dropdown}>
          {options.map((opt) => (
            <div
              key={opt.value}
              className={`${styles.option} ${opt.value === value ? styles.selected : ''} ${opt.disabled ? styles.disabled : ''}`}
              onClick={() => handleSelect(opt)}
            >
              {opt.label}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
