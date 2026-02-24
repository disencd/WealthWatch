import { token, logout } from '$lib/stores/auth';
import { get } from 'svelte/store';

const API_BASE = '/api/v1';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function api<T = unknown>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const headers: Record<string, string> = {};
  const t = get(token);
  if (t) headers['Authorization'] = `Bearer ${t}`;

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(url, {
    ...options,
    headers: { ...headers, ...(options.headers as Record<string, string>) }
  });

  if (res.status === 204) return null as T;

  const data = await res.json();
  if (!res.ok) {
    if (res.status === 401) logout();
    throw new ApiError(data.detail || data.error || 'Request failed', res.status);
  }
  return data as T;
}
