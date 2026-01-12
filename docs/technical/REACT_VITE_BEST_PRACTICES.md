# React + Vite + TypeScript Best Practices

> **Last Updated**: January 2026
> **Source**: [Vite Guide](https://vite.dev/guide/), [React Docs](https://react.dev/)
> **Project Reference**: `/web/src/`

---

## Table of Contents

1. [Why Vite in 2026](#why-vite-in-2026)
2. [Project Structure](#project-structure)
3. [Naming Conventions](#naming-conventions)
4. [TypeScript Configuration](#typescript-configuration)
5. [Component Patterns](#component-patterns)
6. [State Management](#state-management)
7. [Routing](#routing-react-router-v6)
8. [Performance Optimization](#performance-optimization)
9. [Error Handling](#error-handling)
10. [Keyboard Accessibility](#keyboard-accessibility)
11. [Responsive Design](#responsive-design)
12. [Testing with Vitest](#testing-with-vitest)
13. [Vite Configuration](#vite-configuration)
14. [TailwindCSS Integration](#tailwindcss-integration)
15. [Common Pitfalls](#common-pitfalls)

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
├── main.tsx              # Entry point with providers
├── App.tsx               # Root component with routes
├── index.css             # Global styles
├── vite-env.d.ts         # Vite type declarations
├── api/                  # API client and configuration
│   ├── client.ts         # Fetch wrapper with auth
│   └── index.ts
├── components/           # Reusable UI components
│   ├── ErrorBoundary.tsx # Error boundary wrapper
│   ├── Layout.tsx        # Page layout with sidebar
│   ├── RunCard.tsx       # Combat run display
│   ├── StatCard.tsx      # Statistic display
│   └── index.ts          # Barrel export
├── hooks/                # Custom React hooks
│   ├── useApi.ts         # React Query hooks
│   └── index.ts
├── pages/                # Route components
│   ├── Dashboard.tsx
│   ├── Analytics.tsx
│   └── index.ts
├── types/                # TypeScript types
│   └── index.ts
├── data/                 # Mock data (dev only)
│   └── mockData.ts
└── utils/                # Helper functions
    └── classColors.ts
```

**Key Principles:**
- Components are functional with TypeScript interfaces
- Hooks encapsulate data fetching and business logic
- Types are centralized and reusable
- Pages are route-level components

---

## Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Files | PascalCase for components | `RunCard.tsx` |
| Components | PascalCase | `RunCard` |
| Functions | camelCase | `calculateDps` |
| Constants | SCREAMING_SNAKE | `MAX_DPS_THRESHOLD` |
| Types/Interfaces | PascalCase | `CombatRun` |
| Hooks | camelCase with `use` prefix | `useRuns` |
| Query Keys | camelCase arrays | `['runs', id]` |

---

## TypeScript Configuration

Our project uses strict mode for maximum type safety:

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
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",

    /* Strict Mode - All enabled */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true,

    /* Path aliases */
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"]
}
```

### Strict Mode Benefits

| Flag | What It Catches |
|------|-----------------|
| `strict` | Enables all strict type checking options |
| `noUnusedLocals` | Dead code in variable declarations |
| `noUnusedParameters` | Unused function parameters |
| `noFallthroughCasesInSwitch` | Missing `break` in switch cases |
| `noUncheckedSideEffectImports` | Imports that may have side effects |

### Type Patterns

```tsx
// Prefer interfaces for object shapes
interface CombatRunListItem {
  run_id: string;
  character_name: string;
  content_name: string;
  content_type: ContentType;
  difficulty: Difficulty;
  timestamp: string;
  duration_sec: number;
  success: boolean;
  dps: number;
}

// Use type for unions and primitives
type ContentType = 'dungeon' | 'trial' | 'arena' | 'overworld' | 'pvp';
type Difficulty = 'normal' | 'veteran' | 'hardmode';
type PVETier = 'S' | 'A' | 'B' | 'C' | 'F';

// Generic types for API responses
interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
```

---

## Component Patterns

### Functional Components with TypeScript

All components should be functional with explicit prop interfaces:

```tsx
// components/RunCard.tsx
import type { KeyboardEvent } from 'react';

interface RunCardProps {
  run: CombatRunListItem;
  onClick?: () => void;
}

export default function RunCard({ run, onClick }: RunCardProps) {
  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick?.();
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`${run.content_name} run`}
      onClick={onClick}
      onKeyDown={handleKeyDown}
    >
      {/* content */}
    </div>
  );
}
```

### Component Organization

```tsx
// 1. Imports - external, then internal, then types
import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import clsx from 'clsx';
import StatCard from '../components/StatCard';
import type { CombatRun } from '../types';

// 2. Constants outside component
const DIFFICULTY_COLORS = {
  normal: 'badge-info',
  veteran: 'badge-warning',
  hardmode: 'badge-danger',
} as const;

// 3. Component function
export default function Dashboard() {
  // 4. Hooks first
  const { data, isLoading } = useRuns();

  // 5. Memoized values
  const stats = useMemo(() => calculateStats(data), [data]);

  // 6. Event handlers
  const handleSelect = (id: string) => { /* ... */ };

  // 7. Early returns for loading/error
  if (isLoading) return <LoadingSpinner />;

  // 8. Main render
  return (/* JSX */);
}
```

### Prop Patterns

```tsx
// Optional props with defaults
interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: LucideIcon;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  className?: string;
}

export default function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  className,
}: StatCardProps) {
  return (
    <div className={clsx('card', className)}>
      {/* Conditional rendering */}
      {subtitle && <p className="text-sm">{subtitle}</p>}
      {Icon && <Icon className="w-6 h-6" />}
      {trend && (
        <span className={trend.isPositive ? 'text-green-400' : 'text-red-400'}>
          {trend.isPositive ? '+' : ''}{trend.value}%
        </span>
      )}
    </div>
  );
}
```

### Children and Composition

```tsx
interface CardProps {
  children: ReactNode;
  className?: string;
}

function Card({ children, className }: CardProps) {
  return (
    <div className={clsx('card', className)}>
      {children}
    </div>
  );
}

// Usage with composition
<Card>
  <Card.Header>Title</Card.Header>
  <Card.Body>Content</Card.Body>
</Card>
```

---

## State Management

### React Query for Server State

Use React Query for all API data. It provides caching, automatic refetching, and loading/error states:

```tsx
// main.tsx - Provider setup
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>
);
```

### Query Keys Pattern

```tsx
// hooks/useApi.ts
export const queryKeys = {
  runs: ['runs'] as const,
  run: (id: string) => ['runs', id] as const,
  runStats: ['runs', 'stats'] as const,
  recommendations: (runId: string) => ['recommendations', runId] as const,
  percentiles: (runId: string) => ['percentiles', runId] as const,
  features: ['features'] as const,
  feature: (id: string) => ['features', id] as const,
  gearSets: ['gearSets'] as const,
  health: ['health'] as const,
};
```

### Custom Query Hooks

```tsx
// useRuns hook with parameters
export function useRuns(params?: Parameters<typeof api.runs.list>[0]) {
  return useQuery({
    queryKey: [...queryKeys.runs, params],
    queryFn: () => api.runs.list(params),
  });
}

// Dependent query (only runs when runId is truthy)
export function useRun(runId: string) {
  return useQuery({
    queryKey: queryKeys.run(runId),
    queryFn: () => api.runs.get(runId),
    enabled: !!runId,
  });
}

// With staleTime override
export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: () => api.health(),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}
```

### Mutations with Cache Invalidation

```tsx
export function useCreateRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: unknown) => api.runs.create(data),
    onSuccess: () => {
      // Invalidate related queries to trigger refetch
      queryClient.invalidateQueries({ queryKey: queryKeys.runs });
      queryClient.invalidateQueries({ queryKey: queryKeys.runStats });
    },
  });
}

export function useDeleteRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (runId: string) => api.runs.delete(runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.runs });
      queryClient.invalidateQueries({ queryKey: queryKeys.runStats });
    },
  });
}
```

### Context for UI State

Use Context for app-wide UI state that doesn't come from the server:

```tsx
// contexts/ThemeContext.tsx
import { createContext, useContext, useState, ReactNode } from 'react';

interface ThemeContextValue {
  theme: 'dark' | 'light';
  setTheme: (theme: 'dark' | 'light') => void;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
```

### State Selection Guide

| State Type | Solution | Example |
|------------|----------|---------|
| Server data | React Query | API responses, user data |
| UI state (global) | Context | Theme, sidebar open/closed |
| UI state (local) | useState | Form inputs, modal visibility |
| Complex local | useReducer | Multi-step forms |
| URL state | React Router | Filters, pagination |

---

## Routing (React Router v6+)

```tsx
// App.tsx
import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import ErrorBoundary from './components/ErrorBoundary';
import Dashboard from './pages/Dashboard';
import Builds from './pages/Builds';
import Analytics from './pages/Analytics';

function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="builds" element={<Builds />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="characters" element={<Characters />} />
          <Route path="recommendations" element={<Recommendations />} />
        </Route>
      </Routes>
    </ErrorBoundary>
  );
}
```

### Navigation with NavLink

```tsx
// components/Sidebar.tsx
import { NavLink } from 'react-router-dom';
import clsx from 'clsx';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Build Comparison', href: '/builds', icon: GitCompare },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
];

export default function Sidebar() {
  return (
    <nav className="flex-1 p-4 space-y-1">
      {navigation.map((item) => (
        <NavLink
          key={item.name}
          to={item.href}
          className={({ isActive }) =>
            clsx(
              'flex items-center gap-3 px-4 py-3 rounded-lg',
              isActive
                ? 'bg-eso-gold-500/10 text-eso-gold-400'
                : 'text-gray-400 hover:text-gray-100'
            )
          }
        >
          <item.icon className="w-5 h-5" />
          {item.name}
        </NavLink>
      ))}
    </nav>
  );
}
```

---

## Performance Optimization

### Code Splitting with React.lazy and Suspense

```tsx
import { lazy, Suspense } from 'react';

// Lazy load heavy components
const Analytics = lazy(() => import('./pages/Analytics'));
const Builds = lazy(() => import('./pages/Builds'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        <Route path="analytics" element={<Analytics />} />
        <Route path="builds" element={<Builds />} />
      </Routes>
    </Suspense>
  );
}

// Loading component
function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-eso-gold-400" />
    </div>
  );
}
```

### useMemo for Expensive Calculations

```tsx
// pages/Dashboard.tsx
export default function Dashboard() {
  // Memoize data transformations
  const dpsTrendData = useMemo(
    () => mockDPSTrend.map((point) => ({
      ...point,
      date: new Date(point.date).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
      }),
    })),
    [] // Empty deps = only compute once
  );

  const percentileTrendData = useMemo(
    () => mockPercentileTrend.map((point) => ({
      ...point,
      date: new Date(point.date).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
      }),
    })),
    []
  );

  return (/* JSX using memoized data */);
}
```

### useCallback for Stable References

```tsx
import { useCallback, memo } from 'react';

// Memoize callback to prevent child re-renders
function ParentComponent({ runs }: { runs: CombatRun[] }) {
  const handleSelect = useCallback((id: string) => {
    console.log('Selected:', id);
  }, []); // Stable reference

  return <RunList runs={runs} onSelect={handleSelect} />;
}

// Memoize child component
const RunList = memo(function RunList({
  runs,
  onSelect
}: {
  runs: CombatRun[];
  onSelect: (id: string) => void;
}) {
  return runs.map(run => (
    <RunCard key={run.id} run={run} onSelect={() => onSelect(run.id)} />
  ));
});
```

### When to Memoize

| Situation | Memoize? | Why |
|-----------|----------|-----|
| Expensive calculation | Yes | Avoid repeated work |
| Mapping large arrays | Yes | Transform once |
| Callbacks to memoized children | Yes | Preserve referential equality |
| Simple JSX | No | React is already fast |
| Small lists | No | Overhead outweighs benefit |

**Rule of thumb**: Profile first, optimize second. Use React DevTools Profiler to identify actual performance issues.

### Build Optimization (vite.config.ts)

```ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          charts: ['recharts'],
          query: ['@tanstack/react-query'],
        },
      },
    },
  },
});
```

---

## Error Handling

### Error Boundary Component

Error boundaries catch JavaScript errors in the component tree and display a fallback UI:

```tsx
// components/ErrorBoundary.tsx
import { Component, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    // TODO: Send error to logging service in production
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  handleGoHome = (): void => {
    this.setState({ hasError: false, error: null });
    window.location.href = '/';
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen flex items-center justify-center p-4">
          <div className="card max-w-md w-full text-center">
            <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-4" />
            <h1 className="text-xl font-bold mb-2">Something went wrong</h1>
            <p className="text-gray-400 mb-6">
              An unexpected error occurred.
            </p>

            {/* Show error in development */}
            {import.meta.env.DEV && this.state.error && (
              <pre className="mb-6 p-4 bg-gray-800 rounded text-left text-sm overflow-auto">
                {this.state.error.message}
              </pre>
            )}

            <div className="flex gap-3 justify-center">
              <button onClick={this.handleReset} className="btn-secondary">
                <RefreshCw className="w-4 h-4" />
                Try Again
              </button>
              <button onClick={this.handleGoHome} className="btn-primary">
                <Home className="w-4 h-4" />
                Go Home
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
```

### Error Boundary Limitations

Error boundaries do NOT catch errors in:
- Event handlers (use try/catch)
- Asynchronous code (setTimeout, fetch, etc.)
- Server-side rendering
- Errors thrown in the error boundary itself

### API Error Handling

```tsx
// api/client.ts
class APIError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data: unknown
  ) {
    super(`API Error: ${status} ${statusText}`);
    this.name = 'APIError';
  }
}

// Handle errors in components
function RunDetail({ runId }: { runId: string }) {
  const { data, error, isLoading } = useRun(runId);

  if (isLoading) return <LoadingSpinner />;

  if (error) {
    return (
      <div className="text-red-400">
        Failed to load run: {error.message}
      </div>
    );
  }

  return (/* render data */);
}
```

---

## Keyboard Accessibility

### Interactive Elements

All interactive elements must be keyboard accessible:

```tsx
// components/RunCard.tsx
import type { KeyboardEvent } from 'react';

interface RunCardProps {
  run: CombatRunListItem;
  onClick?: () => void;
}

export default function RunCard({ run, onClick }: RunCardProps) {
  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    // Handle Enter and Space for activation
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick?.();
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`${run.content_name} run by ${run.character_name}, ${
        run.success ? 'successful' : 'failed'
      }, ${formatDPS(run.dps)} DPS`}
      className="card-hover cursor-pointer"
      onClick={onClick}
      onKeyDown={handleKeyDown}
    >
      {/* content */}
    </div>
  );
}
```

### ARIA Attributes

| Attribute | Usage |
|-----------|-------|
| `role="button"` | Non-button elements that act as buttons |
| `tabIndex={0}` | Make element focusable in tab order |
| `aria-label` | Accessible name for screen readers |
| `aria-expanded` | Expandable sections (accordions, dropdowns) |
| `aria-hidden="true"` | Decorative icons (already labeled elements) |
| `aria-live="polite"` | Dynamic content updates |

### Focus Management

```tsx
// Modal with focus trap
function Modal({ isOpen, onClose, children }: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      // Focus first focusable element
      modalRef.current?.focus();
    }
  }, [isOpen]);

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div
      ref={modalRef}
      role="dialog"
      aria-modal="true"
      tabIndex={-1}
      onKeyDown={handleKeyDown}
    >
      {children}
    </div>
  );
}
```

### Accessibility Checklist

- [ ] All interactive elements are keyboard focusable
- [ ] Focus order follows visual order
- [ ] Focus is visible (use focus-visible styles)
- [ ] ARIA labels on icon-only buttons
- [ ] Color is not the only indicator (icons, text, patterns)
- [ ] Sufficient color contrast (WCAG AA: 4.5:1 for text)

---

## Responsive Design

### Mobile-First with Tailwind

Our layout adapts to different screen sizes using Tailwind breakpoints:

```tsx
// components/Layout.tsx
export default function Layout() {
  return (
    <div className="flex min-h-screen bg-eso-dark-950">
      <Sidebar />
      {/* No margin on mobile, sidebar margin on medium+ screens */}
      <main className="flex-1 ml-0 md:ml-64">
        <div className="p-4 md:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
```

### Breakpoint Reference

| Breakpoint | Min Width | Example |
|------------|-----------|---------|
| (default) | 0px | `p-4` (applies to all) |
| `sm:` | 640px | `sm:p-6` |
| `md:` | 768px | `md:ml-64` |
| `lg:` | 1024px | `lg:grid-cols-2` |
| `xl:` | 1280px | `xl:grid-cols-4` |
| `2xl:` | 1536px | `2xl:max-w-7xl` |

### Responsive Grid Patterns

```tsx
// Responsive stats grid
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
  <StatCard title="Total Runs" value={stats.total_runs} />
  <StatCard title="Average DPS" value={formatDPS(stats.average_dps)} />
  <StatCard title="Best DPS" value={formatDPS(stats.best_dps)} />
  <StatCard title="Play Time" value={`${hours}h`} />
</div>

// Responsive two-column layout
<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
  <DPSTrendChart />
  <PercentileChart />
</div>
```

### Responsive Sidebar

```tsx
// Mobile: hidden or overlay
// Desktop: fixed sidebar
function Sidebar() {
  return (
    <aside className={clsx(
      // Base: hidden on mobile
      'fixed left-0 top-0 h-screen w-64',
      'bg-eso-dark-900 border-r border-eso-dark-700',
      'flex flex-col',
      // Mobile: hidden (can add toggle button)
      'hidden md:flex'
    )}>
      {/* sidebar content */}
    </aside>
  );
}
```

### Container and Width Patterns

```tsx
// Centered content with max-width
<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
  {/* content */}
</div>

// Full-width card that respects padding
<div className="w-full card">
  {/* content */}
</div>
```

---

## Testing with Vitest

### Configuration

```ts
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    coverage: {
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules/', 'src/test/'],
    },
  },
});
```

### Test Setup

```ts
// src/test/setup.ts
import '@testing-library/jest-dom';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// Cleanup after each test
afterEach(() => {
  cleanup();
});
```

### Component Testing

```tsx
// components/RunCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import RunCard from './RunCard';

describe('RunCard', () => {
  const mockRun = {
    run_id: '1',
    character_name: 'TestChar',
    content_name: 'Veteran Lair of Maarselok',
    content_type: 'dungeon' as const,
    difficulty: 'veteran' as const,
    timestamp: '2026-01-10T12:00:00Z',
    duration_sec: 1200,
    success: true,
    dps: 50000,
  };

  it('renders run information correctly', () => {
    render(<RunCard run={mockRun} />);

    expect(screen.getByText('Veteran Lair of Maarselok')).toBeInTheDocument();
    expect(screen.getByText('TestChar')).toBeInTheDocument();
    expect(screen.getByText('Success')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const onClick = vi.fn();
    render(<RunCard run={mockRun} onClick={onClick} />);

    fireEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('responds to keyboard Enter', () => {
    const onClick = vi.fn();
    render(<RunCard run={mockRun} onClick={onClick} />);

    const card = screen.getByRole('button');
    fireEvent.keyDown(card, { key: 'Enter' });

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('responds to keyboard Space', () => {
    const onClick = vi.fn();
    render(<RunCard run={mockRun} onClick={onClick} />);

    const card = screen.getByRole('button');
    fireEvent.keyDown(card, { key: ' ' });

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('shows failed state correctly', () => {
    const failedRun = { ...mockRun, success: false };
    render(<RunCard run={failedRun} />);

    expect(screen.getByText('Failed')).toBeInTheDocument();
  });
});
```

### Testing Hooks with React Query

```tsx
// hooks/useApi.test.tsx
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi } from 'vitest';
import { useRuns } from './useApi';

// Create wrapper with QueryClientProvider
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

describe('useRuns', () => {
  it('returns loading state initially', () => {
    const { result } = renderHook(() => useRuns(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
  });

  it('returns data after fetch', async () => {
    const { result } = renderHook(() => useRuns(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toBeDefined();
  });
});
```

### Test Commands

```bash
# Run tests once
npm run test

# Watch mode for development
npm run test:watch

# Generate coverage report
npm run test:coverage
```

### Testing Best Practices

1. **Test behavior, not implementation** - Focus on what users see and do
2. **Use Testing Library queries** - Prefer `getByRole`, `getByLabelText` over `getByTestId`
3. **Avoid testing internals** - Don't test state directly, test visible outcomes
4. **Mock API calls** - Use MSW or vi.mock for network requests
5. **Write accessible tests** - If you can't query by role/label, your UI may have accessibility issues

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
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          charts: ['recharts'],
          query: ['@tanstack/react-query'],
        },
      },
    },
  },
});
```

### Environment Variables

```bash
# .env.local (not committed)
VITE_API_URL=http://localhost:8000/api/v1

# Usage in code
const apiUrl = import.meta.env.VITE_API_URL;
const isDev = import.meta.env.DEV;
const isProd = import.meta.env.PROD;
```

---

## TailwindCSS Integration

```js
// tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // ESO-inspired dark theme colors
        'eso-dark': {
          50: '#f7f7f8',
          100: '#eeeef0',
          200: '#d9d9de',
          300: '#b8b8c1',
          400: '#91919f',
          500: '#737383',
          600: '#5d5d6b',
          700: '#4c4c58',
          800: '#41414b',
          900: '#393941',
          950: '#18181b',
        },
        'eso-gold': {
          400: '#facc15',
          500: '#d4a012',
          600: '#a16207',
        },
        'eso-red': {
          400: '#f87171',
          500: '#ef4444',
        },
        'eso-green': {
          400: '#4ade80',
          500: '#22c55e',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
```

### Using clsx for Conditional Classes

```tsx
import clsx from 'clsx';

function Badge({ variant, children }: BadgeProps) {
  return (
    <span
      className={clsx(
        'px-2 py-1 rounded text-xs font-medium',
        variant === 'success' && 'bg-green-500/10 text-green-400',
        variant === 'error' && 'bg-red-500/10 text-red-400',
        variant === 'warning' && 'bg-yellow-500/10 text-yellow-400'
      )}
    >
      {children}
    </span>
  );
}
```

---

## Common Pitfalls

### 1. Mutating State Directly

```tsx
// BAD
const [items, setItems] = useState([1, 2, 3]);
items.push(4); // Mutation!
setItems(items); // Won't trigger re-render

// GOOD
setItems([...items, 4]); // New array
```

### 2. Using useEffect for Derived State

```tsx
// BAD
const [items, setItems] = useState([]);
const [count, setCount] = useState(0);

useEffect(() => {
  setCount(items.length);
}, [items]);

// GOOD
const count = items.length; // Just calculate it
// OR
const count = useMemo(() => items.length, [items]);
```

### 3. Missing Dependencies in Hooks

```tsx
// BAD - stale closure
useEffect(() => {
  fetchData(userId);
}, []); // userId missing from deps

// GOOD
useEffect(() => {
  fetchData(userId);
}, [userId]);
```

### 4. Over-Memoizing

```tsx
// BAD - unnecessary overhead
const name = useMemo(() => user.firstName, [user.firstName]);

// GOOD - just use it
const name = user.firstName;
```

### 5. Not Handling Loading/Error States

```tsx
// BAD
function Component() {
  const { data } = useRuns();
  return <List items={data} />; // Crashes if data is undefined
}

// GOOD
function Component() {
  const { data, isLoading, error } = useRuns();

  if (isLoading) return <Spinner />;
  if (error) return <Error message={error.message} />;
  if (!data) return <Empty />;

  return <List items={data} />;
}
```

### 6. Using `any` Type

```tsx
// BAD
function processData(data: any) { ... }

// GOOD
interface RunData {
  id: string;
  dps: number;
}
function processData(data: RunData) { ... }
```

### 7. Inline Object/Array Props

```tsx
// BAD - creates new reference every render
<Component style={{ color: 'red' }} items={[1, 2, 3]} />

// GOOD - stable references
const style = useMemo(() => ({ color: 'red' }), []);
const items = useMemo(() => [1, 2, 3], []);
<Component style={style} items={items} />

// OR define outside component if static
const STYLE = { color: 'red' };
const ITEMS = [1, 2, 3];
```

---

## Quick Reference

### Package Versions (Current)

```json
{
  "react": "^18.3.1",
  "react-dom": "^18.3.1",
  "react-router-dom": "^7.1.1",
  "@tanstack/react-query": "^5.62.0",
  "vite": "^6.0.5",
  "typescript": "~5.6.2",
  "vitest": "^2.1.0",
  "@testing-library/react": "^16.0.0"
}
```

### Essential Imports

```tsx
// React
import { useState, useEffect, useMemo, useCallback, memo } from 'react';
import type { ReactNode, KeyboardEvent } from 'react';

// React Router
import { Routes, Route, NavLink, Outlet, useParams } from 'react-router-dom';

// React Query
import { useQuery, useMutation, useQueryClient, QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Testing
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
```

---

*This document should be refreshed when React, Vite, or major dependencies release new versions.*
