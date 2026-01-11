/**
 * API Client for ESO Build Optimizer
 *
 * This module provides a configured fetch wrapper for making API calls
 * to the FastAPI backend.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
}

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

async function request<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { params, ...fetchOptions } = options;

  // Build URL with query params
  let url = `${API_BASE_URL}${endpoint}`;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }

  // Get auth token from storage
  const token = localStorage.getItem('auth_token');

  // Only set Content-Type when body exists
  const headers: Record<string, string> = {
    ...(fetchOptions.body && { 'Content-Type': 'application/json' }),
    ...(token && { Authorization: `Bearer ${token}` }),
    ...(fetchOptions.headers as Record<string, string>),
  };

  const response = await fetch(url, {
    ...fetchOptions,
    headers,
  });

  // Handle JSON parsing safely - response.json() can throw on empty or invalid responses
  let data: unknown;
  try {
    const text = await response.text();
    data = text ? JSON.parse(text) : null;
  } catch (e) {
    if (!response.ok) {
      throw new APIError(response.status, response.statusText, null);
    }
    data = null;
  }

  if (!response.ok) {
    throw new APIError(response.status, response.statusText, data);
  }

  return data as T;
}

// API methods
export const api = {
  // Health check
  health: () => request<{ status: string; version: string }>('/health'),

  // Auth
  auth: {
    login: (email: string, password: string) =>
      request<{ access_token: string; token_type: string }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),
    register: (email: string, username: string, password: string) =>
      request('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, username, password }),
      }),
    me: () => request('/auth/me'),
  },

  // Combat Runs
  runs: {
    list: (params?: {
      content_type?: string;
      content_name?: string;
      difficulty?: string;
      character_name?: string;
      success?: boolean;
      limit?: number;
      offset?: number;
    }) => request('/runs', { params }),

    get: (runId: string) => request(`/runs/${runId}`),

    create: (data: unknown) =>
      request('/runs', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    delete: (runId: string) =>
      request(`/runs/${runId}`, { method: 'DELETE' }),

    statistics: () => request('/runs/stats/summary'),

    compare: (runIdA: string, runIdB: string) =>
      request(`/runs/compare/${runIdA}/${runIdB}`),
  },

  // Recommendations
  recommendations: {
    get: (runId: string, regenerate = false) =>
      request(`/runs/${runId}/recommendations`, {
        params: { regenerate },
      }),

    percentiles: (runId: string) =>
      request(`/runs/${runId}/percentiles`),
  },

  // Features (Skills, Sets)
  features: {
    list: (params?: {
      system?: string;
      category?: string;
      feature_type?: string;
      class_restriction?: string;
      search?: string;
      limit?: number;
      offset?: number;
    }) => request('/features', { params }),

    get: (featureId: string) => request(`/features/${featureId}`),

    sets: (params?: {
      set_type?: string;
      weight?: string;
      pve_tier?: string;
      search?: string;
      limit?: number;
      offset?: number;
    }) => request('/features/sets', { params }),
  },
};

export { APIError };
export default api;
