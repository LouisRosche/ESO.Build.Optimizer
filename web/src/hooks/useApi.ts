/**
 * React Query hooks for ESO Build Optimizer API
 *
 * These hooks provide data fetching with caching, automatic refetching,
 * and loading/error states.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../api/client';

// Query keys for cache management
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

// Health check
export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: () => api.health(),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

// Combat Runs
export function useRuns(params?: Parameters<typeof api.runs.list>[0]) {
  return useQuery({
    queryKey: [...queryKeys.runs, params],
    queryFn: () => api.runs.list(params),
  });
}

export function useRun(runId: string) {
  return useQuery({
    queryKey: queryKeys.run(runId),
    queryFn: () => api.runs.get(runId),
    enabled: !!runId,
  });
}

export function useRunStatistics() {
  return useQuery({
    queryKey: queryKeys.runStats,
    queryFn: () => api.runs.statistics(),
  });
}

export function useCreateRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: unknown) => api.runs.create(data),
    onSuccess: () => {
      // Invalidate runs list to trigger refetch
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

// Recommendations
export function useRecommendations(runId: string, regenerate = false) {
  return useQuery({
    queryKey: [...queryKeys.recommendations(runId), { regenerate }],
    queryFn: () => api.recommendations.get(runId, regenerate),
    enabled: !!runId,
  });
}

export function usePercentiles(runId: string) {
  return useQuery({
    queryKey: queryKeys.percentiles(runId),
    queryFn: () => api.recommendations.percentiles(runId),
    enabled: !!runId,
  });
}

// Features
export function useFeatures(params?: Parameters<typeof api.features.list>[0]) {
  return useQuery({
    queryKey: [...queryKeys.features, params],
    queryFn: () => api.features.list(params),
  });
}

export function useGearSets(params?: Parameters<typeof api.features.sets>[0]) {
  return useQuery({
    queryKey: [...queryKeys.gearSets, params],
    queryFn: () => api.features.sets(params),
  });
}
