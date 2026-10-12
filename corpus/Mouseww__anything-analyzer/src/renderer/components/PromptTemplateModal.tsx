import { useEffect, useState, useCallback } from 'react'
import { Modal, Button, Input, TextArea, Tag, Popconfirm, useToast } from '../ui'
import { IconPlus, IconUndo, IconDelete, IconSave } from '../ui/Icons'
import { v4 as uuidv4 } from 'uuid'
import type { PromptTemplate } from '@shared/types'

interface Props {
  open: boolean
  onClose: () => void
}

export default function PromptTemplateModal({ open, onClose }: Props) {
  const toast = useToast()
  const [templates, setTemplates] = useState<PromptTemplate[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<PromptTemplate | null>(null)
  const [dirty, setDirty] = useState(false)

  const loadAll = useCallback(async () => {
    const list = await window.electronAPI.getPromptTemplates()
    setTemplates(list)
    // Auto-select first if nothing selected
    if (!selectedId && list.length > 0) {
      setSelectedId(list[0].id)
      setEditForm({ ...list[0] })
    }
  }, [selectedId])

  useEffect(() => {
    if (open) loadAll()
  }, [open]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelect = (id: string) => {
    const t = templates.find((tpl) => tpl.id === id)
    if (!t) return
    setSelectedId(id)
    setEditForm({ ...t })
    setDirty(false)
  }

  const handleFieldChange = (field: keyof PromptTemplate, value: string) => {
    if (!editForm) return
    setEditForm({ ...editForm, [field]: value })
    setDirty(true)
  }

  const handleSave = async () => {
    if (!editForm) return
    await window.electronAPI.savePromptTemplate(editForm)
    toast.success('模板已保存')
    setDirty(false)
    await loadAll()
  }

  const handleReset = async () => {
    if (!editForm || !editForm.isBuiltin) return
    await window.electronAPI.resetPromptTemplate(editForm.id)
    toast.success('已恢复默认')
    const list = await window.electronAPI.getPromptTemplates()
    setTemplates(list)
    const restored = list.find((t) => t.id === editForm.id)
    if (restored) {
      setEditForm({ ...restored })
      setDirty(false)
    }
  }

  const handleDelete = async () => {
    if (!editForm || editForm.isBuiltin) return
    await window.electronAPI.deletePromptTemplate(editForm.id)
    toast.success('模板已删除')
    setSelectedId(null)
    setEditForm(null)
    setDirty(false)
    const list = await window.electronAPI.getPromptTemplates()
    setTemplates(list)
    if (list.length > 0) {
      setSelectedId(list[0].id)
      setEditForm({ ...list[0] })
    }
  }

  const handleCreate = () => {
    const newTemplate: PromptTemplate = {
      id: uuidv4(),
      name: '新模板',
      description: '',
      systemPrompt: '你是一位网站协议分析专家。你的任务是分析用户在网站上的操作过程中产生的HTTP请求、JS调用和存储变化，识别其业务场景，并生成结构化的协议分析报告。Be precise and technical. Output in Chinese (Simplified).',
      requirements: '',
      isBuiltin: false,
      isModified: false,
    }
    setSelectedId(newTemplate.id)
    setEditForm(newTemplate)
    setDirty(true)
  }

  return (
    <Modal
      title="提示词模板管理"
      open={open}
      onClose={onClose}
      width={800}
    >
      {/* Negate modal body padding so sidebar border runs edge-to-edge */}
      <div style={{ margin: '-16px -24px', display: 'flex', height: 520, overflow: 'hidden' }}>
        {/* Left: template list */}
        <div style={{
          width: 200,
          borderRight: '1px solid var(--color-border)',
          overflow: 'auto',
          flexShrink: 0,
        }}>
          <div style={{ padding: '8px 12px' }}>
            <Button
              variant="dashed"
              icon={<IconPlus size={13} />}
              block
              size="sm"
              onClick={handleCreate}
            >
              新建模板
            </Button>
          </div>
          <div>
            {templates.map((item) => (
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
                    <span style={{
                      fontSize: 'var(--font-size-base)',
                      flex: 1,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      color: 'var(--text-primary)',
                    }}>
                      {item.name}
                    </span>
                    {item.isBuiltin && (
                      <Tag style={{ fontSize: 'var(--font-size-2xs)', lineHeight: '16px', padding: '0 4px' }}>内置</Tag>
                    )}
                    {item.isModified && (
                      <Tag color="orange" style={{ fontSize: 'var(--font-size-2xs)', lineHeight: '16px', padding: '0 4px' }}>已改</Tag>
                    )}
                  </div>
                  <span style={{
                    fontSize: 'var(--font-size-xs)',
                    color: 'var(--text-secondary)',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    display: 'block',
                  }}>
                    {item.description}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: edit form */}
        <div style={{ flex: 1, padding: 16, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 12 }}>
          {editForm ? (
            <>
              <div style={{ display: 'flex', gap: 8 }}>
                <div style={{ flex: 1 }}>
                  <span style={{ display: 'block', fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginBottom: 4 }}>
                    名称
                  </span>
                  <Input
                    value={editForm.name}
                    onChange={(e) => handleFieldChange('name', e.target.value)}
                    inputSize="sm"
                    disabled={editForm.isBuiltin}
                  />
                </div>
                <div style={{ flex: 2 }}>
                  <span style={{ display: 'block', fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginBottom: 4 }}>
                    描述
                  </span>
                  <Input
                    value={editForm.description}
                    onChange={(e) => handleFieldChange('description', e.target.value)}
                    inputSize="sm"
                  />
                </div>
              </div>

              <div>
                <span style={{ display: 'block', fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginBottom: 4 }}>
                  System Prompt
                </span>
                <TextArea
                  value={editForm.systemPrompt}
                  onChange={(e) => handleFieldChange('systemPrompt', e.target.value)}
                  autoSize={{ minRows: 3, maxRows: 6 }}
                  style={{ fontSize: 'var(--font-size-sm)' }}
                />
              </div>

              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                <span style={{ display: 'block', fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginBottom: 4 }}>
                  分析要求
                </span>
                <TextArea
                  value={editForm.requirements}
                  onChange={(e) => handleFieldChange('requirements', e.target.value)}
                  style={{ flex: 1, fontSize: 'var(--font-size-sm)', resize: 'none' }}
                />
              </div>

              <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                {editForm.isBuiltin && editForm.isModified && (
                  <Popconfirm title="确定恢复默认？" onConfirm={handleReset} okText="确定" cancelText="取消">
                    <Button size="sm" icon={<IconUndo size={13} />}>恢复默认</Button>
                  </Popconfirm>
                )}
                {!editForm.isBuiltin && (
                  <Popconfirm title="确定删除该模板？" onConfirm={handleDelete} okText="确定" cancelText="取消">
                    <Button size="sm" variant="danger" icon={<IconDelete size={13} />}>删除</Button>
                  </Popconfirm>
                )}
                <Button
                  variant="primary"
                  size="sm"
                  icon={<IconSave size={13} />}
                  onClick={handleSave}
                  disabled={!dirty}
                >
                  保存
                </Button>
              </div>
            </>
          ) : (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ color: 'var(--text-secondary)' }}>选择或新建模板</span>
            </div>
          )}
        </div>
      </div>
    </Modal>
  )
}
