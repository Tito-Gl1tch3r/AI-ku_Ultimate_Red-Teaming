import { withServerState, ServerState, createServerAction } from '../src/server';
import { useServerState, useOptimisticServerState, useAutoRevalidation } from '../src/hooks';
import type { StateConfig } from '../src/types/types';

// Example state type
interface TodoState {
  todos: Array<{
    id: string;
    text: string;
    completed: boolean;
  }>;
  filter: 'all' | 'active' | 'completed';
}

// Initial state
const config: StateConfig<TodoState> = {
  initialState: {
    todos: [],
    filter: 'all'
  },
  options: {
    storage: {
      key: 'todo-app' as const,
      version: 1,
      migrations: {},
    },
    devTools: true
  }
};

// Server state configuration
const serverOptions = {
  key: 'todos',
  cache: {
    ttl: 60000, // 1 minute
    tags: ['todos'],
    revalidate: true
  }
};

// Server actions
async function addTodo(text: string) {
  return {
    todos: [
      {
        id: Math.random().toString(36).substr(2, 9),
        text,
        completed: false
      }
    ]
  };
}

async function toggleTodo(id: string) {
  // Simulate server delay
  await new Promise(resolve => setTimeout(resolve, 1000));
  return {
    todos: [{ id, completed: true }]
  };
}

// Server Component
function TodoApp({ serverState }: { serverState: ServerState<TodoState> }) {
  // Use optimistic updates for better UX
  const [state, setState] = useOptimisticServerState(serverState);
  
  // Auto-revalidate every minute
  useAutoRevalidation(serverState, ['todos'], 60000);

  // Create server actions
  const addTodoAction = createServerAction(serverState, addTodo);
  const toggleTodoAction = createServerAction(serverState, toggleTodo);

  if (!state) return <div>Loading...</div>;

  return (
    <div>
      <h1>Todo App with Server Integration</h1>
      
      {/* Add Todo Form */}
      <form onSubmit={async (e) => {
        e.preventDefault();
        const form = e.target as HTMLFormElement;
        const input = form.elements.namedItem('todo') as HTMLInputElement;
        
        // Optimistic update
        setState({
          todos: [
            ...state.todos,
            {
              id: 'temp-' + Date.now(),
              text: input.value,
              completed: false
            }
          ]
        });

        // Server action
        await addTodoAction(input.value);
        form.reset();
      }}>
        <input name="todo" placeholder="What needs to be done?" />
        <button type="submit">Add Todo</button>
      </form>

      {/* Todo List */}
      <ul>
        {state.todos.map(todo => (
          <li
            key={todo.id}
            style={{
              textDecoration: todo.completed ? 'line-through' : 'none',
              opacity: todo.id.startsWith('temp-') ? 0.5 : 1
            }}
          >
            <input
              type="checkbox"
              checked={todo.completed}
              onChange={() => toggleTodoAction(todo.id)}
            />
            {todo.text}
          </li>
        ))}
      </ul>

      {/* Filter Controls */}
      <div>
        <button
          onClick={() => setState({ filter: 'all' })}
          disabled={state.filter === 'all'}
        >
          All
        </button>
        <button
          onClick={() => setState({ filter: 'active' })}
          disabled={state.filter === 'active'}
        >
          Active
        </button>
        <button
          onClick={() => setState({ filter: 'completed' })}
          disabled={state.filter === 'completed'}
        >
          Completed
        </button>
      </div>
    </div>
  );
}

// Wrap with server state
export default withServerState(TodoApp, config, serverOptions); 