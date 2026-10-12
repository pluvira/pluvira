import { getPreference, setPreference } from '$lib/utils/preferences';
import { playlistStore } from '$lib/stores/playlistStore';

export class SidebarController {
  public isCollapsed = $state(getPreference<boolean>('sb_collapsed', false));
  public isMobileOpen = $state(false);
  public showLicenseModal = $state(false);
  public showBulletinDrawer = $state(false);
  public showSyncMenu = $state(false);

  /**
   * Toggles sidebar collapsed state and persists preference.
   */
  public toggleCollapse(): void {
    this.isCollapsed = !this.isCollapsed;
    setPreference('sb_collapsed', this.isCollapsed);
  }

  /**
   * Opens mobile off-canvas drawer.
   */
  public openMobileDrawer(): void {
    this.isMobileOpen = true;
  }

  /**
   * Closes mobile off-canvas drawer.
   */
  public closeMobileDrawer(): void {
    this.isMobileOpen = false;
  }

  /**
   * Toggles mobile off-canvas drawer open state.
   */
  public toggleMobileDrawer(): void {
    this.isMobileOpen = !this.isMobileOpen;
  }

  /**
   * Opens Pro upgrade / license details modal.
   */
  public openLicenseModal(): void {
    this.showLicenseModal = true;
  }

  /**
   * Opens Bulletin / Notices drawer.
   */
  public openBulletinDrawer(): void {
    this.showBulletinDrawer = true;
  }

  /**
   * Toggles sync catalog options popover menu.
   */
  public toggleSyncMenu(): void {
    this.showSyncMenu = !this.showSyncMenu;
  }

  /**
   * Closes sync catalog options popover menu.
   */
  public closeSyncMenu(): void {
    this.showSyncMenu = false;
  }

  /**
   * Switches active curated playlist in playlistStore.
   */
  public handlePlaylistChange(playlistId: string): void {
    playlistStore.setActivePlaylist(playlistId);
  }

  /**
   * Triggers background acquisition update.
   */
  public triggerSync(mode: string, onTriggerUpdate?: (mode: string) => void): void {
    this.showSyncMenu = false;
    if (onTriggerUpdate) {
      onTriggerUpdate(mode);
    }
  }
}
