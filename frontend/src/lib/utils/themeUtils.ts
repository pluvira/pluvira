import { getPreference, setPreference } from './preferences';

/**
 * Applies a theme name to the HTML document element and persists preference.
 *
 * @param themeName Theme identifier string (e.g. 'pluvira', 'landonorris', 'neon').
 */
export function applyTheme(themeName: string): void {
  if (typeof document === 'undefined') return;
  document.documentElement.setAttribute('data-theme', themeName);
  setPreference('ui_theme', themeName);
}

/**
 * Initializes theme from stored user preferences or defaults to 'pluvira'.
 *
 * @returns Initialized theme name string.
 */
export function initTheme(): string {
  const theme = getPreference<string>('ui_theme', 'pluvira');
  applyTheme(theme);
  return theme;
}
