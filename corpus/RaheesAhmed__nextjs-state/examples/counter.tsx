import React from 'react';
import { createNextState } from '../src';

interface CounterState {
  count: number;
  lastUpdated: string;
}

const { Provider, useNextState } = createNextState<CounterState>({
  initialState: {
    count: 0,
    lastUpdated: new Date().toISOString(),
  },
});

const Counter: React.FC = () => {
  const { state, setState } = useNextState((state) => ({
    count: state.count,
    lastUpdated: state.lastUpdated,
  }));

  const increment = () => {
    setState({
      count: state.count + 1,
      lastUpdated: new Date().toISOString(),
    });
  };

  const decrement = () => {
    setState({
      count: state.count - 1,
      lastUpdated: new Date().toISOString(),
    });
  };

  return (
    <div>
      <h1>Counter Example</h1>
      <p>Count: {state.count}</p>
      <p>Last Updated: {new Date(state.lastUpdated).toLocaleString()}</p>
      <button onClick={increment}>Increment</button>
      <button onClick={decrement}>Decrement</button>
    </div>
  );
};

const App: React.FC = () => {
  return (
    <Provider>
      <Counter />
    </Provider>
  );
};

export default App;
