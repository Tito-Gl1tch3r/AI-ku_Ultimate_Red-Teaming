import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createTestWrapper } from '../../test-utils'
import TextareaArray from '@/components/textarea-array.vue'

describe('TextareaArray Component', () => {
  const defaultProps = {
    label: 'Test Label',
    modelValue: ['line1', 'line2', 'line3']
  }

  const createWrapper = (overrides = {}) => {
    return createTestWrapper(TextareaArray, {
      props: { ...defaultProps, ...overrides.props },
      slots: overrides.slots,
      global: {
        mocks: {
          ...(overrides.mocks || {})
        }
      }
    })
  }

  it('should render', () => {
    const wrapper = createWrapper()
    expect(wrapper.exists()).toBe(true)
  })

  describe('initial state', () => {
    it('should join modelValue array into a newline-separated string on mount', () => {
      const wrapper = createWrapper()
      expect(wrapper.vm.dataString).toBe('line1\nline2\nline3')
    })

    it('should set dataString to empty string when modelValue is undefined', () => {
      const wrapper = createWrapper({ props: { modelValue: undefined } })
      expect(wrapper.vm.dataString).toBe('')
    })

    it('should set dataString to empty string when modelValue is an empty array', () => {
      const wrapper = createWrapper({ props: { modelValue: [] } })
      expect(wrapper.vm.dataString).toBe('')
    })

    it('should initialize hasError to false', () => {
      const wrapper = createWrapper()
      expect(wrapper.vm.hasError).toBe(false)
    })
  })

  describe('props', () => {
    it('should accept label prop', () => {
      const wrapper = createWrapper({ props: { label: 'My Label' } })
      expect(wrapper.vm.label).toBe('My Label')
    })

    it('should accept readonly prop', () => {
      const wrapper = createWrapper({ props: { readonly: true } })
      expect(wrapper.vm.readonly).toBe(true)
    })

    it('should default readonly to false', () => {
      const wrapper = createWrapper()
      expect(wrapper.vm.readonly).toBe(false)
    })

    it('should default noEmptyLine to false', () => {
      const wrapper = createWrapper()
      expect(wrapper.vm.noEmptyLine).toBe(false)
    })

    it('should accept rules prop', () => {
      const rules = [val => !!val || 'Required']
      const wrapper = createWrapper({ props: { rules } })
      expect(wrapper.vm.rules).toEqual(rules)
    })

    it('should show required asterisk when rules are provided with non-empty first rule', () => {
      const rules = [val => !!val || 'Required']
      const wrapper = createWrapper({ props: { rules } })
      // The template shows asterisk when rules && rules[0] !== ''
      expect(wrapper.vm.rules).toBeTruthy()
      expect(wrapper.vm.rules[0]).not.toBe('')
    })

    it('should not show required asterisk when rules first element is empty string', () => {
      const rules = ['']
      const wrapper = createWrapper({ props: { rules } })
      const asterisk = wrapper.find('.text-red')
      expect(asterisk.exists()).toBe(false)
    })

    it('should not show required asterisk when rules are not provided', () => {
      const wrapper = createWrapper()
      const asterisk = wrapper.find('.text-red')
      expect(asterisk.exists()).toBe(false)
    })

    it('should not render the AI toolbar when readonly', () => {
      const wrapper = createWrapper({ props: { showAiButton: true, readonly: true } })
      expect(wrapper.find('.bg-grey-4').exists()).toBe(false)
    })

    it('should render the AI toolbar when editable', () => {
      const wrapper = createWrapper({ props: { showAiButton: true, readonly: false } })
      expect(wrapper.find('.bg-grey-4').exists()).toBe(true)
    })

    it('should right-align the AI button and use the shared gradient treatment', () => {
      const wrapper = createWrapper({ props: { showAiButton: true, readonly: false } })
      const bar = wrapper.find('.bg-grey-4')
      expect(bar.classes()).toContain('justify-end')
      expect(bar.find('q-btn').classes()).toContain('ai-gradient-icon-btn')
    })

    it('should default framedHeader to false', () => {
      const wrapper = createWrapper()
      expect(wrapper.vm.framedHeader).toBe(false)
      expect(wrapper.find('.textarea-array--framed').exists()).toBe(false)
    })

    it('should render a permanent framed header with its label and required marker', () => {
      const rules = [val => !!val || 'Required']
      const wrapper = createWrapper({ props: { framedHeader: true, rules } })

      expect(wrapper.find('.textarea-array--framed').exists()).toBe(true)
      expect(wrapper.find('.textarea-array__header').text()).toContain('Test Label')
      expect(wrapper.find('.textarea-array__header .text-red').exists()).toBe(true)
    })

    it('should not reserve empty validation space inside the textarea frame', () => {
      const wrapper = createWrapper({ props: { framedHeader: true, rules: [''] } })

      expect(wrapper.find('q-input').attributes()).toHaveProperty('hide-bottom-space')
    })

    it('should highlight only the outer frame during an active AI session', () => {
      const wrapper = createWrapper({
        props: { framedHeader: true, aiSessionActive: true }
      })

      expect(wrapper.find('.textarea-array--ai-active').exists()).toBe(true)
      expect(wrapper.find('q-input').classes()).not.toContain('ai-field-active')
    })

    it('should highlight the input itself without a framed header', () => {
      const wrapper = createWrapper({
        props: { aiSessionActive: true }
      })

      expect(wrapper.find('.textarea-array--ai-active').exists()).toBe(false)
      expect(wrapper.find('q-input').classes()).toContain('ai-field-active')
    })

    it('should keep the framed header but hide its AI action when readonly', () => {
      const wrapper = createWrapper({
        props: { framedHeader: true, showAiButton: true, readonly: true }
      })

      expect(wrapper.find('.textarea-array__header').exists()).toBe(true)
      expect(wrapper.find('[data-testid="textarea-array-ai-action"]').exists()).toBe(false)
    })

    it('should emit ai-click from the icon-only framed-header action', async () => {
      const wrapper = createWrapper({
        props: { framedHeader: true, showAiButton: true }
      })

      const action = wrapper.find('[data-testid="textarea-array-ai-action"]')
      expect(action.find('q-icon').attributes('name')).toBe('auto_awesome')
      await action.trigger('click')
      expect(wrapper.emitted('ai-click')).toHaveLength(1)
    })

    it('should render contextual header actions before the AI action', () => {
      const wrapper = createWrapper({
        props: { framedHeader: true, showAiButton: true },
        slots: { 'header-actions': '<button class="comment-action">Comment</button>' }
      })

      const actions = wrapper.find('.textarea-array__header .q-gutter-xs')
      expect(actions.find('.comment-action').exists()).toBe(true)
      expect(actions.element.firstElementChild).toBe(actions.find('.comment-action').element)
    })
  })

  describe('watcher: modelValue', () => {
    it('should update dataString when modelValue changes', async () => {
      const wrapper = createWrapper()
      expect(wrapper.vm.dataString).toBe('line1\nline2\nline3')

      await wrapper.setProps({ modelValue: ['a', 'b'] })
      expect(wrapper.vm.dataString).toBe('a\nb')
    })

    it('should set dataString to empty string when modelValue becomes null', async () => {
      const wrapper = createWrapper()
      await wrapper.setProps({ modelValue: null })
      expect(wrapper.vm.dataString).toBe('')
    })

    it('should not update dataString if the joined value matches current dataString', async () => {
      const wrapper = createWrapper()
      const original = wrapper.vm.dataString

      // Setting the same value should not trigger a change
      await wrapper.setProps({ modelValue: ['line1', 'line2', 'line3'] })
      expect(wrapper.vm.dataString).toBe(original)
    })
  })

  describe('updateParent method', () => {
    it('should emit update:modelValue with split lines', async () => {
      const wrapper = createWrapper()
      wrapper.vm.dataString = 'foo\nbar\nbaz'
      wrapper.vm.updateParent()

      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
      expect(wrapper.emitted('update:modelValue')[0][0]).toEqual(['foo', 'bar', 'baz'])
    })

    it('should include empty lines when noEmptyLine is false', () => {
      const wrapper = createWrapper()
      wrapper.vm.dataString = 'foo\n\nbar\n'
      wrapper.vm.updateParent()

      expect(wrapper.emitted('update:modelValue')[0][0]).toEqual(['foo', '', 'bar', ''])
    })

    it('should filter out empty lines when noEmptyLine is true', () => {
      const wrapper = createWrapper({ props: { noEmptyLine: true } })
      wrapper.vm.dataString = 'foo\n\nbar\n'
      wrapper.vm.updateParent()

      expect(wrapper.emitted('update:modelValue')[0][0]).toEqual(['foo', 'bar'])
    })

    it('should handle single line input', () => {
      const wrapper = createWrapper()
      wrapper.vm.dataString = 'single'
      wrapper.vm.updateParent()

      expect(wrapper.emitted('update:modelValue')[0][0]).toEqual(['single'])
    })

    it('should handle empty string input', () => {
      const wrapper = createWrapper()
      wrapper.vm.dataString = ''
      wrapper.vm.updateParent()

      expect(wrapper.emitted('update:modelValue')[0][0]).toEqual([''])
    })

    it('should filter empty string from empty input when noEmptyLine is true', () => {
      const wrapper = createWrapper({ props: { noEmptyLine: true } })
      wrapper.vm.dataString = ''
      wrapper.vm.updateParent()

      expect(wrapper.emitted('update:modelValue')[0][0]).toEqual([])
    })
  })

  describe('validate method', () => {
    it('should call validate on the textarea ref and update hasError', () => {
      const wrapper = createWrapper()

      // Mock the ref
      const mockValidate = vi.fn()
      Object.defineProperty(wrapper.vm.$refs, 'textareaField', {
        value: { validate: mockValidate, hasError: true },
        writable: true,
        configurable: true
      })

      wrapper.vm.validate()

      expect(mockValidate).toHaveBeenCalled()
      expect(wrapper.vm.hasError).toBe(true)
    })

    it('should set hasError to false when validation passes', () => {
      const wrapper = createWrapper()

      Object.defineProperty(wrapper.vm.$refs, 'textareaField', {
        value: { validate: vi.fn(), hasError: false },
        writable: true,
        configurable: true
      })

      wrapper.vm.validate()
      expect(wrapper.vm.hasError).toBe(false)
    })
  })
})
