// Persistent compose operation state — survives component unmount/remount
// Event listeners are registered once and never torn down.

let _initialized = false;
let _listeners = [];

export const composeState = {
  status: 'idle',   // idle | running | done | error
  action: '',       // up | down
  error: '',
  logs: [],
};

export function initComposeEvents(EventsOn) {
  if (_initialized) return;
  _initialized = true;

  EventsOn('compose-status', (data) => {
    composeState.action = data.action || '';
    if (data.phase === 'running') {
      composeState.status = 'running';
      composeState.error = '';
      composeState.logs = [];
    } else if (data.phase === 'done') {
      composeState.status = 'done';
      composeState.error = '';
    } else if (data.phase === 'error') {
      composeState.status = 'error';
      composeState.error = data.error || '';
    }
    _notify();
  });

  EventsOn('compose-log', (data) => {
    if (data.message) {
      composeState.logs = [...composeState.logs, { time: new Date().toLocaleTimeString(), message: data.message }];
      _notify();
    }
  });
}

export function dismissComposeStatus() {
  composeState.status = 'idle';
  composeState.error = '';
  composeState.logs = [];
  _notify();
}

// Simple pub/sub for reactive updates
export function onComposeStateChange(fn) {
  _listeners.push(fn);
  return () => {
    _listeners = _listeners.filter(l => l !== fn);
  };
}

function _notify() {
  _listeners.forEach(fn => fn({ ...composeState }));
}
