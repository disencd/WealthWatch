import { writable, get } from 'svelte/store';
import { browser } from '$app/environment';
import { goto } from '$app/navigation';

const STORAGE_KEY = 'wealthwatch_token';

function createTokenStore() {
  const initial = browser ? localStorage.getItem(STORAGE_KEY) || '' : '';
  const { subscribe, set } = writable(initial);
  return {
    subscribe,
    set(value: string) {
      if (browser) {
        if (value) localStorage.setItem(STORAGE_KEY, value);
        else localStorage.removeItem(STORAGE_KEY);
      }
      set(value);
    }
  };
}

export const token = createTokenStore();
export const currentUser = writable<Record<string, unknown> | null>(null);

export function logout() {
  token.set('');
  currentUser.set(null);
  if (browser) goto('/login');
}

export function isAuthenticated(): boolean {
  return !!get(token);
}
