import { describe, it, expect, vi } from 'vitest'
import { createTestWrapper } from '../../test-utils'
import { useAuditQaStore } from '@/stores/audit-qa'

vi.mock('@/boot/i18n', () => ({
  $t: (key) => key
}))

// audit-qa.js pulls in AiService, which pulls in boot/axios, which calls useUserStore() at
// module scope — mocking it here avoids that import chain running before any pinia is active.
vi.mock('@/services/ai', () => ({
  default: {
    runAuditQa: vi.fn()
  }
}))

import AuditQaSidebar from '@/components/audit-qa-sidebar.vue'

function createWrapper(props = {}) {
  const wrapper = createTestWrapper(AuditQaSidebar, {
    props: {
      auditId: 'audit-1',
      height: 'calc(100vh - 104px)',
      ...props
    },
    global: {
      stubs: {
        'qa-results-panel': true,
        'q-scroll-area': { template: '<div><slot /></div>' }
      }
    }
  })

  // The store instance created inside createTestWrapper's fresh pinia is only reachable
  // through the mounted component from here on — resolve it the same way the component does.
  useAuditQaStore().auditId = 'audit-1'

  return wrapper
}

describe('AuditQaSidebar navigation', () => {
  it('pushes the resolved route for a finding location', () => {
    const wrapper = createWrapper({
      findings: [{ _id: '507f1f77bcf86cd799439011', title: 'XSS' }]
    })
    wrapper.vm.$router.push = vi.fn().mockResolvedValue()

    wrapper.vm.navigateTo('finding:507f1f77bcf86cd799439011::XSS')

    expect(wrapper.vm.$router.push).toHaveBeenCalledWith('/audits/audit-1/findings/507f1f77bcf86cd799439011')
  })

  it('pushes the general page for a general location', () => {
    const wrapper = createWrapper()
    wrapper.vm.$router.push = vi.fn().mockResolvedValue()

    wrapper.vm.navigateTo('general')

    expect(wrapper.vm.$router.push).toHaveBeenCalledWith('/audits/audit-1/general')
  })
})
