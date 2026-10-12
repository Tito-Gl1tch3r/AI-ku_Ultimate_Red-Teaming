import React, { useState, forwardRef } from 'react'
import styles from './Input.module.css'

/* ---- Text Input ---- */
export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  inputSize?: 'sm' | 'md' | 'lg'
  suffix?: React.ReactNode
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ inputSize = 'md', suffix, className, ...rest }, ref) => {
    const cls = [styles.input, inputSize !== 'md' && styles[inputSize], className]
      .filter(Boolean)
      .join(' ')

    if (suffix) {
      return (
        <div className={styles.inputWrapper}>
          <input ref={ref} className={cls} {...rest} />
          <span className={styles.suffix}>{suffix}</span>
        </div>
      )
    }

    return <input ref={ref} className={cls} {...rest} />
  }
)
Input.displayName = 'Input'

/* ---- Textarea ---- */
export interface TextAreaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  autoSize?: boolean | { minRows?: number; maxRows?: number }
}

export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(
  ({ autoSize, className, style, ...rest }, ref) => {
    const cls = [styles.textarea, className].filter(Boolean).join(' ')

    const handleInput: React.FormEventHandler<HTMLTextAreaElement> = (e) => {
      if (autoSize) {
        const el = e.currentTarget
        el.style.height = 'auto'
        const minRows = typeof autoSize === 'object' ? autoSize.minRows ?? 2 : 2
        const maxRows = typeof autoSize === 'object' ? autoSize.maxRows ?? 10 : 10
        const lineHeight = 20
        const minH = minRows * lineHeight
        const maxH = maxRows * lineHeight
        el.style.height = `${Math.min(Math.max(el.scrollHeight, minH), maxH)}px`
      }
    }

    return <textarea ref={ref} className={cls} onInput={handleInput} style={style} {...rest} />
  }
)
TextArea.displayName = 'TextArea'

/* ---- Password Input ---- */
export interface PasswordInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type' | 'size'> {
  inputSize?: 'sm' | 'md' | 'lg'
}

export const PasswordInput = forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ inputSize = 'md', className, ...rest }, ref) => {
    const [visible, setVisible] = useState(false)
    const cls = [styles.input, inputSize !== 'md' && styles[inputSize], className]
      .filter(Boolean)
      .join(' ')

    return (
      <div className={styles.passwordWrapper}>
        <input ref={ref} type={visible ? 'text' : 'password'} className={cls} {...rest} />
        <button
          type="button"
          className={styles.passwordToggle}
          onClick={() => setVisible(!visible)}
          tabIndex={-1}
        >
          {visible ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
              <line x1="1" y1="1" x2="23" y2="23" />
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          )}
        </button>
      </div>
    )
  }
)
PasswordInput.displayName = 'PasswordInput'
