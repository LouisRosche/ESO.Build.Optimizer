# React + Vite + TypeScript Best Practices

> **Last Updated**: January 2026
> **Source**: [Vite Guide](https://vite.dev/guide/), [React Docs](https://react.dev/)

---

## Why Vite in 2026

- **Native ESM**: Serves modules directly during dev (~300ms startup)
- **HMR**: Hot module replacement in milliseconds
- **Optimized builds**: Uses Rollup for production
- **First-class TypeScript**: No config needed

```bash
# Create new project
npm create vite@latest my-app -- --template react-ts
```

---

## Project Structure

```
src/
├── main.tsx              # Entry point
├── App.tsx               # Root component
├── index.css             # Global styles
├── vite-env.d.ts         # Vite type declarations
├── api/                  # API client and hooks
│   ├── client.ts         # Axios/fetch wrapper
│   └── index.ts
├── components/           # Reusable UI components
│   ├── Button/
│   │   ├── Button.tsx
│   │   ├── Button.test.tsx
│   │   └── index.ts
│   └── index.ts          # Barrel export
├── hooks/                # Custom React hooks
│   ├── useApi.ts
│   └── index.ts
├── pages/                # Route components
│   ├── Dashboard.tsx
│   └── index.ts
├── types/                # TypeScript types
│   └── index.ts
└── utils/                # Helper functions
    └── index.ts
```

---

## Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Files | kebab-case | `run-card.tsx` |
| Components | PascalCase | `RunCard` |
| Functions | camelCase | `calculateDps` |
| Constants | SCREAMING_SNAKE | `MAX_DPS_THRESHOLD` |
| Types/Interfaces | PascalCase | `CombatRun` |

---

## TypeScript Configuration

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"]
}
```

---

## Component Patterns

### Functional Components with TypeScript

```tsx
interface RunCardProps {
  run: CombatRun;
  onSelect?: (runId: string) => void;
  className?: string;
}

export function RunCard({ run, onSelect, className }: RunCardProps) {
  const handleClick = () => {
    onSelect?.(run.id);
  };

  return (
    <div className={className} onClick={handleClick}>
      <h3>{run.content.name}</h3>
      <p>{run.metrics.dps.toLocaleString()} DPS</p>
    </div>
  );
}
```

### Custom Hooks

```tsx
// hooks/useRuns.ts
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';

export function useRuns(characterId?: string) {
  return useQuery({
    queryKey: ['runs', characterId],
    queryFn: () => apiClient.getRuns(characterId),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
```

---

## State Management

### React Query for Server State

```tsx
// Recommended for API data
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router />
    </QueryClientProvider>
  );
}
```

### Context for UI State

```tsx
// For theme, auth, etc.
const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}
```

---

## Routing (React Router v6+)

```tsx
import { createBrowserRouter, RouterProvider } from 'react-router-dom';

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'builds', element: <Builds /> },
      { path: 'analytics', element: <Analytics /> },
      { path: 'runs/:runId', element: <RunDetail /> },
    ],
  },
]);

function App() {
  return <RouterProvider router={router} />;
}
```

---

## Performance Optimization

### Code Splitting

```tsx
import { lazy, Suspense } from 'react';

// Lazy load heavy components
const Analytics = lazy(() => import('./pages/Analytics'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Analytics />
    </Suspense>
  );
}
```

### Memoization

```tsx
import { memo, useMemo, useCallback } from 'react';

// Memoize expensive components
const RunList = memo(function RunList({ runs }: { runs: CombatRun[] }) {
  return runs.map(run => <RunCard key={run.id} run={run} />);
});

// Memoize expensive calculations
function Dashboard({ runs }: { runs: CombatRun[] }) {
  const avgDps = useMemo(
    () => runs.reduce((sum, r) => sum + r.metrics.dps, 0) / runs.length,
    [runs]
  );

  // Memoize callbacks passed to children
  const handleSelect = useCallback((id: string) => {
    console.log('Selected:', id);
  }, []);

  return <RunList runs={runs} onSelect={handleSelect} />;
}
```

---

## Vite Configuration

```ts
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          charts: ['recharts'],
        },
      },
    },
  },
});
```

---

## Testing

```tsx
// Component test with Vitest + Testing Library
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { RunCard } from './RunCard';

describe('RunCard', () => {
  const mockRun = {
    id: '1',
    content: { name: 'Test Dungeon' },
    metrics: { dps: 50000 },
  };

  it('renders run info', () => {
    render(<RunCard run={mockRun} />);
    expect(screen.getByText('Test Dungeon')).toBeInTheDocument();
    expect(screen.getByText('50,000 DPS')).toBeInTheDocument();
  });

  it('calls onSelect when clicked', () => {
    const onSelect = vi.fn();
    render(<RunCard run={mockRun} onSelect={onSelect} />);
    fireEvent.click(screen.getByText('Test Dungeon'));
    expect(onSelect).toHaveBeenCalledWith('1');
  });
});
```

---

## TailwindCSS Integration

```js
// tailwind.config.js
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // ESO-inspired dark theme
        eso: {
          gold: '#c5a04a',
          dark: '#1a1a1a',
          darker: '#0d0d0d',
        },
      },
    },
  },
  plugins: [],
};
```

---

## Common Pitfalls

1. **Don't mutate state directly**: Always use setState or return new objects
2. **Avoid useEffect for derived state**: Use useMemo instead
3. **Don't over-memoize**: Profile first, optimize second
4. **Handle loading/error states**: Always show feedback to users
5. **Type your API responses**: Don't use `any`

---

*This document should be refreshed when React or Vite release major updates.*
