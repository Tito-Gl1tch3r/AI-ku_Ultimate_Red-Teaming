import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { createI18n } from 'vue-i18n'

// Must mock stores/user before component import - axios.js calls useUserStore() at module scope
const { mockUserStore, mockApi } = vi.hoisted(() => ({
  mockUserStore: {
    id: '1',
    roles: '',
    isAllowed: vi.fn(() => true)
  },
  mockApi: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn()
  }
}))
vi.mock('src/stores/user', () => ({
  useUserStore: vi.fn(() => mockUserStore)
}))
vi.mock('stores/user', () => ({
  useUserStore: vi.fn(() => mockUserStore)
}))
vi.mock('src/boot/axios.js', () => ({
  default: {},
  api: mockApi
}))
vi.mock('boot/axios', () => ({
  default: {},
  api: mockApi
}))

// Mock services used by the page
vi.mock('@/services/vulnerability', () => ({
  default: {
    getVulnerabilities: vi.fn(),
    getVulnerability: vi.fn(),
    createVulnerabilities: vi.fn(),
    updateVulnerability: vi.fn(),
    deleteVulnerability: vi.fn(),
    getVulnUpdates: vi.fn(),
    dismissVulnUpdates: vi.fn(),
    mergeVulnerability: vi.fn()
  }
}))

vi.mock('@/services/data', () => ({
  default: {
    getLanguages: vi.fn(),
    getVulnerabilityTypes: vi.fn(),
    getVulnerabilityCategories: vi.fn(),
    getCustomFields: vi.fn()
  }
}))

vi.mock('@/services/utils', () => ({
  default: {
    filterCustomFields: vi.fn().mockReturnValue([]),
    htmlEncode: vi.fn(v => v),
    syncEditors: vi.fn(),
    strongPassword: vi.fn()
  }
}))

vi.mock('@/services/draft-recovery', async () => {
  const { reactive } = await vi.importActual('vue')
  return {
    default: {
      state: reactive({ current: null, revision: 0 }),
      listDrafts: vi.fn().mockResolvedValue([]),
      loadDraft: vi.fn().mockResolvedValue(null),
      saveDraft: vi.fn().mockResolvedValue({ ok: true }),
      clearDraft: vi.fn().mockResolvedValue({ ok: true }),
      clearStatus: vi.fn(),
      buildKey: vi.fn((userId, scope, refKey) => `pwndoc.draft.${userId}.${scope}.${refKey}`),
      markDraftDiscarded: vi.fn().mockResolvedValue({ ok: true }),
      isStorageAvailable: vi.fn().mockResolvedValue(true),
      DRAFT_STATUS: {
        ACTIVE: 'active_draft',
        DISCARDED: 'discarded_draft',
        SYNCED: 'synced'
      }
    }
  }
})

vi.mock('boot/i18n', () => ({
  $t: (key) => key
}))

vi.mock('quasar', async () => {
  const actual = await vi.importActual('quasar')
  return {
    ...actual,
    Dialog: {
      create: vi.fn().mockReturnValue({
        onOk: vi.fn().mockReturnValue({ onCancel: vi.fn() }),
        onCancel: vi.fn()
      })
    },
    Notify: {
      create: vi.fn()
    }
  }
})

import VulnerabilityService from '@/services/vulnerability'
import DataService from '@/services/data'
import Utils from '@/services/utils'
import DraftRecoveryService from '@/services/draft-recovery'
import { Dialog, Notify } from 'quasar'
import { useVulnQaStore } from '@/stores/vuln-qa'
import VulnerabilitiesPage from '@/pages/vulnerabilities/index.vue'

const mockLanguages = [
  { locale: 'en', language: 'English' },
  { locale: 'fr', language: 'French' }
]

const mockVulnTypes = [
  { name: 'Web', locale: 'en' },
  { name: 'Network', locale: 'en' },
  { name: 'Web', locale: 'fr' }
]

const mockCategories = [
  { name: 'Category1' },
  { name: 'Category2' }
]

const mockVulnerabilities = [
  {
    _id: 'vuln1',
    category: 'Category1',
    status: 0,
    creator: { username: 'admin' },
    cvssv3: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H',
    cvssv4: '',
    priority: '',
    remediationComplexity: '',
    updatedAt: '2024-01-15T00:00:00.000Z',
    details: [
      {
        locale: 'en',
        title: 'SQL Injection',
        vulnType: 'Web',
        description: '<p>desc</p>',
        observation: '',
        remediation: '<p>fix</p>',
        references: [],
        customFields: []
      }
    ]
  },
  {
    _id: 'vuln2',
    category: 'Category2',
    status: 1,
    cvssv3: '',
    cvssv4: '',
    priority: '',
    remediationComplexity: '',
    updatedAt: '2024-03-10T00:00:00.000Z',
    details: [
      {
        locale: 'en',
        title: 'XSS',
        vulnType: 'Web',
        description: '',
        observation: '',
        remediation: '',
        references: [],
        customFields: []
      }
    ]
  },
  {
    _id: 'vuln3',
    category: null,
    status: 2,
    cvssv3: '',
    cvssv4: '',
    priority: '',
    remediationComplexity: '',
    updatedAt: '2024-02-20T00:00:00.000Z',
    details: [
      {
        locale: 'en',
        title: 'Open Port',
        vulnType: 'Network',
        description: '',
        observation: '',
        remediation: '',
        references: [],
        customFields: []
      }
    ]
  }
]

const virtualScrollStub = {
  name: 'QVirtualScroll',
  props: {
    items: Array,
    virtualScrollItemSize: Number
  },
  template: '<div><slot v-for="(item, index) in items" :key="item._id" :item="item" :index="index" /></div>'
}

function setupDefaultMocks() {
  mockApi.get.mockResolvedValue({ data: { datas: { fields: [] } } })
  DataService.getLanguages.mockResolvedValue({ data: { datas: mockLanguages } })
  DataService.getVulnerabilityTypes.mockResolvedValue({ data: { datas: mockVulnTypes } })
  DataService.getVulnerabilityCategories.mockResolvedValue({ data: { datas: mockCategories } })
  DataService.getCustomFields.mockResolvedValue({ data: { datas: [] } })
  VulnerabilityService.getVulnerabilities.mockResolvedValue({ data: { datas: mockVulnerabilities } })
  VulnerabilityService.getVulnerability.mockImplementation((id) => {
    const found = mockVulnerabilities.find((vuln) => vuln._id === id)
    // Mirror the backend, which 404s on an unknown id rather than returning a null body.
    return found
      ? Promise.resolve({ data: { datas: found } })
      : Promise.reject({ response: { status: 404, data: { datas: 'Vulnerability not found' } } })
  })
  VulnerabilityService.getVulnUpdates.mockResolvedValue({ data: { datas: [] } })
  DraftRecoveryService.listDrafts.mockResolvedValue([])
  DraftRecoveryService.state.current = null
  DraftRecoveryService.state.revision = 0
}

describe('Vulnerabilities Page', () => {
  let router, pinia, i18n

  beforeEach(() => {
    // createWebHistory reads window.location, which persists across tests in jsdom; reset it
    // so a leftover /vulnerabilities/<id> URL doesn't deep-link into the next test's mount.
    window.history.replaceState({}, '', '/')

    pinia = createPinia()
    setActivePinia(pinia)

    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/vulnerabilities/:vulnerabilityId?', name: 'vulnerabilities', component: VulnerabilitiesPage },
        { path: '/audits', name: 'audits', component: { template: '<div>Audits</div>' } },
        { path: '/data/custom', component: { template: '<div>Data</div>' } }
      ]
    })

    i18n = createI18n({
      legacy: false,
      globalInjection: true,
      locale: 'en-US',
      fallbackLocale: 'en-US',
      messages: { 'en-US': {} }
    })

    vi.clearAllMocks()
    mockUserStore.isAllowed.mockImplementation(() => true)
    setupDefaultMocks()
  })

  const createWrapper = (options = {}) => {
    return mount(VulnerabilitiesPage, {
      global: {
        plugins: [pinia, router, i18n],
        stubs: {
          'q-select': true,
          'q-chip': true,
          'q-menu': true,
          'q-checkbox': true,
          'q-inner-loading': true,
          'q-toggle': true,
          'q-btn': true,
          'q-btn-dropdown': true,
          'q-dialog': true,
          'q-card': true,
          'q-card-section': true,
          'q-card-actions': true,
          'q-bar': true,
          'q-space': true,
          'q-input': true,
          'q-field': true,
          'q-separator': true,
          'q-expansion-item': true,
          'q-list': true,
          'q-item': true,
          'q-item-section': true,
          'q-item-label': true,
          'q-icon': true,
          'q-tooltip': true,
          'q-tr': true,
          'q-td': true,
          'q-radio': true,
          'q-pagination': true,
          'q-scroll-area': true,
          'q-virtual-scroll': virtualScrollStub,
          'q-tabs': true,
          'q-tab': true,
          'q-tab-panels': true,
          'q-tab-panel': true,
          'q-badge': true,
          'q-layout': true,
          'q-header': true,
          'q-page-container': true,
          'q-page': true,
          'basic-editor': true,
          'breadcrumb': true,
          'cvss3-calculator': true,
          'cvss4-calculator': true,
          'textarea-array': true,
          'custom-fields': true,
          ...(options.stubs || {})
        },
        mocks: {
          $t: (key) => key,
          $settings: {
            report: {
              public: {
                scoringMethods: { CVSS3: true, CVSS4: false }
              }
            }
          },
          $_: {
            cloneDeep: (obj) => JSON.parse(JSON.stringify(obj)),
            isEqual: (left, right) => JSON.stringify(left) === JSON.stringify(right)
          },
          $socket: {
            emit: () => {},
            on: () => {},
            off: () => {}
          },
          ...(options.mocks || {})
        }
      }
    })
  }

  const draftIndicatorStubs = () => ({
    'q-btn-dropdown': { template: '<div><slot /></div>' },
    'q-list': { template: '<div><slot /></div>' },
    'q-item': { template: '<div><slot /></div>' },
    'q-item-section': { template: '<div><slot /></div>' },
    'q-item-label': { template: '<div><slot /></div>' },
    'q-badge': { template: '<span v-bind="$attrs"><slot /></span>' },
    'q-tooltip': { template: '<span><slot /></span>' }
  })

  const flushPromises = async () => {
    await new Promise(resolve => setTimeout(resolve, 0))
    await new Promise(resolve => setTimeout(resolve, 0))
  }

  describe('Initialization', () => {
    it('should call data loading methods on mount', async () => {
      createWrapper()
      await flushPromises()

      expect(DataService.getLanguages).toHaveBeenCalled()
      expect(DataService.getVulnerabilityTypes).toHaveBeenCalled()
      expect(DataService.getVulnerabilityCategories).toHaveBeenCalled()
      expect(DataService.getCustomFields).toHaveBeenCalled()
      expect(VulnerabilityService.getVulnerabilities).toHaveBeenCalled()
    })

    it('should set languages from API response', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.vm.languages).toEqual(mockLanguages)
    })

    it('should set dtLanguage to first locale when languages load', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.vm.dtLanguage).toBe('en')
    })

    it('should set loading to false after vulnerabilities load', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.vm.loading).toBe(false)
    })

    it('should store vulnerabilities from API response', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.vm.vulnerabilities).toEqual(mockVulnerabilities)
    })

    it('should set vulnerability categories from API response', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.vm.vulnCategories).toEqual(mockCategories)
    })

    it('should set vulnerability types from API response', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.vm.vulnTypes).toEqual(mockVulnTypes)
    })

    it('should show no language message when languages array is empty', async () => {
      DataService.getLanguages.mockResolvedValue({ data: { datas: [] } })
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.vm.languages.length).toBe(0)
    })
  })

  describe('Computed Properties', () => {
    it('greys out the vulnerability QA button while its panel is open', async () => {
      const wrapper = createWrapper({
        stubs: {
          'q-bar': { template: '<div><slot /></div>' }
        }
      })
      await flushPromises()

      wrapper.vm.activePane = 'create'
      await wrapper.vm.$nextTick()

      const qaToggle = () => wrapper.get('[data-testid="vulnerability-qa-toggle"]')
      expect(qaToggle().classes()).not.toContain('bg-grey-3')

      wrapper.vm.vulnQaOpen = true
      await wrapper.vm.$nextTick()

      expect(qaToggle().classes()).toContain('bg-grey-3')
    })

    it('marks the editor read-only when the user lacks the edit permission (existing template)', async () => {
      // Editing an existing template requires vulnerabilities:update.
      mockUserStore.isAllowed.mockImplementation((scope) => scope !== 'vulnerabilities:update')
      const wrapper = createWrapper()
      await flushPromises()
      wrapper.vm.vulnerabilityId = 'vuln-1'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.canEditVuln).toBe(false)
      expect(wrapper.vm.vulnReadonly).toBe(true)

      mockUserStore.isAllowed.mockImplementation(() => true)
    })

    it('allows editing an existing template with vulnerabilities:update', async () => {
      mockUserStore.isAllowed.mockImplementation(() => true)
      const wrapper = createWrapper()
      await flushPromises()
      wrapper.vm.vulnerabilityId = 'vuln-1'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.canEditVuln).toBe(true)
      expect(wrapper.vm.vulnReadonly).toBe(false)
    })

    it('marks the editor read-only when creating without vulnerabilities:create', async () => {
      mockUserStore.isAllowed.mockImplementation((scope) => scope !== 'vulnerabilities:create')
      const wrapper = createWrapper()
      await flushPromises()
      // vulnerabilityId is null by default (create mode).
      expect(wrapper.vm.canEditVuln).toBe(false)
      expect(wrapper.vm.vulnReadonly).toBe(true)

      mockUserStore.isAllowed.mockImplementation(() => true)
    })

    it('updates the QA review toggle label for the panel state', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const qaToggle = () => wrapper.get('[data-testid="vulnerability-qa-all-toggle"]')
      expect(qaToggle().attributes('label')).toBe('vulnerabilityQa.showReview')

      useVulnQaStore().panelOpen = true
      await wrapper.vm.$nextTick()

      expect(qaToggle().attributes('label')).toBe('vulnerabilityQa.hideReview')
    })

    it('should filter vulnTypesLang by currentLanguage', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.currentLanguage = 'en'
      expect(wrapper.vm.vulnTypesLang).toEqual([
        { name: 'Web', locale: 'en' },
        { name: 'Network', locale: 'en' }
      ])

      wrapper.vm.currentLanguage = 'fr'
      expect(wrapper.vm.vulnTypesLang).toEqual([
        { name: 'Web', locale: 'fr' }
      ])
    })

    it('should compute computedVulnerabilities for the selected dtLanguage', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.dtLanguage = 'en'
      // All 3 mock vulnerabilities have english details with titles
      expect(wrapper.vm.computedVulnerabilities.length).toBe(3)
    })

    it('should return empty computedVulnerabilities for language with no details', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.dtLanguage = 'fr'
      expect(wrapper.vm.computedVulnerabilities.length).toBe(0)
    })

    it('should compute vulnCategoriesOptions with No Category prepended', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.vm.vulnCategoriesOptions).toEqual(['No Category', 'Category1', 'Category2'])
    })

    it('should compute vulnTypeOptions with Undefined prepended for current dtLanguage', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.dtLanguage = 'en'
      expect(wrapper.vm.vulnTypeOptions).toEqual(['Undefined', 'Web', 'Network'])
    })

    it('should resolve dtLanguageLabel to the matching language display name', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.dtLanguage = 'fr'
      expect(wrapper.vm.dtLanguageLabel).toBe('French')
    })

    it('should fall back to the raw locale code when dtLanguageLabel has no match', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.dtLanguage = 'de'
      expect(wrapper.vm.dtLanguageLabel).toBe('de')
    })

    it('should compute status counts for the selected language', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.dtLanguage = 'en'
      expect(wrapper.vm.statusCounts).toEqual({ all: 3, valid: 1, new: 1, updates: 1 })
    })

    it('should filter vulnerabilities by the single-select status filter', async () => {
      const wrapper = createWrapper()
      await flushPromises()
      wrapper.vm.dtLanguage = 'en'

      wrapper.vm.statusFilter = 'all'
      expect(wrapper.vm.filteredVulnerabilities.length).toBe(3)

      wrapper.vm.statusFilter = 'new'
      expect(wrapper.vm.filteredVulnerabilities.length).toBe(1)
      expect(wrapper.vm.filteredVulnerabilities[0]._id).toBe('vuln2')

      wrapper.vm.statusFilter = 'updates'
      expect(wrapper.vm.filteredVulnerabilities.length).toBe(1)
      expect(wrapper.vm.filteredVulnerabilities[0]._id).toBe('vuln3')
    })

    it('should paginate the sorted vulnerabilities', async () => {
      const wrapper = createWrapper()
      await flushPromises()
      wrapper.vm.dtLanguage = 'en'

      wrapper.vm.pagination.rowsPerPage = 2
      wrapper.vm.pagination.page = 1
      expect(wrapper.vm.paginatedVulnerabilities.length).toBe(2)
      expect(wrapper.vm.pagesNumber).toBe(2)

      wrapper.vm.pagination.page = 2
      expect(wrapper.vm.paginatedVulnerabilities.length).toBe(1)

      // rowsPerPage 0 shows everything
      wrapper.vm.pagination.rowsPerPage = 0
      expect(wrapper.vm.paginatedVulnerabilities.length).toBe(3)
      expect(wrapper.vm.pagesNumber).toBe(1)
    })

    it('uses virtual scrolling when results per page is All', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.dtLanguage = 'en'
      wrapper.vm.pagination.rowsPerPage = 0
      await wrapper.vm.$nextTick()

      const virtualList = wrapper.findComponent({ name: 'QVirtualScroll' })
      expect(virtualList.exists()).toBe(true)
      expect(virtualList.props('items')).toEqual(wrapper.vm.sortedVulnerabilities)
      expect(virtualList.props('virtualScrollItemSize')).toBe(64)
    })
  })

  describe('QA vulnerability navigation', () => {
    it('scrolls the virtual list to a vulnerability when all results are selected', async () => {
      const scrollTo = vi.fn()
      const wrapper = createWrapper({
        stubs: {
          'q-virtual-scroll': {
            name: 'QVirtualScroll',
            props: { items: Array },
            methods: { scrollTo },
            template: '<div><slot v-for="(item, index) in items" :key="item._id" :item="item" :index="index" /></div>'
          }
        }
      })
      await flushPromises()

      wrapper.vm.dtLanguage = 'en'
      wrapper.vm.pagination.rowsPerPage = 0
      await wrapper.vm.$nextTick()
      vi.spyOn(wrapper.vm, 'selectVulnerability').mockResolvedValue()

      const expectedIndex = wrapper.vm.sortedVulnerabilities.findIndex(({ _id }) => _id === 'vuln2')
      await wrapper.vm.navigateToVulnerabilityFromQa('vuln2')
      await wrapper.vm.$nextTick()

      expect(scrollTo).toHaveBeenCalledWith(expectedIndex, 'center-force')
    })
  })

  describe('Router-driven navigation', () => {
    it('shows only one separator before close for a read-only user', async () => {
      mockUserStore.isAllowed.mockImplementation((permission) => permission === 'vulnerabilities:read')
      await router.push({ name: 'vulnerabilities', params: { vulnerabilityId: 'vuln1' } })
      await router.isReady()

      const wrapper = createWrapper({
        stubs: {
          'q-bar': { template: '<div><slot /></div>' },
          'q-separator': { template: '<div data-testid="toolbar-separator" />' }
        }
      })
      await flushPromises()

      const header = wrapper.get('[data-testid="vulnerability-edit-pane"] > div')
      expect(header.findAll('[data-testid="toolbar-separator"]')).toHaveLength(1)
      expect(header.find('[data-testid="edit-vulnerability-close"]').exists()).toBe(true)
    })

    it('pushes the vuln id to the URL on select instead of opening directly', async () => {
      const wrapper = createWrapper()
      await flushPromises()
      await router.isReady()
      const pushSpy = vi.spyOn(router, 'push')

      await wrapper.vm.selectVulnerability(mockVulnerabilities[0])

      expect(pushSpy).toHaveBeenCalledWith({ name: 'vulnerabilities', params: { vulnerabilityId: 'vuln1' } })
    })

    it('fetches full detail and opens the edit pane when the route id changes', async () => {
      const wrapper = createWrapper()
      await flushPromises()
      await router.isReady()

      await router.push({ name: 'vulnerabilities', params: { vulnerabilityId: 'vuln1' } })
      await flushPromises()

      expect(VulnerabilityService.getVulnerability).toHaveBeenCalledWith('vuln1')
      expect(wrapper.vm.vulnerabilityId).toBe('vuln1')
      expect(wrapper.vm.activePane).toBe('edit')
    })

    it('opens the editable pane for a vulnerability with pending updates', async () => {
      VulnerabilityService.getVulnUpdates.mockResolvedValue({
        data: { datas: [{ _id: 'up1', locale: 'en', creator: { username: 'alice' }, customFields: [] }] }
      })
      const wrapper = createWrapper()
      await flushPromises()
      await router.isReady()

      await router.push({ name: 'vulnerabilities', params: { vulnerabilityId: 'vuln3' } })
      await flushPromises()

      expect(wrapper.vm.activePane).toBe('edit')
      expect(wrapper.vm.vulnUpdates.length).toBe(1)
    })

    it('does not switch the editor language when fetching update proposals', async () => {
      VulnerabilityService.getVulnUpdates.mockResolvedValue({
        data: { datas: [{ _id: 'up1', locale: 'fr', creator: { username: 'marie' }, customFields: [] }] }
      })
      const wrapper = createWrapper()
      await flushPromises()
      await router.isReady()

      await router.push({ name: 'vulnerabilities', params: { vulnerabilityId: 'vuln3' } })
      await flushPromises()

      expect(wrapper.vm.currentLanguage).toBe('en')
    })

    it('reaches the updates modal editors when saving with ctrl+s', async () => {
      VulnerabilityService.getVulnUpdates.mockResolvedValue({
        data: { datas: [{ _id: 'up1', locale: 'en', creator: { username: 'alice' }, customFields: [] }] }
      })
      VulnerabilityService.updateVulnerability.mockResolvedValue({})
      const wrapper = createWrapper()
      await flushPromises()
      await router.isReady()
      await router.push({ name: 'vulnerabilities', params: { vulnerabilityId: 'vuln3' } })
      await flushPromises()

      wrapper.vm.updatesModalOpen = true
      await wrapper.vm.$nextTick()

      // Utils.syncEditors walks $refs recursively, so the modal's editors are only flushed if
      // the page holds a ref to it.
      expect(wrapper.vm.$refs.updatesModal).toBeTruthy()

      wrapper.vm.updateVulnerability()
      await flushPromises()

      expect(Utils.syncEditors).toHaveBeenCalledWith(wrapper.vm.$refs)
      expect(VulnerabilityService.updateVulnerability).toHaveBeenCalled()
    })

    it('dismisses the proposals of one language and refreshes the list', async () => {
      VulnerabilityService.getVulnUpdates.mockResolvedValue({
        data: { datas: [{ _id: 'up1', locale: 'fr', creator: { username: 'marie' }, customFields: [] }] }
      })
      VulnerabilityService.dismissVulnUpdates.mockResolvedValue({})
      const wrapper = createWrapper()
      await flushPromises()
      await router.isReady()
      await router.push({ name: 'vulnerabilities', params: { vulnerabilityId: 'vuln3' } })
      await flushPromises()

      VulnerabilityService.getVulnUpdates.mockResolvedValue({ data: { datas: [] } })
      wrapper.vm.updatesModalOpen = true
      wrapper.vm.dismissUpdates('fr')
      await flushPromises()

      expect(VulnerabilityService.dismissVulnUpdates).toHaveBeenCalledWith('vuln3', 'fr')
      expect(wrapper.vm.vulnUpdates.length).toBe(0)
      expect(wrapper.vm.updatesModalOpen).toBe(false)
      expect(wrapper.vm.currentVulnerability.status).toBe(0)
    })

    it('closes the pane when the route id is cleared', async () => {
      const wrapper = createWrapper()
      await flushPromises()
      await router.isReady()

      await router.push({ name: 'vulnerabilities', params: { vulnerabilityId: 'vuln1' } })
      await flushPromises()
      expect(wrapper.vm.activePane).toBe('edit')

      await router.push({ name: 'vulnerabilities' })
      await flushPromises()
      expect(wrapper.vm.activePane).toBeNull()
      expect(wrapper.vm.vulnerabilityId).toBe('')
    })

    it('opens a deep-linked vulnerability on mount', async () => {
      await router.push({ name: 'vulnerabilities', params: { vulnerabilityId: 'vuln2' } })
      await router.isReady()
      const wrapper = createWrapper()
      await flushPromises()

      expect(VulnerabilityService.getVulnerability).toHaveBeenCalledWith('vuln2')
      expect(wrapper.vm.vulnerabilityId).toBe('vuln2')
    })

    it('resets the URL to the base list when opening the create pane', async () => {
      const wrapper = createWrapper()
      await flushPromises()
      await router.isReady()
      await router.push({ name: 'vulnerabilities', params: { vulnerabilityId: 'vuln1' } })
      await flushPromises()

      await wrapper.vm.openCreateVulnerability()
      await flushPromises()

      expect(wrapper.vm.activePane).toBe('create')
      expect(wrapper.vm.$route.params.vulnerabilityId).toBeUndefined()
    })
  })

  describe('QA refresh after save', () => {
    it('refreshes QA outdated state when the save changed content', async () => {
      VulnerabilityService.updateVulnerability.mockResolvedValue({})
      const wrapper = createWrapper()
      await flushPromises()

      const vulnQaStore = useVulnQaStore()
      vulnQaStore.panelOpen = true
      const loadStatusSpy = vi.spyOn(vulnQaStore, 'loadStatus').mockResolvedValue()

      wrapper.vm.vulnerabilityId = 'vuln1'
      wrapper.vm.currentVulnerability = { details: [{ locale: 'en', title: 'Edited', customFields: [] }] }
      wrapper.vm.currentVulnerabilityOrig = { details: [{ locale: 'en', title: 'Original', customFields: [] }] }

      const tokenBefore = wrapper.vm.qaReloadToken
      wrapper.vm.updateVulnerability()
      await flushPromises()

      expect(wrapper.vm.qaReloadToken).toBe(tokenBefore + 1)
      expect(loadStatusSpy).toHaveBeenCalled()
    })

    it('does not refresh QA when saving without changes (no spurious outdated)', async () => {
      VulnerabilityService.updateVulnerability.mockResolvedValue({})
      const wrapper = createWrapper()
      await flushPromises()

      const vulnQaStore = useVulnQaStore()
      vulnQaStore.panelOpen = true
      const loadStatusSpy = vi.spyOn(vulnQaStore, 'loadStatus').mockResolvedValue()

      wrapper.vm.vulnerabilityId = 'vuln1'
      const unchanged = { details: [{ locale: 'en', title: 'Same', customFields: [] }] }
      wrapper.vm.currentVulnerability = unchanged
      wrapper.vm.currentVulnerabilityOrig = wrapper.vm.$_.cloneDeep(unchanged)

      const tokenBefore = wrapper.vm.qaReloadToken
      wrapper.vm.updateVulnerability()
      await flushPromises()

      expect(wrapper.vm.qaReloadToken).toBe(tokenBefore)
      expect(loadStatusSpy).not.toHaveBeenCalled()
    })
  })

  describe('Sticky QA panel', () => {
    it('keeps the QA panel open across pane cleanup (navigation)', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.vulnQaOpen = true
      await wrapper.vm.cleanupCurrentVulnerability()

      expect(wrapper.vm.vulnQaOpen).toBe(true)
    })
  })

  describe('setSort', () => {
    it('should toggle direction when selecting the current sort field', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.vm.pagination.sortBy).toBe('title')
      expect(wrapper.vm.sortDesc).toBe(false)

      wrapper.vm.setSort('title')
      expect(wrapper.vm.sortDesc).toBe(true)

      wrapper.vm.setSort('category')
      expect(wrapper.vm.pagination.sortBy).toBe('category')
      expect(wrapper.vm.sortDesc).toBe(false)
    })
  })

  describe('Draft Recovery Hints', () => {
    it('should render the draft recovery status in create, edit, and update pane headers', async () => {
      const wrapper = createWrapper({
        stubs: {
          'q-bar': { template: '<div><slot /></div>' },
          'draft-recovery-status': { template: '<div data-testid="draft-recovery-status-stub" />' }
        }
      })
      await flushPromises()

      for (const pane of ['create', 'edit']) {
        wrapper.vm.activePane = pane
        await wrapper.vm.$nextTick()
        expect(wrapper.find('[data-testid="draft-recovery-status-stub"]').exists()).toBe(true)
      }
    })

    it('should request vulnerability drafts on mount', async () => {
      createWrapper()
      await flushPromises()

      expect(DraftRecoveryService.listDrafts).toHaveBeenCalledWith({
        userId: '1',
        scopes: ['vuln-modal-edit', 'vuln-modal-create']
      })
    })

    it('should show a row draft badge for vulnerabilities with edit drafts', async () => {
      DraftRecoveryService.listDrafts.mockResolvedValue([
        { scope: 'vuln-modal-edit', refKey: 'vuln1', status: 'active_draft' }
      ])
      const wrapper = createWrapper({ stubs: draftIndicatorStubs() })
      await flushPromises()

      expect(wrapper.find('[data-testid="vulnerability-draft-badge-vuln1"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="vulnerability-draft-badge-vuln2"]').exists()).toBe(false)
    })

    it('should not show the row draft badge for the currently open vulnerability', async () => {
      DraftRecoveryService.listDrafts.mockResolvedValue([
        { scope: 'vuln-modal-edit', refKey: 'vuln1', status: 'active_draft' }
      ])
      const wrapper = createWrapper({ stubs: draftIndicatorStubs() })
      await flushPromises()

      wrapper.vm.vulnerabilityId = 'vuln1'
      await wrapper.vm.$nextTick()

      expect(wrapper.find('[data-testid="vulnerability-draft-badge-vuln1"]').exists()).toBe(false)
    })

    it('should show create category draft badges for no category and matching categories', async () => {
      DraftRecoveryService.listDrafts.mockResolvedValue([
        { scope: 'vuln-modal-create', refKey: '_new:none', status: 'active_draft' },
        { scope: 'vuln-modal-create', refKey: '_new:Category2', status: 'discarded_draft' }
      ])
      const wrapper = createWrapper({ stubs: draftIndicatorStubs() })
      await flushPromises()

      expect(wrapper.find('[data-testid="create-vulnerability-draft-badge-none"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="create-vulnerability-draft-badge-Category2"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="create-vulnerability-draft-badge-Category1"]').exists()).toBe(false)
    })

    it('should refresh vulnerability draft indicators when draft recovery revision changes', async () => {
      DraftRecoveryService.listDrafts.mockResolvedValue([])
      const wrapper = createWrapper({ stubs: draftIndicatorStubs() })
      await flushPromises()

      expect(wrapper.find('[data-testid="vulnerability-draft-badge-vuln1"]').exists()).toBe(false)

      DraftRecoveryService.listDrafts.mockResolvedValue([
        { scope: 'vuln-modal-edit', refKey: 'vuln1', status: 'active_draft' }
      ])
      DraftRecoveryService.state.revision += 1
      await wrapper.vm.$nextTick()
      await flushPromises()

      expect(wrapper.find('[data-testid="vulnerability-draft-badge-vuln1"]').exists()).toBe(true)
    })
  })

  describe('getDtTitle', () => {
    it('should return title for matching locale', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.dtLanguage = 'en'
      const title = wrapper.vm.getDtTitle(mockVulnerabilities[0])
      expect(title).toBe('SQL Injection')
    })

    it('should return error key when locale not found', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.dtLanguage = 'de'
      const title = wrapper.vm.getDtTitle(mockVulnerabilities[0])
      expect(title).toBe('err.notDefinedLanguage')
    })
  })

  describe('getDtType', () => {
    it('should return vulnType for matching locale', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.dtLanguage = 'en'
      const type = wrapper.vm.getDtType(mockVulnerabilities[0])
      expect(type).toBe('Web')
    })

    it('should return Undefined when locale not found', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.dtLanguage = 'de'
      const type = wrapper.vm.getDtType(mockVulnerabilities[0])
      expect(type).toBe('Undefined')
    })
  })

  describe('cleanCurrentVulnerability', () => {
    it('should reset current vulnerability fields', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.currentVulnerability.cvssv3 = 'CVSS:3.1/AV:N'
      wrapper.vm.currentVulnerability.cvssv4 = 'CVSS:4.0/AV:N'
      wrapper.vm.currentVulnerability.priority = 3
      wrapper.vm.currentVulnerability.remediationComplexity = 2

      wrapper.vm.cleanCurrentVulnerability()

      expect(wrapper.vm.currentVulnerability.cvssv3).toBe('')
      expect(wrapper.vm.currentVulnerability.cvssv4).toBe('')
      expect(wrapper.vm.currentVulnerability.priority).toBe('')
      expect(wrapper.vm.currentVulnerability.remediationComplexity).toBe('')
      expect(wrapper.vm.currentVulnerability.details.length).toBeGreaterThan(0)
    })

    it('should set category from currentCategory if present', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.currentCategory = { name: 'TestCategory' }
      wrapper.vm.cleanCurrentVulnerability()

      expect(wrapper.vm.currentVulnerability.category).toBe('TestCategory')
    })

    it('should set category to null when no currentCategory', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.currentCategory = null
      wrapper.vm.cleanCurrentVulnerability()

      expect(wrapper.vm.currentVulnerability.category).toBeNull()
    })

    it('should clear errors', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.errors.title = 'some error'
      wrapper.vm.cleanCurrentVulnerability()

      expect(wrapper.vm.errors.title).toBe('')
    })
  })

  describe('setCurrentDetails', () => {
    it('should create new detail entry when locale does not exist', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.currentVulnerability.details = []
      wrapper.vm.currentLanguage = 'en'
      wrapper.vm.setCurrentDetails()

      expect(wrapper.vm.currentVulnerability.details.length).toBe(1)
      expect(wrapper.vm.currentVulnerability.details[0].locale).toBe('en')
      expect(wrapper.vm.currentVulnerability.details[0].title).toBe('')
      expect(wrapper.vm.currentDetailsIndex).toBe(0)
    })

    it('should set currentDetailsIndex to existing detail when locale exists', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.currentVulnerability.details = [
        { locale: 'en', title: 'Test', customFields: [] },
        { locale: 'fr', title: 'TestFR', customFields: [] }
      ]
      wrapper.vm.currentLanguage = 'fr'
      wrapper.vm.setCurrentDetails()

      expect(wrapper.vm.currentDetailsIndex).toBe(1)
    })

    it('should call filterCustomFields from Utils', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.currentVulnerability.details = []
      wrapper.vm.currentLanguage = 'en'
      wrapper.vm.setCurrentDetails()

      expect(Utils.filterCustomFields).toHaveBeenCalled()
    })
  })

  describe('createVulnerability', () => {
    it('should set title error when no detail has a title', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.currentVulnerability.details = [
        { locale: 'en', title: '', customFields: [] }
      ]
      wrapper.vm.createVulnerability()

      expect(wrapper.vm.errors.title).toBe('err.titleRequired')
      expect(VulnerabilityService.createVulnerabilities).not.toHaveBeenCalled()
    })

    it('should call createVulnerabilities service when title is present', async () => {
      VulnerabilityService.createVulnerabilities.mockResolvedValue({})
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.currentVulnerability.details = [
        { locale: 'en', title: 'New Vuln', customFields: [] }
      ]

      wrapper.vm.createVulnerability()
      await flushPromises()

      expect(VulnerabilityService.createVulnerabilities).toHaveBeenCalledWith([wrapper.vm.currentVulnerability])
    })

    it('should show the inline saved state without a success notification on create', async () => {
      VulnerabilityService.createVulnerabilities.mockResolvedValue({})
      VulnerabilityService.getVulnerabilities.mockResolvedValue({
        data: {
          datas: [
            ...mockVulnerabilities,
            {
              _id: 'new-vuln',
              category: null,
              status: 1,
              details: [{ locale: 'en', title: 'New Vuln', customFields: [] }]
            }
          ]
        }
      })
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.currentVulnerability.details = [
        { locale: 'en', title: 'New Vuln', customFields: [] }
      ]
      wrapper.vm.activePane = 'create'
      await wrapper.vm.$nextTick()
      wrapper.vm.createVulnerability()
      await flushPromises()

      expect(wrapper.vm.saveButtonState).toBe('saved')
      expect(Notify.create).not.toHaveBeenCalled()
    })

    it('keeps the typed rich content and adopts the new id after create', async () => {
      VulnerabilityService.createVulnerabilities.mockResolvedValue({})
      VulnerabilityService.getVulnerabilities.mockResolvedValue({
        data: {
          datas: [
            ...mockVulnerabilities,
            { _id: 'new-vuln', category: null, status: 0, details: [{ locale: 'en', title: 'Fresh', vulnType: 'Web' }] }
          ]
        }
      })
      const wrapper = createWrapper()
      await flushPromises()
      await router.isReady()

      wrapper.vm.activePane = 'create'
      wrapper.vm.currentVulnerability.details = [
        { locale: 'en', title: 'Fresh', description: '<p>typed body</p>', customFields: [] }
      ]
      wrapper.vm.createVulnerability()
      await flushPromises()

      expect(wrapper.vm.vulnerabilityId).toBe('new-vuln')
      // The lightweight list row lacks the body, so the typed content must be preserved.
      expect(wrapper.vm.currentVulnerability.details[0].description).toBe('<p>typed body</p>')
      // The created id is stamped onto the kept object so delete-by-currentVulnerability works.
      expect(wrapper.vm.currentVulnerability._id).toBe('new-vuln')
      expect(wrapper.vm.activePane).toBe('edit')
    })

    it('should show error notification on create failure', async () => {
      VulnerabilityService.createVulnerabilities.mockRejectedValue({
        response: { data: { datas: 'Creation failed' } }
      })
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.currentVulnerability.details = [
        { locale: 'en', title: 'New Vuln', customFields: [] }
      ]
      wrapper.vm.createVulnerability()
      await flushPromises()

      expect(Notify.create).toHaveBeenCalledWith(expect.objectContaining({
        message: 'Creation failed',
        color: 'negative'
      }))
    })
  })

  describe('updateVulnerability', () => {
    it('should set title error when no detail has a title', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.currentVulnerability.details = [
        { locale: 'en', title: '', customFields: [] }
      ]
      wrapper.vm.updateVulnerability()

      expect(wrapper.vm.errors.title).toBe('err.titleRequired')
      expect(VulnerabilityService.updateVulnerability).not.toHaveBeenCalled()
    })

    it('should call updateVulnerability service with correct params', async () => {
      VulnerabilityService.updateVulnerability.mockResolvedValue({})
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.vulnerabilityId = 'vuln1'
      wrapper.vm.currentVulnerability.details = [
        { locale: 'en', title: 'Updated Vuln', customFields: [] }
      ]
      wrapper.vm.updateVulnerability()
      await flushPromises()

      expect(VulnerabilityService.updateVulnerability).toHaveBeenCalledWith(
        'vuln1',
        wrapper.vm.currentVulnerability
      )
    })

    it('should show the inline saved state without a success notification on update', async () => {
      VulnerabilityService.updateVulnerability.mockResolvedValue({})
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.vulnerabilityId = 'vuln1'
      wrapper.vm.currentVulnerability.details = [
        { locale: 'en', title: 'Updated Vuln', customFields: [] }
      ]
      wrapper.vm.activePane = 'edit'
      await wrapper.vm.$nextTick()
      wrapper.vm.updateVulnerability()
      await flushPromises()

      expect(wrapper.vm.saveButtonState).toBe('saved')
      expect(Notify.create).not.toHaveBeenCalled()
    })

    it('should show error notification on update failure', async () => {
      VulnerabilityService.updateVulnerability.mockRejectedValue({
        response: { data: { datas: 'Update failed' } }
      })
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.vulnerabilityId = 'vuln1'
      wrapper.vm.currentVulnerability.details = [
        { locale: 'en', title: 'Updated Vuln', customFields: [] }
      ]
      wrapper.vm.updateVulnerability()
      await flushPromises()

      expect(Notify.create).toHaveBeenCalledWith(expect.objectContaining({
        message: 'Update failed',
        color: 'negative'
      }))
    })
  })

  describe('deleteVulnerability', () => {
    it('should call deleteVulnerability service and refresh list on success', async () => {
      VulnerabilityService.deleteVulnerability.mockResolvedValue({})
      const wrapper = createWrapper()
      await flushPromises()

      vi.clearAllMocks()
      setupDefaultMocks()
      VulnerabilityService.deleteVulnerability.mockResolvedValue({})

      wrapper.vm.deleteVulnerability('vuln1')
      await flushPromises()

      expect(VulnerabilityService.deleteVulnerability).toHaveBeenCalledWith('vuln1')
      expect(VulnerabilityService.getVulnerabilities).toHaveBeenCalled()
      expect(Notify.create).toHaveBeenCalledWith(expect.objectContaining({
        message: 'msg.vulnerabilityDeletedOk',
        color: 'positive'
      }))
    })

    it('should show error notification on delete failure', async () => {
      VulnerabilityService.deleteVulnerability.mockRejectedValue({
        response: { data: { datas: 'Delete failed' } }
      })
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.deleteVulnerability('vuln1')
      await flushPromises()

      expect(Notify.create).toHaveBeenCalledWith(expect.objectContaining({
        message: 'Delete failed',
        color: 'negative'
      }))
    })
  })

  describe('confirmDeleteVulnerability', () => {
    it('should open a confirmation dialog', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.confirmDeleteVulnerability({ _id: 'vuln1' })

      expect(Dialog.create).toHaveBeenCalledWith(expect.objectContaining({
        title: 'msg.confirmSuppression',
        message: 'msg.vulnerabilityWillBeDeleted'
      }))
    })

    it('falls back to the open vulnerabilityId when the row has no _id (create flow)', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const deleteSpy = vi.spyOn(wrapper.vm, 'deleteVulnerability').mockImplementation(() => {})
      // Invoke the confirm callback so the delete target id is exercised.
      Dialog.create.mockReturnValueOnce({ onOk: (cb) => { cb(); return { onCancel: vi.fn() } } })

      wrapper.vm.vulnerabilityId = 'open-id'
      // currentVulnerability from the create flow has no _id.
      wrapper.vm.confirmDeleteVulnerability(wrapper.vm.currentVulnerability)

      expect(deleteSpy).toHaveBeenCalledWith('open-id')
    })
  })

  describe('clone', () => {
    it('remounts the full edit pane when navigating to another vulnerability', async () => {
      let cvssMounts = 0
      const wrapper = createWrapper({
        stubs: {
          'q-card-section': { template: '<div><slot /></div>' },
          'cvss3-calculator': {
            props: ['modelValue'],
            mounted() { cvssMounts += 1 },
            template: '<div />'
          }
        }
      })
      await flushPromises()

      wrapper.vm.vulnerabilityId = 'vuln1'
      wrapper.vm.activePane = 'edit'
      await wrapper.vm.$nextTick()
      expect(cvssMounts).toBe(1)

      wrapper.vm.vulnerabilityId = 'vuln2'
      await wrapper.vm.$nextTick()
      expect(cvssMounts).toBe(2)
    })

    it('should deep clone the row into currentVulnerability', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const row = {
        _id: 'vuln1',
        category: 'Category1',
        cvssv3: '',
        cvssv4: '',
        priority: '',
        remediationComplexity: '',
        details: [
          { locale: 'en', title: 'SQL Injection', customFields: [] }
        ],
        status: 0
      }

      wrapper.vm.clone(row)

      expect(wrapper.vm.vulnerabilityId).toBe('vuln1')
      expect(wrapper.vm.currentVulnerability.category).toBe('Category1')
    })

    it('should snapshot the normalized vulnerability as the original version', async () => {
      Utils.filterCustomFields.mockReturnValueOnce([
        {
          customField: { _id: 'field1', label: 'Impact' },
          text: 'Low'
        }
      ])
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.currentLanguage = 'en'
      wrapper.vm.clone({
        _id: 'vuln1',
        category: 'Category1',
        cvssv3: '',
        cvssv4: '',
        priority: '',
        remediationComplexity: '',
        details: [
          {
            locale: 'en',
            title: 'SQL Injection',
            customFields: [
              { customField: 'field1', text: 'Low' }
            ]
          }
        ],
        status: 0
      })

      expect(wrapper.vm.currentVulnerabilityOrig).toEqual(wrapper.vm.currentVulnerability)
    })
  })

  describe('customSort', () => {
    it('should sort by title ascending', async () => {
      const wrapper = createWrapper()
      await flushPromises()
      wrapper.vm.dtLanguage = 'en'

      const rows = [...mockVulnerabilities]
      const sorted = wrapper.vm.customSort(rows, 'title', false)

      expect(wrapper.vm.getDtTitle(sorted[0])).toBe('Open Port')
      expect(wrapper.vm.getDtTitle(sorted[1])).toBe('SQL Injection')
      expect(wrapper.vm.getDtTitle(sorted[2])).toBe('XSS')
    })

    it('should sort by title descending', async () => {
      const wrapper = createWrapper()
      await flushPromises()
      wrapper.vm.dtLanguage = 'en'

      const rows = [...mockVulnerabilities]
      const sorted = wrapper.vm.customSort(rows, 'title', true)

      expect(wrapper.vm.getDtTitle(sorted[0])).toBe('XSS')
      expect(wrapper.vm.getDtTitle(sorted[2])).toBe('Open Port')
    })

    it('should sort by category', async () => {
      const wrapper = createWrapper()
      await flushPromises()
      wrapper.vm.dtLanguage = 'en'

      const rows = [...mockVulnerabilities]
      const sorted = wrapper.vm.customSort(rows, 'category', false)

      expect(sorted[0].category).toBe('Category1')
      expect(sorted[1].category).toBe('Category2')
    })

    it('should sort by last modified', async () => {
      const wrapper = createWrapper()
      await flushPromises()
      wrapper.vm.dtLanguage = 'en'

      const rows = [...mockVulnerabilities]
      const sorted = wrapper.vm.customSort(rows, 'lastModified', false)

      expect(sorted[0]._id).toBe('vuln1')
      expect(sorted[1]._id).toBe('vuln3')
      expect(sorted[2]._id).toBe('vuln2')
    })

    it('should sort by last modified descending', async () => {
      const wrapper = createWrapper()
      await flushPromises()
      wrapper.vm.dtLanguage = 'en'

      const rows = [...mockVulnerabilities]
      const sorted = wrapper.vm.customSort(rows, 'lastModified', true)

      expect(sorted[0]._id).toBe('vuln2')
      expect(sorted[1]._id).toBe('vuln3')
      expect(sorted[2]._id).toBe('vuln1')
    })

    it('should return undefined for null rows', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const result = wrapper.vm.customSort(null, 'title', false)
      expect(result).toBeUndefined()
    })
  })

  describe('customFilter', () => {
    it('should filter by title search term', async () => {
      const wrapper = createWrapper()
      await flushPromises()
      wrapper.vm.dtLanguage = 'en'

      const terms = { title: 'SQL', status: 'all' }
      const result = wrapper.vm.customFilter(mockVulnerabilities, terms)

      expect(result.length).toBe(1)
      expect(result[0]._id).toBe('vuln1')
    })

    it('should filter by status', async () => {
      const wrapper = createWrapper()
      await flushPromises()
      wrapper.vm.dtLanguage = 'en'

      // Only show valid (status 0), exclude new and updates
      const terms = { title: '', status: 'valid' }
      const result = wrapper.vm.customFilter(mockVulnerabilities, terms)

      expect(result.length).toBe(1)
      expect(result[0]._id).toBe('vuln1')
    })

    it('should filter by selected categories (multi-select, No Category included)', async () => {
      const wrapper = createWrapper()
      await flushPromises()
      wrapper.vm.dtLanguage = 'en'

      let result = wrapper.vm.customFilter(mockVulnerabilities, { title: '', categories: ['Category1'] })
      expect(result.map(row => row._id)).toEqual(['vuln1'])

      result = wrapper.vm.customFilter(mockVulnerabilities, { title: '', categories: ['Category1', 'No Category'] })
      expect(result.map(row => row._id)).toEqual(['vuln1', 'vuln3'])
    })

    it('should filter by selected types (multi-select)', async () => {
      const wrapper = createWrapper()
      await flushPromises()
      wrapper.vm.dtLanguage = 'en'

      const result = wrapper.vm.customFilter(mockVulnerabilities, { title: '', types: ['Network'] })
      expect(result.map(row => row._id)).toEqual(['vuln3'])
    })

    it('should filter by CVSS range bucket', async () => {
      const wrapper = createWrapper()
      await flushPromises()
      wrapper.vm.dtLanguage = 'en'

      // vuln1 has a 9.8 CVSSv3 vector -> critical; the others have no CVSS
      const critical = wrapper.vm.customFilter(mockVulnerabilities, { title: '', cvssRange: 'critical' })
      expect(critical.map(row => row._id)).toEqual(['vuln1'])

      const low = wrapper.vm.customFilter(mockVulnerabilities, { title: '', cvssRange: 'low' })
      expect(low.length).toBe(0)
    })

    it('should filter by creator username', async () => {
      const wrapper = createWrapper()
      await flushPromises()
      wrapper.vm.dtLanguage = 'en'

      const result = wrapper.vm.customFilter(mockVulnerabilities, { title: '', creator: 'admin' })
      expect(result.map(row => row._id)).toEqual(['vuln1'])
    })

    it('should count active filter groups and reset them', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.vm.activeFilterCount).toBe(0)

      wrapper.vm.search.categories = ['Category1']
      wrapper.vm.search.types = ['Web']
      wrapper.vm.search.cvssRange = 'high'
      wrapper.vm.search.creator = 'admin'
      expect(wrapper.vm.activeFilterCount).toBe(4)

      wrapper.vm.search.unsavedOnly = true
      expect(wrapper.vm.activeFilterCount).toBe(5)

      wrapper.vm.resetAdvancedFilters()
      expect(wrapper.vm.activeFilterCount).toBe(0)
      expect(wrapper.vm.search).toEqual({
        title: '', categories: [], types: [], cvssRange: 'all', creator: null, unsavedOnly: false
      })
    })

    it('should count vulnerabilities with unsaved changes in the selected language', async () => {
      const wrapper = createWrapper()
      await flushPromises()
      wrapper.vm.dtLanguage = 'en'
      wrapper.vm.vulnerabilityDrafts = [
        { scope: 'vuln-modal-edit', refKey: 'vuln1', status: 'active_draft' },
        { scope: 'vuln-modal-edit', refKey: 'vuln2', status: 'active_draft' },
        { scope: 'vuln-modal-create', refKey: '_new:none', status: 'active_draft' }
      ]

      expect(wrapper.vm.unsavedChangesCount).toBe(2)

      wrapper.vm.vulnerabilityId = 'vuln1'
      expect(wrapper.vm.unsavedChangesCount).toBe(1)
    })

    it('should filter by unsaved changes only', async () => {
      const wrapper = createWrapper()
      await flushPromises()
      wrapper.vm.dtLanguage = 'en'
      wrapper.vm.vulnerabilityDrafts = [
        { scope: 'vuln-modal-edit', refKey: 'vuln1', status: 'active_draft' }
      ]

      const result = wrapper.vm.customFilter(mockVulnerabilities, { title: '', unsavedOnly: true })
      expect(result.map(row => row._id)).toEqual(['vuln1'])
    })

    it('should expose the filtered count through filteredRowsCount', async () => {
      const wrapper = createWrapper()
      await flushPromises()
      wrapper.vm.dtLanguage = 'en'

      expect(wrapper.vm.filteredRowsCount).toBe(3)

      wrapper.vm.search.title = 'SQL'
      expect(wrapper.vm.filteredRowsCount).toBe(1)
    })

    it('should filter case-insensitively', async () => {
      const wrapper = createWrapper()
      await flushPromises()
      wrapper.vm.dtLanguage = 'en'

      const terms = { title: 'sql injection', status: 'all' }
      const result = wrapper.vm.customFilter(mockVulnerabilities, terms)

      expect(result.length).toBe(1)
    })
  })

  describe('goToAudits', () => {
    it('should navigate to audits page with findingTitle query', async () => {
      const wrapper = createWrapper()
      await flushPromises()
      await router.isReady()
      wrapper.vm.dtLanguage = 'en'

      const pushSpy = vi.spyOn(router, 'push')
      wrapper.vm.goToAudits(mockVulnerabilities[0])

      expect(pushSpy).toHaveBeenCalledWith({
        name: 'audits',
        query: { findingTitle: 'SQL Injection' }
      })
    })
  })

  describe('getVulnTitleLocale', () => {
    it('should return title for matching locale', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const title = wrapper.vm.getVulnTitleLocale(mockVulnerabilities[0], 'en')
      expect(title).toBe('SQL Injection')
    })

    it('should return "undefined" when locale not found', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const title = wrapper.vm.getVulnTitleLocale(mockVulnerabilities[0], 'de')
      expect(title).toBe('undefined')
    })
  })

  describe('mergeVulnerabilities', () => {
    it('should call mergeVulnerability service with correct params', async () => {
      VulnerabilityService.mergeVulnerability.mockResolvedValue({})
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.mergeVulnLeft = 'vuln1'
      wrapper.vm.mergeVulnRight = 'vuln2'
      wrapper.vm.mergeLanguageRight = 'fr'

      wrapper.vm.mergeVulnerabilities()
      await flushPromises()

      expect(VulnerabilityService.mergeVulnerability).toHaveBeenCalledWith('vuln1', 'vuln2', 'fr')
    })

    it('should show success notification on merge success', async () => {
      VulnerabilityService.mergeVulnerability.mockResolvedValue({})
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.mergeVulnLeft = 'vuln1'
      wrapper.vm.mergeVulnRight = 'vuln2'
      wrapper.vm.mergeLanguageRight = 'fr'

      wrapper.vm.mergeVulnerabilities()
      await flushPromises()

      expect(Notify.create).toHaveBeenCalledWith(expect.objectContaining({
        message: 'msg.vulnerabilityMergeOk',
        color: 'positive'
      }))
    })

    it('should show error notification on merge failure', async () => {
      VulnerabilityService.mergeVulnerability.mockRejectedValue({
        response: { data: { datas: 'Merge failed' } }
      })
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.mergeVulnLeft = 'vuln1'
      wrapper.vm.mergeVulnRight = 'vuln2'
      wrapper.vm.mergeLanguageRight = 'fr'

      wrapper.vm.mergeVulnerabilities()
      await flushPromises()

      expect(Notify.create).toHaveBeenCalledWith(expect.objectContaining({
        message: 'Merge failed',
        color: 'negative'
      }))
    })
  })

  describe('cleanErrors', () => {
    it('should clear title error', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.errors.title = 'some error'
      wrapper.vm.cleanErrors()

      expect(wrapper.vm.errors.title).toBe('')
    })
  })

  describe('Error handling on data load', () => {
    it('should handle languages load failure gracefully', async () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {})
      DataService.getLanguages.mockRejectedValue(new Error('Network error'))

      const wrapper = createWrapper()
      await flushPromises()

      expect(consoleSpy).toHaveBeenCalled()
      consoleSpy.mockRestore()
    })

    it('should handle vulnerabilities load failure and show notification', async () => {
      VulnerabilityService.getVulnerabilities.mockRejectedValue({
        response: { data: { datas: 'Failed to load' } }
      })

      const wrapper = createWrapper()
      await flushPromises()

      expect(Notify.create).toHaveBeenCalledWith(expect.objectContaining({
        message: 'Failed to load',
        color: 'negative'
      }))
    })
  })

  describe('Data properties', () => {
    it('should have correct initial state', async () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.loading).toBe(true)
      expect(wrapper.vm.vulnerabilities).toEqual([])
      expect(wrapper.vm.search).toEqual({
        title: '', categories: [], types: [], cvssRange: 'all', creator: null, unsavedOnly: false
      })
      expect(wrapper.vm.statusFilter).toBe('all')
      expect(wrapper.vm.errors).toEqual({ title: '' })
      expect(wrapper.vm.pagination.rowsPerPage).toBe(25)
      expect(wrapper.vm.pagination.sortBy).toBe('title')
      expect(wrapper.vm.sortDesc).toBe(false)
      expect(wrapper.vm.activePane).toBeNull()
    })

    it('should have correct rowsPerPageOptions', async () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.rowsPerPageOptions).toEqual([
        { label: '25', value: 25 },
        { label: '50', value: 50 },
        { label: '100', value: 100 },
        { label: 'All', value: 0 }
      ])
    })
  })

  describe('Merge computed filters', () => {
    it('should show each merge search only after its language is selected', async () => {
      const wrapper = createWrapper({
        stubs: {
          'q-card-section': { template: '<div><slot /></div>' },
          'q-input': { template: '<input v-bind="$attrs" />' }
        }
      })
      await flushPromises()
      wrapper.vm.activePane = 'merge'
      await wrapper.vm.$nextTick()

      expect(wrapper.find('[data-testid="merge-search-left"]').exists()).toBe(false)
      expect(wrapper.find('[data-testid="merge-search-right"]').exists()).toBe(false)

      wrapper.vm.mergeLanguageLeft = 'en'
      await wrapper.vm.$nextTick()
      expect(wrapper.find('[data-testid="merge-search-left"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="merge-search-right"]').exists()).toBe(false)

      wrapper.vm.mergeLanguageRight = 'fr'
      await wrapper.vm.$nextTick()
      expect(wrapper.find('[data-testid="merge-search-right"]').exists()).toBe(true)
    })

    it('should independently search merge candidates by their localized titles', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.vulnerabilities = [
        { _id: 'en-alpha', details: [{ locale: 'en', title: 'Alpha finding' }] },
        { _id: 'en-beta', details: [{ locale: 'en', title: 'Beta finding' }] },
        { _id: 'fr-gamma', details: [{ locale: 'fr', title: 'Constat Gamma' }] },
        { _id: 'fr-delta', details: [{ locale: 'fr', title: 'Constat Delta' }] }
      ]
      wrapper.vm.mergeLanguageLeft = 'en'
      wrapper.vm.mergeLanguageRight = 'fr'
      wrapper.vm.mergeSearchLeft = 'BETA'
      wrapper.vm.mergeSearchRight = 'delta'

      expect(wrapper.vm.filteredVulnerabilitiesMergeLeft.map(vuln => vuln._id)).toEqual(['en-beta'])
      expect(wrapper.vm.filteredVulnerabilitiesMergeRight.map(vuln => vuln._id)).toEqual(['fr-delta'])
    })

    it('should filter vulnerabilities for merge left panel', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.mergeLanguageLeft = 'en'
      wrapper.vm.mergeLanguageRight = 'fr'

      // All vulns have 'en' details but none have 'fr', so they show in left
      const leftFiltered = wrapper.vm.filteredVulnerabilitiesMergeLeft
      expect(leftFiltered.length).toBe(3)
    })

    it('should filter vulnerabilities for merge right panel', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      wrapper.vm.mergeLanguageLeft = 'en'
      wrapper.vm.mergeLanguageRight = 'fr'

      // No vulns have 'fr' details but not 'en', so right is empty
      const rightFiltered = wrapper.vm.filteredVulnerabilitiesMergeRight
      expect(rightFiltered.length).toBe(0)
    })
  })
})
