import React, { useState, useEffect } from 'react'
import { Button, Select, TextArea, Tag } from '../ui'
import {
  IconPlay,
  IconPause,
  IconStop,
  IconExperiment,
  IconCheck,
  IconClose,
  IconLoading,
} from '../ui/Icons'
import { useLocale } from '../i18n'
import type { SessionStatus, PromptTemplate } from '../../shared/types'
import styles from './ControlBar.module.css'

interface ControlBarProps {
  status: SessionStatus | null
  onStart: () => void
  onPause: () => void
  onResume: () => void
  onStop: () => void
  onAnalyze: (purpose?: string) => void
  hasRequests: boolean
  isAnalyzing?: boolean
  selectedSeqCount?: number
}

const ControlBar: React.FC<ControlBarProps> = ({
  status,
  onStart,
  onPause,
  onResume,
  onStop,
  onAnalyze,
  hasRequests,
  isAnalyzing = false,
  selectedSeqCount = 0,
}) => {
  const { t } = useLocale()
  const [purposeId, setPurposeId] = useState<string>('auto')
  const [customText, setCustomText] = useState('')
  const [customExpanded, setCustomExpanded] = useState(false)
  const [templates, setTemplates] = useState<PromptTemplate[]>([])

  useEffect(() => {
    window.electronAPI.getPromptTemplates().then(setTemplates).catch(() => {})
  }, [])

  const isRunning = status === 'running'
  const isPaused = status === 'paused'
  const isStopped = status === 'stopped' || status === null

  const handlePurposeChange = (value: string) => {
    if (value === 'custom') {
      setCustomExpanded(true)
    } else {
      setPurposeId(value)
      setCustomExpanded(false)
    }
  }

  const handleCustomConfirm = () => {
    const trimmed = customText.trim()
    if (trimmed) {
      setPurposeId('custom')
      setCustomExpanded(false)
    }
  }

  const handleCustomCancel = () => {
    setCustomExpanded(false)
    if (purposeId !== 'custom') setCustomText('')
  }

  const handleAnalyze = () => {
    if (purposeId === 'custom') {
      onAnalyze(customText.trim() || undefined)
    } else if (purposeId === 'auto') {
      onAnalyze(undefined)
    } else {
      onAnalyze(purposeId)
    }
  }

  const selectOptions = [
    ...templates.map((tpl) => ({ label: tpl.name, value: tpl.id })),
    { label: t('capture.custom'), value: 'custom' },
  ]

  return (
    <div className={styles.controlBar}>
      {/* Main control row */}
      <div className={styles.mainRow}>
        <div className={styles.leftGroup}>
          <Button
            variant="success"
            icon={<IconPlay size={14} />}
            disabled={!isStopped}
            onClick={onStart}
          >
            {t('capture.start')}
          </Button>

          <Button
            variant="default"
            icon={isPaused ? <IconPlay size={14} /> : <IconPause size={14} />}
            disabled={!(isRunning || isPaused)}
            onClick={isPaused ? onResume : onPause}
          >
            {isPaused ? t('capture.resume') : t('capture.pause')}
          </Button>

          <Button
            variant="danger"
            icon={<IconStop size={14} />}
            disabled={!(isRunning || isPaused)}
            onClick={onStop}
          >
            {t('capture.stop')}
          </Button>

          <Select
            value={customExpanded ? 'custom' : purposeId}
            onChange={handlePurposeChange}
            style={{ width: 160 }}
            disabled={isAnalyzing}
            options={selectOptions}
          />

          <Button
            variant="primary"
            icon={<IconExperiment size={14} />}
            disabled={!(isStopped && hasRequests) || isAnalyzing}
            loading={isAnalyzing}
            onClick={handleAnalyze}
          >
            {isAnalyzing
              ? t('capture.analyze') + '...'
              : selectedSeqCount > 0
                ? t('capture.analyzeSelected', { count: selectedSeqCount })
                : t('capture.analyze')}
          </Button>
        </div>

        {/* Right side: status tags */}
        <div className={styles.rightGroup}>
          {purposeId === 'custom' && customText.trim() && !customExpanded && (
            <Tag color="info" style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {customText.trim()}
            </Tag>
          )}
          {isRunning && (
            <Tag color="success">
              <span className={styles.statusTag}>
                <IconLoading size={12} />
                {t('capture.running')}
              </span>
            </Tag>
          )}
          {isPaused && <Tag color="warning">{t('capture.paused')}</Tag>}
          {isStopped && status !== null && <Tag color="default">{t('capture.stopped')}</Tag>}
        </div>
      </div>

      {/* Inline custom purpose input */}
      {customExpanded && (
        <div className={styles.customRow}>
          <div className={styles.customInput}>
            <TextArea
              value={customText}
              onChange={(e) => setCustomText(e.target.value)}
              placeholder={t('capture.customPurpose')}
              autoSize={{ minRows: 1, maxRows: 4 }}
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleCustomConfirm()
                }
              }}
            />
          </div>
          <div className={styles.customBtns}>
            <Button
              variant="primary"
              size="sm"
              iconOnly
              icon={<IconCheck size={14} />}
              disabled={!customText.trim()}
              onClick={handleCustomConfirm}
            />
            <Button
              size="sm"
              iconOnly
              icon={<IconClose size={14} />}
              onClick={handleCustomCancel}
            />
          </div>
        </div>
      )}
    </div>
  )
}

export default ControlBar
