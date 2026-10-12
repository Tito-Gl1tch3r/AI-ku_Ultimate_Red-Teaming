// @vitest-environment jsdom
/** AppearanceRow behavior: dark-only product, single Dark cube always
 * selected; Light and System were removed with the light palette. */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { createSnapshotStore, type SessionListState, type WorkspaceListState } from '@pentest-harness/dsh-client-runtime/client'
import { bindSnapshotSelector } from '@pentest-harness/dsh-client-test-runtime'
import { AppearanceRow } from '../src/client/AppearanceRow.tsx'
import type { AppearanceRowComponentProps } from '../src/client/AppearanceRow.tsx'
import { createAppearanceRowStore } from '../src/client/settings-store.ts'
import type { ThemePreference } from '../src/client/index.ts'

afterEach(cleanup)

const COPY: Record<string, string> = {
  'appearance.title': 'Appearance',
  'appearance.dark': 'Dark',
}

/** Empty global standard-kit hooks (the row reads neither). */
function emptySessions() {
  const store = createSnapshotStore<SessionListState>(
    { ids: [], byId: {}, current: undefined, phase: 'ready', subagentsByParent: {}, jobsBySession: {}, currentAddress: undefined })
  return bindSnapshotSelector(store)
}
function emptyWorkspaces() {
  const store = createSnapshotStore<WorkspaceListState>({
    items: [], archivedSessionIds: [], state: 'idle', phase: 'ready', error: null,
    baselinesReady: true, recentWorkspaceId: undefined,
  })
  return bindSnapshotSelector(store)
}

function mount(preference: ThemePreference = 'system') {
  // Real store instance — the sanctioned zero-machinery path for tests.
  const store = createAppearanceRowStore().create()
  store.actions.sync(preference, 0)
  const setTheme = vi.fn()
  const props: AppearanceRowComponentProps = {
    useSessions: emptySessions(),
    useWorkspaces: emptyWorkspaces(),
    useStore: bindSnapshotSelector(store),
    actions: store.actions,
    t: (key: string) => COPY[key] ?? key,
    setTheme,
  }
  render(<AppearanceRow {...props} />)
  return { store, setTheme }
}

describe('AppearanceRow', () => {
  it('renders the title and the single always-selected Dark cube', () => {
    mount('dark')
    expect(screen.getByText('Appearance')).toBeDefined()
    expect(screen.getByRole('button', { name: /Dark/ }).getAttribute('aria-pressed')).toBe('true')
    // The light palette was removed: no Light or System cubes exist.
    expect(screen.queryByRole('button', { name: /Light/ })).toBeNull()
    expect(screen.queryByRole('button', { name: /System/ })).toBeNull()
  })
})
