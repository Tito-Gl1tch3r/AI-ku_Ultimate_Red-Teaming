import React, { createContext, useContext, useCallback } from 'react'
import { zh } from './zh'
import { en } from './en'
import type { LocaleKey } from './zh'

export type Locale = 'zh' | 'en'

const localeMap: Record<Locale, Record<string, string>> = { zh, en }

interface LocaleContextValue {
  locale: Locale
  t: (key: LocaleKey, vars?: Record<string, string | number>) => string
}

const LocaleContext = createContext<LocaleContextValue>({
  locale: 'zh',
  t: (key) => key,
})

export function LocaleProvider({
  locale,
  children,
}: {
  locale: Locale
  children: React.ReactNode
}) {
  const t = useCallback(
    (key: LocaleKey, vars?: Record<string, string | number>) => {
      let text = localeMap[locale]?.[key] ?? localeMap.zh[key] ?? key
      if (vars) {
        Object.entries(vars).forEach(([k, v]) => {
          text = text.replace(`{${k}}`, String(v))
        })
      }
      return text
    },
    [locale]
  )

  return React.createElement(LocaleContext.Provider, { value: { locale, t } }, children)
}

export function useLocale() {
  return useContext(LocaleContext)
}

export type { LocaleKey }
