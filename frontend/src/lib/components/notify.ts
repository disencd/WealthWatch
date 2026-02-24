import { writable } from 'svelte/store';

interface Toast {
  id: number;
  message: string;
  type: 'info' | 'success' | 'error';
}

let nextId = 0;
export const toasts = writable<Toast[]>([]);

export function notify(message: string, type: 'info' | 'success' | 'error' = 'info') {
  const id = nextId++;
  toasts.update(t => [...t, { id, message, type }]);
  setTimeout(() => {
    toasts.update(t => t.filter(x => x.id !== id));
  }, 3000);
}
