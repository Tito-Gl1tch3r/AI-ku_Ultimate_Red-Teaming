import { useEffect, useState, useCallback } from 'react'
import { Modal, Button, Input, TextArea, Switch, Popconfirm, useToast } from '../ui'
import { IconPlus, IconDelete, IconSave, IconApi } from '../ui/Icons'
import { v4 as uuidv4 } from 'uuid'
import type { MCPServerConfig } from '@shared/types'

interface Props {
  open: boolean
  onClose: () => void
}

/** stdio 默认 JSON 模板 */
const STDIO_TEMPLATE = JSON.stringify({ command: '', args: [], env: {} }, null, 2)
/** HTTP 默认 JSON 模板 */
const HTTP_TEMPLATE = JSON.stringify({ url: '' }, null, 2)

/**
 * 从 MCPServerConfig 提取传输相关字段，生成 JSON 文本
 */
function configToJson(config: MCPServerConfig): string {
  if (config.transport === 'streamableHttp') {
    const payload: Record<string, unknown> = { url: config.url }
    if (config.headers && Object.keys(config.headers).length > 0) {
      payload.headers = config.headers
    }
    return JSON.stringify(payload, null, 2)
  }
  return JSON.stringify(
    { command: config.command, args: config.args, env: config.env },
    null,
    2,
  )
}

/**
 * 获取左侧列表中的描述文本
 */
function getServerDescription(server: MCPServerConfig): string {
  if (server.transport === 'streamableHttp') {
    return server.url || '未配置 URL'
  }
  return [server.command, ...server.args].filter(Boolean).join(' ') || '未配置命令'
}

export default function MCPServerModal({ open, onClose }: Props) {
  const toast = useToast()
  const [servers, setServers] = useState<MCPServerConfig[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<MCPServerConfig | null>(null)
  const [dirty, setDirty] = useState(false)

  // 传输类型 + JSON 编辑器状态
  const [transportType, setTransportType] = useState<'stdio' | 'streamableHttp'>('stdio')
  const [jsonText, setJsonText] = useState(STDIO_TEMPLATE)
  const [jsonError, setJsonError] = useState<string | null>(null)

  const loadAll = useCallback(async () => {
    const list = await window.electronAPI.getMCPServers()
    setServers(list)
    if (!selectedId && list.length > 0) {
      selectServer(list[0])
    }
  }, [selectedId])

  useEffect(() => {
    if (open) loadAll()
  }, [open]) // eslint-disable-line react-hooks/exhaustive-deps

  const selectServer = (server: MCPServerConfig) => {
    setSelectedId(server.id)
    setEditForm({ ...server })
    setTransportType(server.transport)
    setJsonText(configToJson(server))
    setJsonError(null)
    setDirty(false)
  }

  const handleSelect = (id: string) => {
    const s = servers.find((srv) => srv.id === id)
    if (s) selectServer(s)
  }

  const handleTransportTypeChange = (type: 'stdio' | 'streamableHttp') => {
    setTransportType(type)
    const template = type === 'stdio' ? STDIO_TEMPLATE : HTTP_TEMPLATE
    setJsonText(template)
    setJsonError(null)
    if (editForm) {
      const base = { id: editForm.id, name: editForm.name, enabled: editForm.enabled }
      setEditForm(
        type === 'stdio'
          ? { ...base, transport: 'stdio', command: '', args: [], env: {} }
          : { ...base, transport: 'streamableHttp', url: '' },
      )
      setDirty(true)
    }
  }

  const handleJsonChange = (text: string) => {
    setJsonText(text)
    setDirty(true)
    try {
      const parsed = JSON.parse(text)
      setJsonError(null)
      // 自动检测传输类型
      if (parsed.url && !parsed.command) {
        setTransportType('streamableHttp')
      } else if (parsed.command && !parsed.url) {
        setTransportType('stdio')
      }
    } catch (e) {
      setJsonError(`JSON 格式错误: ${(e as Error).message}`)
    }
  }

  const handleNameChange = (name: string) => {
    if (!editForm) return
    setEditForm({ ...editForm, name } as MCPServerConfig)
    setDirty(true)
  }

  const handleEnabledChange = (enabled: boolean) => {
    if (!editForm) return
    setEditForm({ ...editForm, enabled } as MCPServerConfig)
    setDirty(true)
  }

  const handleSave = async () => {
    if (!editForm) return
    if (!editForm.name.trim()) {
      toast.warning('请输入服务器名称')
      return
    }

    let parsed: Record<string, unknown>
    try {
      parsed = JSON.parse(jsonText)
    } catch (e) {
      toast.error(`JSON 格式错误: ${(e as Error).message}`)
      return
    }

    let serverConfig: MCPServerConfig
    const base = { id: editForm.id, name: editForm.name, enabled: editForm.enabled }

    if (transportType === 'streamableHttp') {
      const url = parsed.url
      if (typeof url !== 'string' || !url.trim()) {
        toast.warning('请输入服务器 URL')
        return
      }
      try {
        new URL(url)
      } catch {
        toast.warning('URL 格式无效')
        return
      }
      serverConfig = {
        ...base,
        transport: 'streamableHttp',
        url: (url as string).trim(),
        headers: (parsed.headers as Record<string, string>) || undefined,
      }
    } else {
      const command = parsed.command
      if (typeof command !== 'string' || !command.trim()) {
        toast.warning('请输入启动命令')
        return
      }
      serverConfig = {
        ...base,
        transport: 'stdio',
        command: (command as string).trim(),
        args: Array.isArray(parsed.args) ? parsed.args.map(String) : [],
        env: (parsed.env as Record<string, string>) || {},
      }
    }

    await window.electronAPI.saveMCPServer(serverConfig)
    toast.success('MCP 服务器已保存')
    setDirty(false)
    const list = await window.electronAPI.getMCPServers()
    setServers(list)
  }

  const handleDelete = async () => {
    if (!editForm) return
    await window.electronAPI.deleteMCPServer(editForm.id)
    toast.success('MCP 服务器已删除')
    setSelectedId(null)
    setEditForm(null)
    setDirty(false)
    const list = await window.electronAPI.getMCPServers()
    setServers(list)
    if (list.length > 0) selectServer(list[0])
  }

  const handleCreate = () => {
    const id = uuidv4()
    const newServer: MCPServerConfig = {
      id,
      name: '',
      enabled: true,
      transport: 'stdio',
      command: '',
      args: [],
      env: {},
    }
    setSelectedId(id)
    setEditForm(newServer)
    setTransportType('stdio')
    setJsonText(STDIO_TEMPLATE)
    setJsonError(null)
    setDirty(true)
  }

  return (
    <Modal
      title="MCP 服务器管理"
      open={open}
      onClose={onClose}
      width={800}
    >
      {/* Negate modal body padding so sidebar border runs edge-to-edge */}
      <div style={{ margin: '-16px -24px', display: 'flex', height: 480, overflow: 'hidden' }}>
        {/* Left: server list */}
        <div
          style={{
            width: 200,
            borderRight: '1px solid var(--color-border)',
            overflow: 'auto',
            flexShrink: 0,
          }}
        >
          <div style={{ padding: '8px 12px' }}>
            <Button
              variant="dashed"
              icon={<IconPlus size={13} />}
              block
              size="sm"
              onClick={handleCreate}
            >
              添加服务器
            </Button>
          </div>
          <div>
            {servers.map((item) => (
              <div
                key={item.id}
                onClick={() => handleSelect(item.id)}
                style={{
                  cursor: 'pointer',
                  padding: '8px 12px',
                  background: selectedId === item.id ? 'var(--color-accent-bg)' : 'transparent',
                  borderLeft: selectedId === item.id ? '3px solid var(--color-accent)' : '3px solid transparent',
                }}
              >
                <div style={{ minWidth: 0, width: '100%' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 2 }}>
                    <IconApi
                      size={12}
                      style={{ color: item.enabled ? 'var(--color-success)' : 'var(--text-muted)', flexShrink: 0 }}
                    />
                    <span style={{
                      fontSize: 'var(--font-size-base)',
                      flex: 1,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      color: 'var(--text-primary)',
                    }}>
                      {item.name || '未命名'}
                    </span>
                  </div>
                  <span style={{
                    fontSize: 'var(--font-size-xs)',
                    color: 'var(--text-secondary)',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    display: 'block',
                  }}>
                    {getServerDescription(item)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: edit panel */}
        <div
          style={{
            flex: 1,
            padding: 16,
            overflow: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
          }}
        >
          {editForm ? (
            <>
              {/* 名称 + 启用 */}
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <div style={{ flex: 1 }}>
                  <span style={{ display: 'block', fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginBottom: 4 }}>
                    名称
                  </span>
                  <Input
                    value={editForm.name}
                    onChange={(e) => handleNameChange(e.target.value)}
                    placeholder="如：文件系统 / 远程搜索"
                    inputSize="sm"
                  />
                </div>
                <div style={{ paddingTop: 18 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>启用</span>
                    <Switch
                      checked={editForm.enabled}
                      onChange={handleEnabledChange}
                    />
                  </div>
                </div>
              </div>

              {/* 传输类型选择 */}
              <div>
                <span style={{ display: 'block', fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginBottom: 4 }}>
                  传输类型
                </span>
                <div style={{
                  display: 'flex',
                  background: 'var(--color-surface)',
                  borderRadius: 6,
                  padding: 2,
                  width: 'fit-content',
                }}>
                  {[
                    { label: '本地命令 (stdio)', value: 'stdio' },
                    { label: '远程服务 (HTTP)', value: 'streamableHttp' },
                  ].map(opt => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => handleTransportTypeChange(opt.value as 'stdio' | 'streamableHttp')}
                      style={{
                        padding: '3px 10px',
                        fontSize: 'var(--font-size-sm)',
                        border: 'none',
                        borderRadius: 4,
                        cursor: 'pointer',
                        background: transportType === opt.value ? 'var(--color-accent)' : 'transparent',
                        color: transportType === opt.value ? 'var(--color-base)' : 'var(--text-secondary)',
                        transition: 'all 0.15s',
                      }}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* JSON 编辑器 */}
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                <span style={{ display: 'block', fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginBottom: 4 }}>
                  配置 (JSON)
                </span>
                <TextArea
                  value={jsonText}
                  onChange={(e) => handleJsonChange(e.target.value)}
                  autoSize={{ minRows: 6, maxRows: 12 }}
                  style={{
                    fontSize: 'var(--font-size-sm)',
                    fontFamily: "'Cascadia Code', 'Fira Code', 'JetBrains Mono', Consolas, monospace",
                    lineHeight: '1.6',
                    ...(jsonError ? { borderColor: 'var(--color-error)' } : {}),
                  }}
                  placeholder={
                    transportType === 'stdio'
                      ? '{\n  "command": "npx",\n  "args": ["-y", "@modelcontextprotocol/server-xxx"],\n  "env": {}\n}'
                      : '{\n  "url": "https://example.com/mcp",\n  "headers": {}\n}'
                  }
                />
                {jsonError && (
                  <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-error)', marginTop: 2 }}>
                    {jsonError}
                  </span>
                )}
              </div>

              {/* 操作按钮 */}
              <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 'auto' }}>
                <Popconfirm title="确定删除该服务器？" onConfirm={handleDelete} okText="确定" cancelText="取消">
                  <Button size="sm" variant="danger" icon={<IconDelete size={13} />}>
                    删除
                  </Button>
                </Popconfirm>
                <Button
                  variant="primary"
                  size="sm"
                  icon={<IconSave size={13} />}
                  onClick={handleSave}
                  disabled={!dirty || !!jsonError}
                >
                  保存
                </Button>
              </div>
            </>
          ) : (
            <div
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <span style={{ color: 'var(--text-secondary)' }}>选择或添加 MCP 服务器</span>
            </div>
          )}
        </div>
      </div>
    </Modal>
  )
}
