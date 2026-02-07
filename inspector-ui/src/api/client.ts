/**
 * API Client
 *
 * Base HTTP client for API requests.
 */
import { useConfigStore } from '@/stores/config-store';

const API_BASE = import.meta.env.VITE_API_URL || '';

export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public code: string,
    public requestId?: string,
    public details?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

interface ErrorResponse {
  error: {
    message: string;
    code: string;
    requestId: string;
    details?: unknown;
  };
}

function getProjectId(): string {
  return useConfigStore.getState().projectId;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorData: ErrorResponse | null = null;
    try {
      errorData = await response.json();
    } catch {
      // Response might not be JSON
    }

    throw new ApiError(
      errorData?.error?.message || `HTTP ${response.status}: ${response.statusText}`,
      response.status,
      errorData?.error?.code || 'UNKNOWN_ERROR',
      errorData?.error?.requestId,
      errorData?.error?.details
    );
  }

  // Handle empty responses
  const contentType = response.headers.get('content-type');
  if (contentType?.includes('application/json')) {
    return response.json();
  }

  // For file downloads or non-JSON responses
  return response.text() as unknown as T;
}

export async function get<T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    });
  }

  const response = await fetch(url.toString(), {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
      'X-Project-Id': getProjectId()
    }
  });

  return handleResponse<T>(response);
}

export async function post<T>(path: string, data?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'X-Project-Id': getProjectId()
    },
    body: data ? JSON.stringify(data) : undefined
  });

  return handleResponse<T>(response);
}

export async function put<T>(path: string, data?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'X-Project-Id': getProjectId()
    },
    body: data ? JSON.stringify(data) : undefined
  });

  return handleResponse<T>(response);
}

export async function del<T>(path: string, params?: Record<string, string | boolean>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    });
  }

  const response = await fetch(url.toString(), {
    method: 'DELETE',
    headers: {
      'Accept': 'application/json',
      'X-Project-Id': getProjectId()
    }
  });

  return handleResponse<T>(response);
}
