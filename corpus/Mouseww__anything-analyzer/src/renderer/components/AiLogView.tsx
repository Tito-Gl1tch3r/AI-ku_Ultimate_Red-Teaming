import React, { useEffect, useState, useCallback } from 'react'
import { useLocale } from '../i18n'
import { Empty } from '../ui'
import { AiLogList } from './AiLogList'
import { AiLogDetail } from './AiLogDetail'
import type { AiRequestLog } from '@shared/types'
import styles from './AiLogView.module.css'

interface AiLogViewProps {
  sessionId: string
  sessionName?: string
  onBack: () => void
}

export const AiLogView: React.FC<AiLogViewProps> = ({ sessionId, sessionName, onBack }) => {
  const { t } = useLocale()
  const [logs, setLogs] = useState<AiRequestLog[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [isGlobal, setIsGlobal] = useState(false)

  const loadLogs = useCallback(async () => {
    const data = isGlobal
      ? await window.electronAPI.getAiRequestLogsAll(200, 0)
      : await window.electronAPI.getAiRequestLogs(sessionId)
    setLogs(data)
    // Auto-select first if current selection not in list
    if (data.length > 0 && (selectedId === null || !data.some(l => l.id === selectedId))) {
      setSelectedId(data[0].id)
    }
    if (data.length === 0) setSelectedId(null)
  }, [sessionId, isGlobal, selectedId])

  useEffect(() => {
    loadLogs()
  }, [sessionId, isGlobal])  // eslint-disable-line react-hooks/exhaustive-deps

  if (logs.length === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.toolbar}>
          <button className={styles.backBtn} onClick={onBack}>{t('aiLog.backToReport')}</button>
        </div>
        <div className={styles.emptyContainer}>
          <Empty description={t('aiLog.noData')} />
        </div>
      </div>
    )
  }

  return (
    <div className={styles.container}>
      {/* Toolbar */}
      <div className={styles.toolbar}>
        <button className={styles.backBtn} onClick={onBack}>
          {isGlobal ? t('aiLog.backToSession') : t('aiLog.backToReport')}
        </button>
        <div className={styles.toolbarSpacer} />
        {!isGlobal && sessionName && (
          <span className={styles.sessionLabel}>Session: {sessionName}</span>
        )}
        {isGlobal && (
          <span className={styles.globalLabel}>{t('aiLog.globalMode')}</span>
        )}
        <button
          className={styles.toggleBtn}
          onClick={() => {
            if (isGlobal) {
              setIsGlobal(false)
            } else {
              setIsGlobal(true)
            }
            setSelectedId(null)
          }}
        >
          {isGlobal ? t('aiLog.backToSession') : t('aiLog.viewAllSessions')}
        </button>
      </div>

      {/* Main content: list + detail */}
      <div className={styles.mainContent}>
        <AiLogList logs={logs} selectedId={selectedId} onSelect={setSelectedId} />
        <AiLogDetail logId={selectedId} />
      </div>
    </div>
  )
}
