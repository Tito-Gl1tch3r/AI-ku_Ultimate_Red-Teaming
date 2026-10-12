import React, { useEffect, useState, useCallback } from 'react';
import type { DevTools } from './index';
import type { DeepReadonly, PerformanceMetrics } from '../types/types';

interface PanelProps<T extends object> {
  devTools: DevTools<T>;
  position?: 'right' | 'bottom';
  width?: number;
  height?: number;
}

export function DevToolsPanel<T extends object>({
  devTools,
  position = 'right',
  width = 300,
  height = 500,
}: PanelProps<T>) {
  const [selectedTab, setSelectedTab] = useState<'state' | 'actions' | 'performance'>('state');
  const [currentState, setCurrentState] = useState<DeepReadonly<T> | null>(null);
  const [actions, setActions] = useState<Array<{ type: string; payload: unknown; timestamp: number }>>([]);
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [selectedSnapshot, setSelectedSnapshot] = useState<number>(-1);
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    return devTools.subscribe((state) => {
      setCurrentState(state.currentState);
      setActions(state.actions);
      setMetrics(state.performance);
    });
  }, [devTools]);

  const handleTimeTravel = useCallback((index: number) => {
    setSelectedSnapshot(index);
    const state = devTools.jumpToState(index);
    if (state) {
      setCurrentState(state as DeepReadonly<T>);
    }
  }, [devTools]);

  const handleExport = useCallback(() => {
    const state = devTools.exportState();
    const blob = new Blob([state], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `next-state-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [devTools]);

  const handleImport = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const content = e.target?.result as string;
        const { state } = JSON.parse(content);
        devTools.importState(state);
      } catch (error) {
        console.error('Failed to import state:', error);
      }
    };
    reader.readAsText(file);
  }, [devTools]);

  if (isCollapsed) {
    return (
      <div
        style={{
          position: 'fixed',
          [position === 'right' ? 'right' : 'bottom']: 0,
          bottom: 0,
          padding: '8px',
          background: '#1a1a1a',
          color: '#fff',
          cursor: 'pointer',
          borderTopLeftRadius: '4px',
        }}
        onClick={() => setIsCollapsed(false)}
      >
        📊 DevTools
      </div>
    );
  }

  return (
    <div
      style={{
        position: 'fixed',
        [position === 'right' ? 'right' : 'bottom']: 0,
        bottom: 0,
        width: position === 'right' ? width : '100%',
        height: position === 'right' ? '100vh' : height,
        background: '#1a1a1a',
        color: '#fff',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '-2px 0 5px rgba(0,0,0,0.2)',
      }}
    >
      {/* Header */}
      <div style={{ padding: '8px', borderBottom: '1px solid #333', display: 'flex', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setSelectedTab('state')}
            style={{ background: selectedTab === 'state' ? '#333' : 'transparent' }}
          >
            State
          </button>
          <button
            onClick={() => setSelectedTab('actions')}
            style={{ background: selectedTab === 'actions' ? '#333' : 'transparent' }}
          >
            Actions
          </button>
          <button
            onClick={() => setSelectedTab('performance')}
            style={{ background: selectedTab === 'performance' ? '#333' : 'transparent' }}
          >
            Performance
          </button>
        </div>
        <button onClick={() => setIsCollapsed(true)}>×</button>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: 'auto', padding: '8px' }}>
        {selectedTab === 'state' && (
          <div>
            <div style={{ marginBottom: '8px', display: 'flex', gap: '8px' }}>
              <button onClick={handleExport}>Export</button>
              <label>
                Import
                <input
                  type="file"
                  accept=".json"
                  onChange={handleImport}
                  style={{ display: 'none' }}
                />
              </label>
            </div>
            <pre style={{ margin: 0 }}>
              {JSON.stringify(currentState, null, 2)}
            </pre>
          </div>
        )}

        {selectedTab === 'actions' && (
          <div>
            {actions.map((action, index) => (
              <div
                key={action.timestamp}
                style={{
                  padding: '4px',
                  cursor: 'pointer',
                  background: selectedSnapshot === index ? '#333' : 'transparent',
                }}
                onClick={() => handleTimeTravel(index)}
              >
                <div style={{ fontWeight: 'bold' }}>{action.type}</div>
                <div style={{ fontSize: '0.8em', color: '#999' }}>
                  {new Date(action.timestamp).toLocaleTimeString()}
                </div>
                {action.duration && (
                  <div style={{ fontSize: '0.8em', color: '#666' }}>
                    Duration: {action.duration.toFixed(2)}ms
                  </div>
                )}
                <pre style={{ margin: '4px 0', fontSize: '0.9em' }}>
                  {JSON.stringify(action.payload, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        )}

        {selectedTab === 'performance' && metrics && (
          <div>
            <div style={{ marginBottom: '16px' }}>
              <h3 style={{ margin: '0 0 8px' }}>Metrics</h3>
              <div>Total Updates: {metrics.updates}</div>
              <div>Active Listeners: {metrics.listeners}</div>
              <div>Average Update Time: {metrics.avgUpdateTime.toFixed(2)}ms</div>
              <div>Last Update Time: {metrics.lastUpdateTime.toFixed(2)}ms</div>
            </div>

            <div>
              <h3 style={{ margin: '0 0 8px' }}>Update Timeline</h3>
              <div style={{ display: 'flex', height: '100px', alignItems: 'flex-end', gap: '2px' }}>
                {actions.map((action) => (
                  <div
                    key={action.timestamp}
                    style={{
                      width: '8px',
                      height: `${Math.min(100, (action.duration || 0) / 2)}%`,
                      background: '#4caf50',
                      title: `${action.type}: ${action.duration}ms`,
                    }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
