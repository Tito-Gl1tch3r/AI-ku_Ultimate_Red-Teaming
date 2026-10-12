import { describe, it, expect, vi } from 'vitest'
import { createTestWrapper } from '../../test-utils'
import QaResultsPanel from '@/components/qa-results-panel.vue'

vi.mock('@/boot/i18n', () => ({
  $t: vi.fn((key) => key)
}))

const messages = {
  'en-US': {
    auditQa: {
      outdatedBanner: 'These results are out of date — content changed since the last run. Re-run recommended.',
      errors: 'Errors',
      warnings: 'Warnings',
      infos: 'Infos',
      total: 'Total',
      lastRun: 'Last run',
      noIssues: 'No issues flagged',
      noResultsYet: 'No QA results yet.',
      running: 'Running...',
      runProgrammatic: 'Run Built-in Checks',
      runAi: 'Run AI Checks',
      runAll: 'Run All',
      aiReview: 'AI review — verify before acting'
    }
  }
}

const baseCounts = { total: 1, error: 0, warning: 1, info: 0 }

function createWrapper(props = {}) {
  return createTestWrapper(QaResultsPanel, {
    messages,
    props: {
      title: 'QA Review',
      hasReportData: true,
      counts: baseCounts,
      groupedIssues: [],
      ...props
    },
    global: {
      stubs: {
        'q-banner': { template: '<div><slot /><slot name="action" /></div>' },
        // Quasar auto-stubs drop named/scoped slots by default — forward `header` explicitly
        // so the group header (label + "Go to section" button) is actually testable.
        'q-expansion-item': { template: '<div><div class="qa-group-header"><slot name="header" /></div><slot /></div>' }
      }
    }
  })
}

describe('QaResultsPanel header', () => {
  it('renders the title without a checklist icon', () => {
    const wrapper = createWrapper()

    expect(wrapper.text()).toContain('QA Review')
    expect(wrapper.html()).not.toContain('fa-list-check')
  })
})

describe('QaResultsPanel outdated banner', () => {
  it('shows the outdated banner when the report is stale', () => {
    const wrapper = createWrapper({ outdated: true })

    expect(wrapper.text()).toContain('These results are out of date')
  })

  it('does not show the outdated banner when the report is current', () => {
    const wrapper = createWrapper({ outdated: false })

    expect(wrapper.text()).not.toContain('These results are out of date')
  })

  it('dismisses the banner when the close button is clicked', async () => {
    const wrapper = createWrapper({ outdated: true })

    await wrapper.find('[data-testid="qa-outdated-dismiss"]').trigger('click')

    expect(wrapper.text()).not.toContain('These results are out of date')
  })

  it('re-runs QA from the banner with the last run scope', async () => {
    const wrapper = createWrapper({ outdated: true, runScope: 'programmatic' })

    await wrapper.find('[data-testid="qa-outdated-rerun"]').trigger('click')

    // Programmatic runs never carry a provider (the second arg is forced empty).
    expect(wrapper.emitted('run')).toEqual([['programmatic', '']])
  })

  it('forwards the selected provider on an AI re-run', async () => {
    const wrapper = createWrapper({ outdated: true, runScope: 'ai', showAiAction: true })
    wrapper.vm.selectedProvider = 'anthropic'

    wrapper.vm.emitRun('ai')

    expect(wrapper.emitted('run')).toEqual([['ai', 'anthropic']])
  })

  it('can render the outdated banner as an actionless hint', () => {
    const wrapper = createWrapper({
      outdated: true,
      showOutdatedRerun: false,
      showOutdatedDismiss: false
    })

    expect(wrapper.text()).toContain('These results are out of date')
    expect(wrapper.find('[data-testid="qa-outdated-rerun"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="qa-outdated-dismiss"]').exists()).toBe(false)
  })

  it('re-shows the banner after a fresh run completes while still outdated', async () => {
    const wrapper = createWrapper({ outdated: true })

    await wrapper.find('[data-testid="qa-outdated-dismiss"]').trigger('click')
    expect(wrapper.text()).not.toContain('These results are out of date')

    await wrapper.setProps({ loading: true })
    await wrapper.setProps({ loading: false, outdated: true })

    expect(wrapper.text()).toContain('These results are out of date')
  })
})

describe('QaResultsPanel AI-sourced issue caption', () => {
  const groupedIssues = [{
    label: 'General',
    issues: [
      {
        severity: 'warning',
        category: 'completeness',
        title: 'Structural issue',
        message: 'Missing field',
        location: 'report',
        source: 'structural'
      },
      {
        severity: 'warning',
        category: 'redaction',
        title: 'AI issue',
        message: 'Sensitive data found',
        location: 'report',
        source: 'ai'
      }
    ]
  }]

  it('shows the AI review caption only on AI-sourced issues', () => {
    const wrapper = createWrapper({ groupedIssues })

    expect(wrapper.text()).toContain('AI review — verify before acting')
  })

  it('does not show the AI review caption when there are no AI-sourced issues', () => {
    const wrapper = createWrapper({
      groupedIssues: [{
        label: 'General',
        issues: [groupedIssues[0].issues[0]]
      }]
    })

    expect(wrapper.text()).not.toContain('AI review — verify before acting')
  })
})

describe('QaResultsPanel info tile', () => {
  it('renders an info stat tile alongside errors, warnings, and total', () => {
    const wrapper = createWrapper({ counts: { total: 4, error: 1, warning: 1, info: 2 } })

    expect(wrapper.find('.qa-stat--info .qa-stat__value').text()).toBe('2')
  })

  it('filters to info severity when the info tile is clicked', async () => {
    const wrapper = createWrapper({ counts: { total: 4, error: 1, warning: 1, info: 2 } })

    await wrapper.find('.qa-stat--info').trigger('click')

    expect(wrapper.emitted('update:severityFilter')).toEqual([['info']])
  })
})

describe('QaResultsPanel group expansion', () => {
  const groupedIssues = [
    { key: 'report', label: 'Report', issues: [] },
    { key: 'general', label: 'General', issues: [] }
  ]

  it('shows one collapse-all toolbar action when every group is expanded', () => {
    const wrapper = createWrapper({ groupedIssues })
    const toggle = wrapper.get('[data-testid="qa-groups-toggle"]')

    expect(wrapper.vm.expandedGroups).toEqual({ report: true, general: true })
    expect(toggle.attributes('aria-label')).toBe('collapseAll')
    expect(toggle.attributes('icon')).toBe('unfold_less')
  })

  it('collapses all groups, then offers to expand them again', async () => {
    const wrapper = createWrapper({ groupedIssues })

    await wrapper.get('[data-testid="qa-groups-toggle"]').trigger('click')

    expect(wrapper.vm.expandedGroups).toEqual({ report: false, general: false })
    expect(wrapper.get('[data-testid="qa-groups-toggle"]').attributes('aria-label')).toBe('expandAll')
    expect(wrapper.get('[data-testid="qa-groups-toggle"]').attributes('icon')).toBe('unfold_more')

    await wrapper.get('[data-testid="qa-groups-toggle"]').trigger('click')
    expect(wrapper.vm.expandedGroups).toEqual({ report: true, general: true })
  })

  it('expands every group from a partially expanded state', async () => {
    const wrapper = createWrapper({ groupedIssues })
    wrapper.vm.expandedGroups.general = false
    await wrapper.vm.$nextTick()

    await wrapper.get('[data-testid="qa-groups-toggle"]').trigger('click')

    expect(wrapper.vm.expandedGroups).toEqual({ report: true, general: true })
  })

  it('preserves existing group state and opens newly arriving groups', async () => {
    const wrapper = createWrapper({ groupedIssues })
    wrapper.vm.expandedGroups.report = false

    await wrapper.setProps({
      groupedIssues: [
        groupedIssues[0],
        { key: 'network', label: 'Network', issues: [] }
      ]
    })

    expect(wrapper.vm.expandedGroups).toEqual({ report: false, network: true })
  })

  it('hides the bulk action when fewer than two groups are visible', () => {
    const wrapper = createWrapper({ groupedIssues: [groupedIssues[0]] })

    expect(wrapper.find('[data-testid="qa-groups-toggle"]').exists()).toBe(false)
  })
})

describe('QaResultsPanel running indicator', () => {
  it('shows the progress bar and in-progress line while a run is in flight', () => {
    const wrapper = createWrapper({ running: true, startedAt: Date.now() })

    expect(wrapper.find('.qa-run-progress').exists()).toBe(true)
    expect(wrapper.find('.qa-run-inprogress').exists()).toBe(true)
    expect(wrapper.find('.qa-results-panel--running').exists()).toBe(true)
  })

  it('does not show the in-progress indicators when idle', () => {
    const wrapper = createWrapper({ running: false })

    expect(wrapper.find('.qa-run-progress').exists()).toBe(false)
    expect(wrapper.find('.qa-run-inprogress').exists()).toBe(false)
    expect(wrapper.find('.qa-results-panel--running').exists()).toBe(false)
  })

  it('keeps the previous report visible while running (does not replace it with a spinner)', () => {
    const wrapper = createWrapper({
      running: true,
      startedAt: Date.now(),
      groupedIssues: [{
        label: 'General',
        issues: [{ severity: 'warning', category: 'completeness', title: 'Issue', message: 'msg', location: 'report', source: 'structural' }]
      }]
    })

    expect(wrapper.text()).toContain('Issue')
    expect(wrapper.find('.qa-run-progress').exists()).toBe(true)
  })
})

describe('QaResultsPanel finding-row rendering', () => {
  const findingRowsGroup = {
    key: 'category:Injection',
    label: 'Findings > Injection',
    findingRows: [{
      key: 'finding-1',
      title: 'XSS',
      findingId: 'finding-1',
      issues: [
        { location: 'finding:finding-1::XSS', title: 'Still needs redaction', message: 'msg', severity: 'warning', category: 'redaction' },
        { location: 'finding:finding-1::XSS/description', title: 'Missing detail', message: 'msg', severity: 'error', category: 'completeness' }
      ]
    }]
  }

  function createFindingRowWrapper() {
    return createWrapper({ groupedIssues: [findingRowsGroup], showNavigation: true })
  }

  it('renders exactly one Go to finding button for the whole row, on the title, not per issue', () => {
    const wrapper = createFindingRowWrapper()
    const findingRow = wrapper.find('.qa-finding-row')
    const buttons = findingRow.findAll('q-btn')
    expect(buttons).toHaveLength(1)
    expect(buttons[0].attributes('label')).toBe('auditQa.goToFinding')
  })

  it('does not render any button on individual issue rows', () => {
    const wrapper = createFindingRowWrapper()
    const rows = wrapper.findAll('.qa-issue')
    expect(rows).toHaveLength(2)
    rows.forEach((row) => expect(row.find('q-btn').exists()).toBe(false))
  })

  it('emits navigate with the first issue\'s location and the row on click', async () => {
    const wrapper = createFindingRowWrapper()

    await wrapper.find('.qa-finding-row').find('q-btn').trigger('click')

    const emitted = wrapper.emitted('navigate')
    expect(emitted).toHaveLength(1)
    expect(emitted[0][0]).toBe('finding:finding-1::XSS')
    expect(emitted[0][1]).toMatchObject({ key: expect.anything() })
  })
})

describe('QaResultsPanel flat-group navigation', () => {
  it('renders a Go to section button on a general/section group header', () => {
    const wrapper = createWrapper({
      showNavigation: true,
      groupedIssues: [{ key: 'general', label: 'General information', issues: [
        { location: 'general', title: 'Missing scope', message: 'msg', severity: 'warning', category: 'completeness' }
      ] }]
    })

    const buttons = wrapper.find('.qa-groups').findAll('q-btn')
    expect(buttons).toHaveLength(1)
    expect(buttons[0].attributes('label')).toBe('auditQa.goToSection')
  })

  it('does not render any button on the Report group', () => {
    const wrapper = createWrapper({
      showNavigation: true,
      groupedIssues: [{ key: 'report', label: 'Report', issues: [
        { location: 'report', title: 'Instructions issue', message: 'msg', severity: 'warning', category: 'instructions' }
      ] }]
    })

    expect(wrapper.find('.qa-groups').find('q-btn').exists()).toBe(false)
  })

  it('does not render a button on individual issues within a flat group', () => {
    const wrapper = createWrapper({
      showNavigation: true,
      groupedIssues: [{ key: 'general', label: 'General information', issues: [
        { location: 'general', title: 'Missing scope', message: 'msg', severity: 'warning', category: 'completeness' }
      ] }]
    })

    expect(wrapper.find('.qa-issue q-btn').exists()).toBe(false)
  })

  it('emits navigate with the location on click', async () => {
    const wrapper = createWrapper({
      showNavigation: true,
      groupedIssues: [{ key: 'section:Executive Summary', label: 'Executive Summary', issues: [
        { location: 'section:Executive Summary', title: 'Missing detail', message: 'msg', severity: 'warning', category: 'completeness' }
      ] }]
    })

    await wrapper.find('.qa-groups').find('q-btn').trigger('click')

    expect(wrapper.emitted('navigate')).toEqual([['section:Executive Summary']])
  })
})

describe('QaResultsPanel AI-unavailable banner', () => {
  it('promotes AI-unavailable messages to a banner instead of a buried row', () => {
    const wrapper = createWrapper({
      aiUnavailableMessages: ['Automated content review could not run: provider not configured']
    })

    expect(wrapper.find('.qa-ai-unavailable-banner').exists()).toBe(true)
    expect(wrapper.text()).toContain('Automated content review could not run: provider not configured')
  })

  it('does not render the banner when there are no AI-unavailable messages', () => {
    const wrapper = createWrapper({ aiUnavailableMessages: [] })

    expect(wrapper.find('.qa-ai-unavailable-banner').exists()).toBe(false)
  })
})

describe('QaResultsPanel run actions', () => {
  it('collapses the scope buttons into a single "Run again" control once a report exists', () => {
    const wrapper = createWrapper()

    expect(wrapper.find('[data-testid="qa-run-again"]').exists()).toBe(true)
  })

  it('keeps the stacked scope buttons before the first run', () => {
    const wrapper = createWrapper({ hasReportData: false })

    expect(wrapper.find('[data-testid="qa-run-again"]').exists()).toBe(false)
  })

  it('can restrict the main rerun control to outdated reports', async () => {
    const wrapper = createWrapper({ rerunOnlyWhenOutdated: true, outdated: false })

    expect(wrapper.find('[data-testid="qa-run-again"]').exists()).toBe(false)

    await wrapper.setProps({ outdated: true })
    expect(wrapper.find('[data-testid="qa-run-again"]').exists()).toBe(true)
  })

  it('repeats the last run scope from the main button and offers the other scopes in the menu', async () => {
    const wrapper = createWrapper({ runScope: 'ai' })

    await wrapper.find('[data-testid="qa-run-again"]').trigger('click')
    // The second arg is the selected provider (empty = org default); programmatic forces empty.
    expect(wrapper.emitted('run')).toEqual([['ai', '']])

    // The default scope is on the main button, so it is not repeated in the dropdown.
    expect(wrapper.find('[data-testid="qa-run-scope-ai"]').exists()).toBe(false)

    await wrapper.find('[data-testid="qa-run-scope-programmatic"]').trigger('click')
    expect(wrapper.emitted('run')).toEqual([['ai', ''], ['programmatic', '']])
  })

  it('defaults "Run again" to the full run when no scope was recorded', async () => {
    const wrapper = createWrapper()

    await wrapper.find('[data-testid="qa-run-again"]').trigger('click')
    expect(wrapper.emitted('run')).toEqual([['all', '']])
  })
})

describe('QaResultsPanel dismiss controls', () => {
  const dismissableGroups = [{
    key: 'catalog',
    label: 'Cross-template checks',
    issues: [{
      severity: 'warning',
      category: 'duplicates',
      title: 'Possible duplicate',
      message: 'Looks the same',
      location: 'database',
      source: 'structural',
      key: 'k1',
      dismissed: false,
      linkedTemplates: [
        { id: 'v1', title: 'SQL Injection' },
        { id: 'v2', title: 'SQLi (copy)' }
      ]
    }]
  }]

  it('shows the status filter chips only when enabled and emits the chosen status', async () => {
    expect(createWrapper().find('[data-testid="qa-status-filter-active"]').exists()).toBe(false)

    const wrapper = createWrapper({ showStatusFilter: true, statusCounts: { outdated: 2, resolved: 3 } })
    expect(wrapper.find('[data-testid="qa-status-filter-active"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="qa-status-filter-outdated"]').text()).toContain('(2)')
    expect(wrapper.find('[data-testid="qa-status-filter-resolved"]').text()).toContain('(3)')

    await wrapper.find('[data-testid="qa-status-filter-resolved"]').trigger('click')
    expect(wrapper.emitted('update:statusFilter')).toEqual([['resolved']])
  })

  it('renders the run-again hint under the button only when provided', () => {
    expect(createWrapper().find('[data-testid="qa-run-again-caption"]').exists()).toBe(false)
    expect(createWrapper({ runAgainHint: 'only outdated re-run' })
      .find('[data-testid="qa-run-again-caption"]').text()).toBe('only outdated re-run')
  })

  it('shows the text filter only when enabled', () => {
    expect(createWrapper().find('[data-testid="qa-text-filter"]').exists()).toBe(false)
    expect(createWrapper({ showTextFilter: true }).find('[data-testid="qa-text-filter"]').exists()).toBe(true)
  })

  it('emits dismiss with the clicked issue', async () => {
    const wrapper = createWrapper({ showDismissActions: true, groupedIssues: dismissableGroups })

    await wrapper.find('[data-testid="qa-dismiss-issue"]').trigger('click')

    const emitted = wrapper.emitted('dismiss')
    expect(emitted).toHaveLength(1)
    expect(emitted[0][0]).toMatchObject({ key: 'k1' })
  })

  it('navigates to each linked template from catalog issue chips', async () => {
    const wrapper = createWrapper({ groupedIssues: dismissableGroups })

    const chips = wrapper.findAll('[data-testid="qa-linked-template"]')
    expect(chips).toHaveLength(2)

    await chips[1].trigger('click')
    expect(wrapper.emitted('navigate')).toEqual([['database', { findingId: 'v2' }]])
  })
})
