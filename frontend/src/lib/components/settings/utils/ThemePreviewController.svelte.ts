import { getPreference } from '$lib/utils/preferences';
import { applyTheme } from '$lib/utils/themeUtils';
import { toastStore } from '$lib/stores/toastStore';

export interface ThemeOption {
  value: string;
  label: string;
  description: string;
}

export const THEME_OPTIONS: ThemeOption[] = [
  {
    value: 'pluvira',
    label: 'Pluvira Dark (Default)',
    description: 'Modern ocean slate canvas with bio-emerald and hydra cyan accents.'
  },
  {
    value: 'landonorris',
    label: 'Lando Norris',
    description: 'Minimal warm olive canvas with vibrant electric lime accent.'
  },
  {
    value: 'neon',
    label: 'Neon Emerald',
    description: 'Deep black background with emerald green accent highlights.'
  }
];

export class ThemePreviewController {
  activeTheme = $state(getPreference<string>('ui_theme', 'pluvira'));
  previewTheme = $state(getPreference<string>('ui_theme', 'pluvira'));

  setPreview(theme: string) {
    this.previewTheme = theme;
  }

  applyActiveTheme() {
    this.activeTheme = this.previewTheme;
    applyTheme(this.previewTheme);
    toastStore.success(`Theme '${this.previewTheme.toUpperCase()}' applied successfully.`);
  }

  resetPreview() {
    this.previewTheme = this.activeTheme;
  }
}
