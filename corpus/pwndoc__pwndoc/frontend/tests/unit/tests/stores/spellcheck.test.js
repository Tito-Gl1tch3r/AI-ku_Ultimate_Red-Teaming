import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ALL_CATEGORIES, useSpellcheckStore } from '@/stores/spellcheck'

describe('spellcheck store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('loads persisted settings and exposes getters', () => {
    localStorage.setItem('spellcheckEnabled', 'false')
    localStorage.setItem('spellcheckDisabledCategories', 'STYLE,,TYPOS')
    const store = useSpellcheckStore()
    store.loadFromStorage()
    expect(store.enabled).toBe(false)
    expect(store.isActive(true)).toBe(false)
    expect(store.disabledCategoriesString).toBe('STYLE,TYPOS')
    expect(store.isCategoryEnabled('STYLE')).toBe(false)
    expect(ALL_CATEGORIES).toContainEqual({ id: 'STYLE' })
  })

  it('uses the global setting when no override is persisted', () => {
    const store = useSpellcheckStore()
    store.loadFromStorage()
    expect(store.enabled).toBeNull()
    expect(store.isActive(true)).toBe(true)
    expect(store.isActive(false)).toBe(false)
  })

  it('saves true, false and inherited settings', () => {
    const store = useSpellcheckStore()
    store.setEnabled(true)
    expect(localStorage.getItem('spellcheckEnabled')).toBe('true')
    store.setEnabled(false)
    expect(localStorage.getItem('spellcheckEnabled')).toBe('false')
    store.setEnabled(null)
    expect(localStorage.getItem('spellcheckEnabled')).toBeNull()
  })

  it('persists category toggles and removes empty storage', () => {
    const store = useSpellcheckStore()
    store.toggleCategory('STYLE')
    expect(store.disabledCategories).toEqual(['STYLE'])
    expect(localStorage.getItem('spellcheckDisabledCategories')).toBe('STYLE')
    store.toggleCategory('STYLE')
    expect(store.disabledCategories).toEqual([])
    expect(localStorage.getItem('spellcheckDisabledCategories')).toBeNull()
  })
})
