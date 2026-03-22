/**
 * React Query hooks for ESO Build Optimizer API
 *
 * These hooks provide data fetching with caching, automatic refetching,
 * and loading/error states. All hooks gracefully handle API failures
 * so pages can fall back to mock data when the backend is unreachable.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../api/client';
import type {
  CombatRunListItem,
  RunStatistics,
  Recommendation,
  RecommendationsResponse,
  Character,
  GearSet,
  DPSTrendPoint,
  PercentileDataPoint,
  BuffAnalysis,
  CombatRun,
} from '../types';

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
  characters: ['characters'] as const,
  character: (id: string) => ['characters', id] as const,
  dpsTrend: ['analytics', 'dps-trend'] as const,
  percentileTrend: ['analytics', 'percentile-trend'] as const,
  buffAnalysis: ['analytics', 'buff-analysis'] as const,
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
  return useQuery<CombatRunListItem[]>({
    queryKey: [...queryKeys.runs, params],
    queryFn: () => api.runs.list(params) as Promise<CombatRunListItem[]>,
    retry: 1,
    staleTime: 1000 * 60 * 2, // 2 minutes
  });
}

export function useRun(runId: string) {
  return useQuery<CombatRun>({
    queryKey: queryKeys.run(runId),
    queryFn: () => api.runs.get(runId) as Promise<CombatRun>,
    enabled: !!runId,
    retry: 1,
  });
}

export function useRunStatistics() {
  return useQuery<RunStatistics>({
    queryKey: queryKeys.runStats,
    queryFn: () => api.runs.statistics() as Promise<RunStatistics>,
    retry: 1,
    staleTime: 1000 * 60 * 2,
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
  return useQuery<RecommendationsResponse>({
    queryKey: [...queryKeys.recommendations(runId), { regenerate }],
    queryFn: () => api.recommendations.get(runId, regenerate) as Promise<RecommendationsResponse>,
    enabled: !!runId,
    retry: 1,
  });
}

export function usePercentiles(runId: string) {
  return useQuery({
    queryKey: queryKeys.percentiles(runId),
    queryFn: () => api.recommendations.percentiles(runId),
    enabled: !!runId,
    retry: 1,
  });
}

// Features
export function useFeatures(params?: Parameters<typeof api.features.list>[0]) {
  return useQuery({
    queryKey: [...queryKeys.features, params],
    queryFn: () => api.features.list(params),
    retry: 1,
  });
}

export function useGearSets(params?: Parameters<typeof api.features.sets>[0]) {
  return useQuery<GearSet[]>({
    queryKey: [...queryKeys.gearSets, params],
    queryFn: () => api.features.sets(params) as Promise<GearSet[]>,
    retry: 1,
    staleTime: 1000 * 60 * 5,
  });
}

// Characters
export function useCharacters() {
  return useQuery<Character[]>({
    queryKey: queryKeys.characters,
    queryFn: () => api.characters.list() as Promise<Character[]>,
    retry: 1,
    staleTime: 1000 * 60 * 2,
  });
}

export function useCharacter(characterId: string) {
  return useQuery<Character>({
    queryKey: queryKeys.character(characterId),
    queryFn: () => api.characters.get(characterId) as Promise<Character>,
    enabled: !!characterId,
    retry: 1,
  });
}

// Analytics
export function useDPSTrend(params?: { time_range?: string; character_name?: string }) {
  return useQuery<DPSTrendPoint[]>({
    queryKey: [...queryKeys.dpsTrend, params],
    queryFn: () => api.analytics.dpsTrend(params) as Promise<DPSTrendPoint[]>,
    retry: 1,
    staleTime: 1000 * 60 * 5,
  });
}

export function usePercentileTrend(params?: { time_range?: string; character_name?: string }) {
  return useQuery<PercentileDataPoint[]>({
    queryKey: [...queryKeys.percentileTrend, params],
    queryFn: () => api.analytics.percentileTrend(params) as Promise<PercentileDataPoint[]>,
    retry: 1,
    staleTime: 1000 * 60 * 5,
  });
}

export function useBuffAnalysis(params?: { time_range?: string; character_name?: string }) {
  return useQuery<BuffAnalysis[]>({
    queryKey: [...queryKeys.buffAnalysis, params],
    queryFn: () => api.analytics.buffAnalysis(params) as Promise<BuffAnalysis[]>,
    retry: 1,
    staleTime: 1000 * 60 * 5,
  });
}
