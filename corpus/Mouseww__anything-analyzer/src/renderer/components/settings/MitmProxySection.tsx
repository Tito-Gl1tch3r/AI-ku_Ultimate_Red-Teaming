import { useEffect, useState } from 'react'
import { InputNumber, Button, Switch, Badge, Tooltip, Modal, useToast } from '../../ui'
import {
  IconShield,
  IconExport,
  IconDelete,
  IconReload,
  IconWifi,
} from '../../ui/Icons'
import type { MitmProxyConfig } from '@shared/types'

export default function MitmProxySection() {
  const toast = useToast()
  const [mitmEnabled, setMitmEnabled] = useState(false)
  const [mitmPort, setMitmPort] = useState(8888)
  const [mitmRunning, setMitmRunning] = useState(false)
  const [mitmCaInstalled, setMitmCaInstalled] = useState(false)
  const [mitmCaInitialized, setMitmCaInitialized] = useState(false)
  const [mitmSystemProxy, setMitmSystemProxy] = useState(false)
  const [mitmLoading, setMitmLoading] = useState(false)
  const [regenConfirmOpen, setRegenConfirmOpen] = useState(false)
  const [localIPs, setLocalIPs] = useState<string[]>([])

  useEffect(() => {
    window.electronAPI.getMitmProxyConfig().then(config => {
      setMitmEnabled(config.enabled)
      setMitmPort(config.port)
      setMitmCaInstalled(config.caInstalled)
      setMitmSystemProxy(config.systemProxy)
    })
    window.electronAPI.getMitmProxyStatus().then(status => {
      setMitmRunning(status.running)
      setMitmCaInitialized(status.caInitialized)
      if (status.caInstalled !== undefined) setMitmCaInstalled(status.caInstalled)
      if (status.systemProxyEnabled !== undefined) setMitmSystemProxy(status.systemProxyEnabled)
      if (status.localIPs) setLocalIPs(status.localIPs)
    })
  }, [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%' }}>
      <div>
        <Badge
          color={mitmRunning ? 'var(--color-success)' : 'var(--text-muted)'}
          label={mitmRunning ? '运行中' : '已停止'}
          style={{ fontSize: 'var(--font-size-sm)' }}
        />
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 'var(--font-size-base)' }}>启用 MITM 代理</span>
        <Switch checked={mitmEnabled} onChange={setMitmEnabled} />
      </div>

      {mitmEnabled && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 'var(--font-size-base)' }}>端口</span>
            <InputNumber
              min={1024}
              max={65535}
              value={mitmPort}
              onChange={v => v !== null && setMitmPort(v)}
              style={{ width: 120 }}
            />
          </div>

          {/* System Proxy Toggle */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Tooltip title="将系统 HTTP/HTTPS 代理指向 MITM 代理，无需手动配置即可捕获所有应用流量">
              <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 'var(--font-size-base)', cursor: 'default' }}>
                <IconWifi size={14} />
                设为系统代理
              </span>
            </Tooltip>
            <Switch
              checked={mitmSystemProxy}
              disabled={mitmLoading}
              onChange={async (checked) => {
                setMitmLoading(true)
                try {
                  if (checked) {
                    const result = await window.electronAPI.enableMitmSystemProxy()
                    if (result.success) {
                      setMitmSystemProxy(true)
                      toast.success('已设为系统代理')
                    } else {
                      toast.error(result.error || '设置系统代理失败')
                    }
                  } else {
                    const result = await window.electronAPI.disableMitmSystemProxy()
                    if (result.success) {
                      setMitmSystemProxy(false)
                      toast.success('已取消系统代理')
                    } else {
                      toast.error(result.error || '取消系统代理失败')
                    }
                  }
                } finally {
                  setMitmLoading(false)
                }
              }}
            />
          </div>
          {mitmSystemProxy && (
            <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
              所有应用的流量将自动通过 MITM 代理，关闭应用时自动还原
            </span>
          )}

          {/* CA Certificate Management */}
          <div style={{ marginTop: 4 }}>
            <span style={{ fontWeight: 600, fontSize: 'var(--font-size-base)' }}>CA 证书管理</span>
          </div>

          {!mitmCaInstalled ? (
            <>
              <div style={{
                padding: '6px 12px',
                background: 'var(--color-warning-bg)',
                border: '1px solid var(--color-warning-border)',
                borderLeft: '3px solid var(--color-warning)',
                borderRadius: 4,
                fontSize: 'var(--font-size-sm)',
                color: 'var(--text-primary)',
              }}>
                ⚠ CA 证书未安装到系统，HTTPS 流量将无法拦截
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <Button
                  variant="primary"
                  icon={<IconShield size={14} />}
                  loading={mitmLoading}
                  onClick={async () => {
                    setMitmLoading(true)
                    try {
                      const result = await window.electronAPI.installMitmCA()
                      if (result.success) {
                        setMitmCaInstalled(true)
                        toast.success('CA 证书已安装到系统信任链')
                      } else {
                        toast.error(result.error || '安装失败')
                      }
                    } finally {
                      setMitmLoading(false)
                    }
                  }}
                >
                  一键安装 CA 证书
                </Button>
                <Button
                  icon={<IconExport size={14} />}
                  onClick={() => window.electronAPI.exportMitmCA()}
                >
                  导出
                </Button>
              </div>
            </>
          ) : (
            <>
              <div style={{
                padding: '6px 12px',
                background: 'var(--color-success-bg)',
                border: '1px solid var(--color-success-border)',
                borderLeft: '3px solid var(--color-success)',
                borderRadius: 4,
                fontSize: 'var(--font-size-sm)',
                color: 'var(--text-primary)',
              }}>
                ✓ CA 证书已安装
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <Button
                  icon={<IconDelete size={14} />}
                  loading={mitmLoading}
                  onClick={async () => {
                    setMitmLoading(true)
                    try {
                      const result = await window.electronAPI.uninstallMitmCA()
                      if (result.success) {
                        setMitmCaInstalled(false)
                        toast.success('CA 证书已卸载')
                      } else {
                        toast.error(result.error || '卸载失败')
                      }
                    } finally {
                      setMitmLoading(false)
                    }
                  }}
                >
                  卸载证书
                </Button>
                <Button
                  icon={<IconExport size={14} />}
                  onClick={() => window.electronAPI.exportMitmCA()}
                >
                  导出
                </Button>
                <Button
                  variant="danger"
                  icon={<IconReload size={14} />}
                  loading={mitmLoading}
                  onClick={() => setRegenConfirmOpen(true)}
                >
                  重新生成 CA
                </Button>
              </div>
            </>
          )}

          {/* Usage Instructions */}
          {!mitmSystemProxy && (
            <div style={{ marginTop: 4 }}>
              <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
                在外部浏览器/设备中配置 HTTP 代理为：
              </span>
              <div style={{ marginTop: 4, display: 'flex', flexDirection: 'column', gap: 2 }}>
                {localIPs.length > 0 ? localIPs.map(ip => (
                  <code key={ip} style={{
                    background: 'var(--color-surface)',
                    padding: '2px 6px',
                    borderRadius: 4,
                    fontSize: 'var(--font-size-sm)',
                    fontFamily: 'var(--font-mono)',
                    userSelect: 'all',
                  }}>
                    {ip}:{mitmPort}
                  </code>
                )) : (
                  <code style={{
                    background: 'var(--color-surface)',
                    padding: '2px 6px',
                    borderRadius: 4,
                    fontSize: 'var(--font-size-sm)',
                    fontFamily: 'var(--font-mono)',
                  }}>
                    http://&lt;本机IP&gt;:{mitmPort}
                  </code>
                )}
              </div>
            </div>
          )}

          {/* Mobile cert download hint */}
          <div style={{
            marginTop: 4,
            padding: '8px 12px',
            background: 'var(--color-info-bg, rgba(59,130,246,0.08))',
            border: '1px solid var(--color-info-border, rgba(59,130,246,0.2))',
            borderRadius: 4,
            fontSize: 'var(--font-size-sm)',
            color: 'var(--text-secondary)',
            lineHeight: 1.6,
          }}>
            📱 手机安装证书：连接代理后，用浏览器访问{' '}
            <code style={{
              background: 'var(--color-surface)',
              padding: '1px 5px',
              borderRadius: 3,
              fontFamily: 'var(--font-mono)',
              fontSize: 'var(--font-size-sm)',
              userSelect: 'all',
            }}>
              http://cert.anything.test
            </code>
          </div>
        </>
      )}

      <Button variant="primary" block onClick={async () => {
        const config: MitmProxyConfig = {
          enabled: mitmEnabled,
          port: mitmPort,
          caInstalled: mitmCaInstalled,
          systemProxy: mitmSystemProxy,
        }
        await window.electronAPI.saveMitmProxyConfig(config)
        toast.success('MITM 代理设置已保存')
        const status = await window.electronAPI.getMitmProxyStatus()
        setMitmRunning(status.running)
        setMitmCaInitialized(status.caInitialized)
      }}>
        保存 MITM 代理设置
      </Button>

      {/* Confirm modal for regenerating CA */}
      <Modal
        open={regenConfirmOpen}
        onClose={() => setRegenConfirmOpen(false)}
        title="重新生成 CA"
        footer={
          <div style={{ display: 'flex', gap: 8 }}>
            <Button onClick={() => setRegenConfirmOpen(false)}>取消</Button>
            <Button
              variant="danger"
              onClick={async () => {
                setRegenConfirmOpen(false)
                setMitmLoading(true)
                try {
                  await window.electronAPI.regenerateMitmCA()
                  setMitmCaInstalled(false)
                  setMitmRunning(false)
                  toast.success('CA 已重新生成，请重新安装证书')
                } finally {
                  setMitmLoading(false)
                }
              }}
            >
              确认
            </Button>
          </div>
        }
      >
        <p style={{ margin: 0, fontSize: 'var(--font-size-base)' }}>
          重新生成后需要重新安装证书，已配置代理的设备将出现证书错误。确定继续？
        </p>
      </Modal>
    </div>
  )
}
