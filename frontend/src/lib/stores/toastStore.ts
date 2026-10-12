import { writable } from 'svelte/store';

export interface ToastNotification {
  id: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  timeoutMs?: number;
}

export function calculateToastTimeout(message: string): number {
  const wordCount = message.trim().split(/\s+/).filter(Boolean).length;
  return Math.min(8000, Math.max(3500, 3000 + wordCount * 200));
}

function createToastStore() {
  const { subscribe, update } = writable<ToastNotification[]>([]);

  function addToast(message: string, type: ToastNotification['type'] = 'info', timeoutMs?: number) {
    const resolvedTimeout = timeoutMs !== undefined ? timeoutMs : calculateToastTimeout(message);
    const id = Math.random().toString(36).substring(2, 9);
    const toast: ToastNotification = { id, message, type, timeoutMs: resolvedTimeout };

    update((items) => [...items, toast]);

    if (resolvedTimeout > 0) {
      setTimeout(() => {
        removeToast(id);
      }, resolvedTimeout);
    }
  }

  function removeToast(id: string) {
    update((items) => items.filter((item) => item.id !== id));
  }

  return {
    subscribe,
    add: addToast,
    remove: removeToast,
    info: (msg: string, timeout?: number) => addToast(msg, 'info', timeout),
    success: (msg: string, timeout?: number) => addToast(msg, 'success', timeout),
    warning: (msg: string, timeout?: number) => addToast(msg, 'warning', timeout),
    error: (msg: string, timeout?: number) => addToast(msg, 'error', timeout)
  };
}

export const toastStore = createToastStore();
