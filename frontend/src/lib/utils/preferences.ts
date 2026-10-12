const AUTH_TOKEN_KEY = 'jwt_token';

/**
 * Safely retrieves the stored JWT authentication token.
 *
 * @returns Token string or null if not authenticated.
 */
export function getAuthToken(): string | null {
  if (typeof window === 'undefined' || !window.localStorage) {
    return null;
  }
  try {
    return window.localStorage.getItem(AUTH_TOKEN_KEY);
  } catch {
    return null;
  }
}

/**
 * Safely persists the JWT authentication token.
 *
 * @param token JWT token string.
 */
export function setAuthToken(token: string): void {
  if (typeof window === 'undefined' || !window.localStorage) {
    return;
  }
  try {
    window.localStorage.setItem(AUTH_TOKEN_KEY, token);
  } catch {
    // Ignore storage quota errors
  }
}

/**
 * Safely clears the stored JWT authentication token.
 */
export function clearAuthToken(): void {
  if (typeof window === 'undefined' || !window.localStorage) {
    return;
  }
  try {
    window.localStorage.removeItem(AUTH_TOKEN_KEY);
  } catch {
    // Ignore storage access errors
  }
}

/**
 * Checks whether an authentication token is currently present.
 *
 * @returns True if token exists.
 */
export function hasAuthToken(): boolean {
  return Boolean(getAuthToken());
}

/**
 * Safely retrieves a typed preference from browser localStorage with fallback.
 *
 * @param key LocalStorage key string.
 * @param fallback Default value if key is not found or invalid.
 * @returns Parsed value or fallback.
 */
export function getPreference<T>(key: string, fallback: T): T {
  if (typeof window === 'undefined' || !window.localStorage) {
    return fallback;
  }

  try {
    const raw = window.localStorage.getItem(key);
    if (raw === null || raw === undefined) {
      return fallback;
    }
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

/**
 * Safely persists a typed preference value into browser localStorage.
 *
 * @param key LocalStorage key string.
 * @param value Value to serialize and store.
 */
export function setPreference<T>(key: string, value: T): void {
  if (typeof window === 'undefined' || !window.localStorage) {
    return;
  }

  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Ignore storage quota errors
  }
}




/**
 * Checks if a delete confirmation dialog should be displayed for a given scope.
 *
 * @param scope Confirmation domain key.
 * @returns True if confirmation is required (default true), false if suppressed by user.
 */
export function shouldConfirmDelete(scope: string): boolean {
  return getPreference<boolean>(`confirm_delete_${scope}`, true);
}

/**
 * Sets whether delete confirmation is required for a given scope.
 *
 * @param scope Confirmation domain key.
 * @param confirmRequired True to require confirmation, false to suppress.
 */
export function setDeleteConfirmationPreference(scope: string, confirmRequired: boolean): void {
  setPreference(`confirm_delete_${scope}`, confirmRequired);
}

/**
 * Resets all stored delete confirmation preferences across all scopes.
 */
export function resetDeleteConfirmations(): void {
  if (typeof window === 'undefined' || !window.localStorage) {
    return;
  }

  try {
    const keysToRemove: string[] = [];
    for (let i = 0; i < window.localStorage.length; i++) {
      const key = window.localStorage.key(i);
      if (key && key.startsWith('confirm_delete_')) {
        keysToRemove.push(key);
      }
    }
    keysToRemove.forEach((key) => window.localStorage.removeItem(key));
  } catch {
    // Ignore storage access errors
  }
}

/**
 * Safely extracts a query parameter from the URL hash string.
 *
 * @param paramName Target query parameter key.
 * @returns Parameter value string or null if not found.
 */
export function getHashQueryParam(paramName: string): string | null {
  if (typeof window === 'undefined' || !window.location.hash) {
    return null;
  }
  try {
    const hashQuery = window.location.hash.split('?')[1];
    if (!hashQuery) return null;
    const params = new URLSearchParams(hashQuery);
    return params.get(paramName);
  } catch {
    return null;
  }
}


const ACTIVE_PLAYLIST_KEY = 'active_playlist_id';

/**
 * Safely retrieves the stored active playlist identifier.
 *
 * @returns Playlist ID string (defaults to 'default').
 */
export function getActivePlaylistId(): string {
  return getPreference<string>(ACTIVE_PLAYLIST_KEY, 'default');
}

/**
 * Safely persists the active playlist identifier.
 *
 * @param playlistId Playlist ID string.
 */
export function setActivePlaylistId(playlistId: string): void {
  setPreference(ACTIVE_PLAYLIST_KEY, playlistId || 'default');
}


const SEARCH_VIEW_MODE_KEY = 'search_view_mode';
const SEARCH_DENSITY_MODE_KEY = 'search_density_mode';
const RECENT_SEARCHES_KEY = 'search_recent_queries';

/**
 * Safely retrieves the stored search layout view mode ('timeline' or 'grouped').
 *
 * @returns Layout mode string (defaults to 'timeline').
 */
export function getSearchViewMode(): 'timeline' | 'grouped' {
  return getPreference<'timeline' | 'grouped'>(SEARCH_VIEW_MODE_KEY, 'timeline');
}

/**
 * Safely persists the search layout view mode.
 *
 * @param mode Layout view mode ('timeline' or 'grouped').
 */
export function setSearchViewMode(mode: 'timeline' | 'grouped'): void {
  setPreference(SEARCH_VIEW_MODE_KEY, mode);
}

/**
 * Safely retrieves the stored search card density mode ('cards' or 'compact').
 *
 * @returns Card density mode string (defaults to 'cards').
 */
export function getSearchDensityMode(): 'cards' | 'compact' {
  return getPreference<'cards' | 'compact'>(SEARCH_DENSITY_MODE_KEY, 'cards');
}

/**
 * Safely persists the search card density mode.
 *
 * @param density Card density mode ('cards' or 'compact').
 */
export function setSearchDensityMode(density: 'cards' | 'compact'): void {
  setPreference(SEARCH_DENSITY_MODE_KEY, density);
}

/**
 * Safely retrieves the list of recent search query strings.
 *
 * @returns Array of recent query strings.
 */
export function getRecentSearches(): string[] {
  return getPreference<string[]>(RECENT_SEARCHES_KEY, []);
}

/**
 * Adds a query string to recent searches (deduplicated, latest first).
 *
 * @param query Search query to store.
 * @param maxItems Maximum history length (default 10).
 */
export function addRecentSearch(query: string, maxItems = 10): void {
  const trimmed = query.trim();
  if (!trimmed) return;
  const current = getRecentSearches().filter((q) => q.toLowerCase() !== trimmed.toLowerCase());
  const updated = [trimmed, ...current].slice(0, maxItems);
  setPreference(RECENT_SEARCHES_KEY, updated);
}

/**
 * Removes a specific query from recent searches history.
 *
 * @param query Target query to remove.
 */
export function removeRecentSearch(query: string): void {
  const updated = getRecentSearches().filter((q) => q !== query);
  setPreference(RECENT_SEARCHES_KEY, updated);
}

/**
 * Clears all stored recent searches history.
 */
export function clearRecentSearches(): void {
  setPreference(RECENT_SEARCHES_KEY, []);
}

export type LiveChannelScope = 'curated' | 'all';
const LIVE_CHANNEL_SCOPE_KEY = 'tv_channel_scope';

/**
 * Safely retrieves the stored Live TV channel scope mode ('curated' or 'all').
 *
 * @returns Scope string (defaults to 'curated').
 */
export function getLiveChannelScope(): LiveChannelScope {
  return getPreference<LiveChannelScope>(LIVE_CHANNEL_SCOPE_KEY, 'curated');
}

/**
 * Safely persists the Live TV channel scope mode.
 *
 * @param scope Scope mode ('curated' or 'all').
 */
export function setLiveChannelScope(scope: LiveChannelScope): void {
  setPreference(LIVE_CHANNEL_SCOPE_KEY, scope);
}

const EPG_SLOW_NUDGE_DISMISSED_KEY = 'epg_slow_nudge_dismissed';

/**
 * Safely retrieves whether the slow EPG sync upgrade nudge has been dismissed.
 *
 * @returns True if dismissed, false otherwise.
 */
export function getEpgSlowNudgeDismissed(): boolean {
  return getPreference<boolean>(EPG_SLOW_NUDGE_DISMISSED_KEY, false);
}

/**
 * Safely persists the dismissed status for the slow EPG sync upgrade nudge.
 *
 * @param dismissed True if dismissed.
 */
export function setEpgSlowNudgeDismissed(dismissed: boolean): void {
  setPreference(EPG_SLOW_NUDGE_DISMISSED_KEY, dismissed);
}
