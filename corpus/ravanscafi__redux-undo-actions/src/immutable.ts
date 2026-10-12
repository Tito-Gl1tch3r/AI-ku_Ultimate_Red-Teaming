import type { UnknownAction } from 'redux'
import type { HistoryAction } from './types'

// A frozen array can still contain mutable entries. Only arrays recorded here
// can be reused without checking every action again.
const capturedHistoryArrays = new WeakSet<object>()

export function captureHistoryAction<Action extends UnknownAction>(
  action: Action,
  undone = false,
  immutable = true,
): HistoryAction<Action> {
  if (!immutable) {
    return { action, undone }
  }

  return Object.freeze({
    action: cloneAndFreezePlainData(action, 'action'),
    undone,
  })
}

export function setHistoryActionUndone<Action extends UnknownAction>(
  historyAction: HistoryAction<Action>,
  undone: boolean,
  immutable = true,
): HistoryAction<Action> {
  const next = { action: historyAction.action, undone }
  return immutable ? Object.freeze(next) : next
}

export function freezeHistoryActions<Action extends UnknownAction>(
  actions: HistoryAction<Action>[],
  immutable = true,
): readonly HistoryAction<Action>[] {
  if (!immutable) {
    return actions
  }

  const frozenActions = Object.freeze(actions)
  capturedHistoryArrays.add(frozenActions)
  return frozenActions
}

export function isCapturedHistoryActions(
  actions: readonly HistoryAction<UnknownAction>[],
): boolean {
  return capturedHistoryArrays.has(actions)
}

export function captureHistoryActions<Action extends UnknownAction>(
  actions: readonly HistoryAction<Action>[],
  immutable = true,
): readonly HistoryAction<Action>[] {
  if (!immutable) {
    return actions
  }

  return freezeHistoryActions(
    actions.map(({ action, undone }) =>
      captureHistoryAction(action, undone, immutable),
    ),
    immutable,
  )
}

function cloneAndFreezePlainData<T>(
  value: T,
  path: string,
  seen: WeakMap<object, unknown> = new WeakMap<object, unknown>(),
): T {
  if (typeof value === 'function') {
    throw new TypeError(
      `Cannot store function at ${path}. Action history only supports primitives, arrays, and plain objects.`,
    )
  }

  if (typeof value !== 'object' || value === null) {
    return value
  }

  const existing = seen.get(value)
  if (existing !== undefined) {
    return existing as T
  }

  if (Array.isArray(value)) {
    const copy: unknown[] = new Array(value.length)
    seen.set(value, copy)

    for (const key of Reflect.ownKeys(value)) {
      if (key === 'length') {
        continue
      }
      const descriptor = Object.getOwnPropertyDescriptor(value, key)
      if (!descriptor) {
        continue
      }
      if (!('value' in descriptor)) {
        throw new TypeError(
          `Cannot store accessor property at ${formatPath(path, key)}. Action history only supports plain data properties.`,
        )
      }
      Object.defineProperty(copy, key, {
        configurable: false,
        enumerable: descriptor.enumerable,
        value: cloneAndFreezePlainData(
          descriptor.value as unknown,
          formatPath(path, key),
          seen,
        ),
        writable: false,
      })
    }
    return Object.freeze(copy) as T
  }

  const prototype = Reflect.getPrototypeOf(value)
  if (prototype !== Object.prototype && prototype !== null) {
    throw new TypeError(
      `Cannot store non-plain value at ${path}. Action history only supports primitives, arrays, and plain objects.`,
    )
  }

  const copy = Object.create(prototype) as Record<PropertyKey, unknown>
  seen.set(value, copy)

  for (const key of Reflect.ownKeys(value)) {
    const descriptor = Object.getOwnPropertyDescriptor(value, key)
    if (!descriptor) {
      continue
    }
    if (!('value' in descriptor)) {
      throw new TypeError(
        `Cannot store accessor property at ${formatPath(path, key)}. Action history only supports plain data properties.`,
      )
    }
    Object.defineProperty(copy, key, {
      configurable: false,
      enumerable: descriptor.enumerable,
      value: cloneAndFreezePlainData(
        descriptor.value as unknown,
        formatPath(path, key),
        seen,
      ),
      writable: false,
    })
  }

  return Object.freeze(copy) as T
}

function formatPath(path: string, key: PropertyKey): string {
  return typeof key === 'symbol'
    ? `${path}[${String(key)}]`
    : `${path}.${String(key)}`
}
