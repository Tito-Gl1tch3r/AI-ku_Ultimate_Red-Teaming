/**
 * Appearance preference row registered into the General section item slot
 * (figma 501:30012 'Frame 2117131228'): title + preference cubes. The product
 * is dark-only, so the row shows the Dark theme as the single, always-selected
 * option; Light and System were removed with the light palette.
 */
import clsx from 'clsx'
import { IconDarkOutline16 } from '@pentest-harness/dsh-client-ui-primitives'
import type { PropsLocale, PropsRuntime, PropsStore } from '@pentest-harness/dsh-client-ui-slots'
import type { ThemePreference } from '../theme-settings.ts'
import type { ThemeKey } from './locales.ts'
import type {} from '@pentest-harness/dsh-client-ui-settings/client'
import type { createAppearanceRowStore } from './settings-store.ts'
import css from './AppearanceRow.module.css'

/** Injected business face: the preference write (t rides the standard locale seat). */
export interface AppearanceRowInjected {
  /** Switch the theme preference. */
  setTheme: (id: ThemePreference) => void
}

/** Full component props: runtime share + store share + locale seat + injected face. */
export type AppearanceRowComponentProps =
  PropsRuntime<'settings.general.item'> & PropsStore<ReturnType<typeof createAppearanceRowStore>>
  & PropsLocale<'settings.theme'> & AppearanceRowInjected

/** The single dark-only preference (figma 501:30016: Dark). */
const CUBES: readonly { id: ThemePreference; labelKey: ThemeKey; Icon: typeof IconDarkOutline16 }[] = [
  { id: 'dark', labelKey: 'appearance.dark', Icon: IconDarkOutline16 },
]

/**
 * Render the Appearance row.
 * @param props - composed slot props.
 * @returns the row element tree.
 */
export function AppearanceRow({ t, useStore }: AppearanceRowComponentProps) {
  const preference = useStore(s => s.preference)
  return (
    <div className={css.group}>
      <div className={css.title}>{t('appearance.title')}</div>
      <div className={css.cubeRow}>
        {CUBES.map(({ id, labelKey, Icon }) => (
          <button
            key={id}
            type="button"
            className={clsx(css.themeCube, preference === id && css.selected)}
            aria-pressed={preference === id}
          >
            <Icon />
            {t(labelKey)}
          </button>
        ))}
      </div>
    </div>
  )
}
