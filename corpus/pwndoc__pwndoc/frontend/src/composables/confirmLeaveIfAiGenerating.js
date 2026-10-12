import { Dialog } from 'quasar'
import { useAiGenerationStore } from '@/stores/ai-generation'
import { $t } from '@/boot/i18n'

function shouldConfirmLeave(store) {
  return store.isGenerating || (store.drawerOpen && store.isActive)
}

function confirmLeaveAiSession({ onLeave, onStay, dialog = {} }) {
  const store = useAiGenerationStore()

  if (!shouldConfirmLeave(store)) {
    onLeave()
    return
  }

  Dialog.create({
    title: dialog.title || $t('aiChat.leaveWhileGeneratingTitle'),
    message: dialog.message || (store.isGenerating ?
      $t('aiChat.leaveWhileGeneratingMessage') :
      $t('aiChat.leaveWhileAiSessionMessage')),
    ok: { label: dialog.okLabel || $t('btn.leave'), color: 'negative' },
    cancel: { label: dialog.cancelLabel || $t('btn.stay'), color: 'white' },
    focus: 'cancel'
  })
  .onOk(() => {
    store.cancelSession({ force: true })
    onLeave()
  })
  .onCancel(() => {
    if (onStay)
      onStay()
  })
}

export function runAfterAiGenerationCheck(callback, dialog) {
  confirmLeaveAiSession({ onLeave: callback, dialog })
}

export function confirmRouterLeaveIfAiGenerating(next) {
  confirmLeaveAiSession({
    onLeave: () => next(),
    onStay: () => next(false)
  })
}
