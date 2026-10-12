import { writable, derived } from 'svelte/store';
import { api } from '$lib/api/client';
import type { BulletinDTO } from '$lib/api/types';

export interface BulletinState {
  bulletins: BulletinDTO[];
  loading: boolean;
  isLoaded: boolean;
  lastFetched: number | null;
}

const defaultState: BulletinState = {
  bulletins: [],
  loading: false,
  isLoaded: false,
  lastFetched: null
};

export function resolveLocalizedText(
  dict?: Record<string, string> | null,
  preferredLang = 'en'
): string {
  if (!dict || typeof dict !== 'object') return '';
  if (dict[preferredLang]) return dict[preferredLang];
  if (dict['en']) return dict['en'];
  const firstKey = Object.keys(dict)[0];
  return firstKey ? dict[firstKey] : '';
}

function createBulletinStore() {
  const { subscribe, set, update } = writable<BulletinState>(defaultState);

  return {
    subscribe,
    fetchBulletins: async (includeDismissed = false): Promise<BulletinDTO[]> => {
      update((s) => ({ ...s, loading: true }));
      try {
        const res = await api.getBulletins(includeDismissed);
        const list = res.bulletins || [];
        update((s) => ({
          ...s,
          bulletins: list,
          loading: false,
          isLoaded: true,
          lastFetched: Date.now()
        }));
        return list;
      } catch {
        update((s) => ({ ...s, loading: false, isLoaded: true }));
        return [];
      }
    },
    dismiss: async (id: string): Promise<boolean> => {
      try {
        await api.dismissBulletin(id);
        update((s) => ({
          ...s,
          bulletins: s.bulletins.map((b) =>
            b.id === id ? { ...b, is_dismissed: true, dismissed_at: new Date().toISOString() } : b
          )
        }));
        return true;
      } catch {
        return false;
      }
    },
    markRead: async (id: string): Promise<boolean> => {
      try {
        await api.markBulletinRead(id);
        update((s) => ({
          ...s,
          bulletins: s.bulletins.map((b) => (b.id === id ? { ...b, is_read: true } : b))
        }));
        return true;
      } catch {
        return false;
      }
    },
    deleteBulletin: async (id: string): Promise<boolean> => {
      try {
        await api.deleteBulletin(id);
        update((s) => ({
          ...s,
          bulletins: s.bulletins.filter((b) => b.id !== id)
        }));
        return true;
      } catch {
        return false;
      }
    },
    clearArchived: async (): Promise<boolean> => {
      try {
        await api.clearArchivedBulletins();
        update((s) => ({
          ...s,
          bulletins: s.bulletins.filter((b) => !b.is_dismissed)
        }));
        return true;
      } catch {
        return false;
      }
    },
    setBulletins: (bulletins: BulletinDTO[]) => {
      update((s) => ({ ...s, bulletins, isLoaded: true }));
    },
    reset: () => set(defaultState)
  };
}

export const bulletinStore = createBulletinStore();

export const activeBulletins = derived(bulletinStore, ($s) =>
  $s.bulletins.filter((b) => !b.is_dismissed)
);

export const archivedBulletins = derived(bulletinStore, ($s) =>
  $s.bulletins.filter((b) => b.is_dismissed)
);

export const criticalBulletins = derived(bulletinStore, ($s) =>
  $s.bulletins.filter((b) => !b.is_dismissed && (b.level === 'critical' || b.level === 'security' || !b.dismissible))
);

export const unreadBulletinCount = derived(bulletinStore, ($s) =>
  $s.bulletins.filter((b) => !b.is_dismissed && !b.is_read).length
);
