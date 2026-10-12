import { writable } from 'svelte/store';
import type { PlaylistItem } from '$lib/api/types';
import { api } from '$lib/api/client';
import { getActivePlaylistId, setActivePlaylistId } from '$lib/utils/preferences';

export interface PlaylistState {
  activePlaylistId: string;
  playlists: PlaylistItem[];
  loading: boolean;
  isLoaded: boolean;
}

const defaultState: PlaylistState = {
  activePlaylistId: 'default',
  playlists: [
    {
      id: 'default',
      name: 'My List',
      export_token: '',
      is_default: true
    }
  ],
  loading: false,
  isLoaded: false
};

function createPlaylistStore() {
  const { subscribe, set, update } = writable<PlaylistState>(defaultState);

  return {
    subscribe,
    initFromPreferences: () => {
      const storedId = getActivePlaylistId();
      update((state) => ({ ...state, activePlaylistId: storedId }));
    },
    setActivePlaylist: (playlistId: string) => {
      setActivePlaylistId(playlistId);
      update((state) => ({ ...state, activePlaylistId: playlistId }));
    },
    loadPlaylists: async () => {
      update((state) => ({ ...state, loading: true }));
      try {
        const list = await api.getPlaylists();
        const storedId = getActivePlaylistId();
        const validId = list.some((p) => p.id === storedId) ? storedId : (list[0]?.id || 'default');
        setActivePlaylistId(validId);
        update((state) => ({
          ...state,
          playlists: list.length > 0 ? list : defaultState.playlists,
          activePlaylistId: validId,
          loading: false,
          isLoaded: true
        }));
      } catch {
        update((state) => ({ ...state, loading: false, isLoaded: true }));
      }
    },
    setPlaylists: (playlists: PlaylistItem[]) => {
      update((state) => {
        const storedId = state.activePlaylistId;
        const validId = playlists.some((p) => p.id === storedId) ? storedId : (playlists[0]?.id || 'default');
        setActivePlaylistId(validId);
        return {
          ...state,
          playlists,
          activePlaylistId: validId,
          isLoaded: true
        };
      });
    },
    addPlaylist: (item: PlaylistItem) => {
      update((state) => ({
        ...state,
        playlists: [...state.playlists.filter((p) => p.id !== item.id), item]
      }));
    },
    removePlaylist: (playlistId: string) => {
      update((state) => {
        const filtered = state.playlists.filter((p) => p.id !== playlistId);
        const nextActive = state.activePlaylistId === playlistId ? (filtered[0]?.id || 'default') : state.activePlaylistId;
        setActivePlaylistId(nextActive);
        return {
          ...state,
          playlists: filtered,
          activePlaylistId: nextActive
        };
      });
    },
    reset: () => {
      set({
        ...defaultState,
        activePlaylistId: getActivePlaylistId()
      });
    }
  };
}

export const playlistStore = createPlaylistStore();
