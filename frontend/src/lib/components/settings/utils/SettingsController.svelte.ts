import { api } from '$lib/api/client';
import type { GlobalConfig, SchedulePayload, Source, EPGSource, LicenseResponse, ScheduledJob, HistoryRecord, SystemStatus, EpgSourceStatItem } from '$lib/api/types';
import { toastStore } from '$lib/stores/toastStore';
import { licenseStore } from '$lib/stores/licenseStore';
import {
  getPreference,
  setPreference,
  getHashQueryParam,
  resetDeleteConfirmations,
  getEpgSlowNudgeDismissed,
  setEpgSlowNudgeDismissed
} from '$lib/utils/preferences';
import { removeArrayItem, moveArrayItem } from '$lib/utils/arrayUtils';
import { parseNewlineList } from '$lib/utils/stringUtils';
import { formatCrockfordId } from '$lib/utils/crockfordUtils';
import {
  normalizeConfig,
  normalizeSchedule,
  isConfigDirty,
  isScheduleDirty,
  type MacroSettingsTabKey,
  type GeneralSubTabKey,
  type SourcesSubTabKey,
  type UpdatesSubTabKey,
  type BackupSubTabKey,
  type NotificationSectionsState,
  DEFAULT_NOTIFICATION_SECTIONS
} from './SettingsUtils';

export class SettingsController {
  public loading = $state(false);
  public saving = $state(false);
  public activeMacroTab = $state<MacroSettingsTabKey>(
    getPreference<MacroSettingsTabKey>('st_active_macro_tab', 'general')
  );
  public generalSubTab = $state<GeneralSubTabKey>(
    (() => {
      const saved = getPreference<string>('st_general_sub_tab', 'system');
      return (['system', 'advanced', 'theme'].includes(saved) ? saved : 'system') as GeneralSubTabKey;
    })()
  );
  public sourcesSubTab = $state<SourcesSubTabKey>(
    getPreference<SourcesSubTabKey>('st_sources_sub_tab', 'iptv')
  );
  public updatesSubTab = $state<UpdatesSubTabKey>(
    getPreference<UpdatesSubTabKey>('st_updates_sub_tab', 'scheduler')
  );
  public backupSubTab = $state<BackupSubTabKey>(
    getPreference<BackupSubTabKey>('st_backup_sub_tab', 'backup')
  );

  public showPassword = $state(false);
  public newOverrideKey = $state('');
  public newOverrideValue = $state('');
  public newNotificationUrl = $state('');
  public openAllowedMap = $state<Record<number, boolean>>({});
  public openDeniedMap = $state<Record<number, boolean>>({});
  public openRewritesSectionMap = $state<Record<number, boolean>>({});

  public get sourceOptions(): string[] {
    return (this.config?.sources || []).map((s) => s.name).filter(Boolean);
  }

  public get crockfordId(): string | null {
    return (
      (this.licenseData as any)?.crockford_id ||
      this.licenseData?.license?.crockford_id ||
      this.systemStatus?.license?.crockford_id ||
      this.systemStatus?.crockford_id ||
      null
    );
  }

  public get formattedCrockfordId(): string {
    return formatCrockfordId(this.crockfordId);
  }

  public get isRegistered(): boolean {
    return Boolean(this.crockfordId);
  }

  public copyCrockfordId(): void {
    const idToCopy = this.formattedCrockfordId || this.crockfordId;
    if (!idToCopy) return;
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(idToCopy);
      toastStore.info(`Copied Crockford UID ${idToCopy} to clipboard.`);
    }
  }

  public toggleShowPassword(): void {
    this.showPassword = !this.showPassword;
  }

  public toggleAllowedOpen(sourceIdx: number, val?: boolean): void {
    const cur = Boolean(this.openAllowedMap[sourceIdx]);
    this.openAllowedMap = { ...this.openAllowedMap, [sourceIdx]: val !== undefined ? val : !cur };
  }

  public toggleDeniedOpen(sourceIdx: number, val?: boolean): void {
    const cur = Boolean(this.openDeniedMap[sourceIdx]);
    this.openDeniedMap = { ...this.openDeniedMap, [sourceIdx]: val !== undefined ? val : !cur };
  }

  public toggleRewritesSectionOpen(sourceIdx: number, val?: boolean): void {
    const cur = Boolean(this.openRewritesSectionMap[sourceIdx]);
    this.openRewritesSectionMap = { ...this.openRewritesSectionMap, [sourceIdx]: val !== undefined ? val : !cur };
  }

  public get activeTab(): MacroSettingsTabKey {
    return this.activeMacroTab;
  }
  public set activeTab(tab: MacroSettingsTabKey) {
    this.setMacroTab(tab);
  }

  public config = $state<GlobalConfig>(normalizeConfig());
  public schedule = $state<SchedulePayload>({ enabled: true, jobs: [] });
  public initialConfig = $state<GlobalConfig | null>(null);
  public initialSchedule = $state<SchedulePayload | null>(null);

  public isDirty = $derived(
    isConfigDirty(this.initialConfig, this.config) ||
    isScheduleDirty(this.initialSchedule, this.schedule)
  );
  public expandSource = $state<string | null>(null);
  public expandedIptvIdx = $state<number | null>(getPreference<number | null>('st_iptv_open_idx', null));
  public expandedEpgIdx = $state<number | null>(getPreference<number | null>('st_epg_open_idx', null));
  public expandedOverridesIdx = $state<number | null>(getPreference<number | null>('gt_overrides_open_idx', null));
  public cachingOpen = $state<boolean>(getPreference<boolean>('gt_caching_open', false));
  public rewritesSectionOpen = $state<boolean>(getPreference<boolean>('gt_rewrites_section_open', false));
  public overridesSectionOpen = $state<boolean>(getPreference<boolean>('gt_overrides_section_open', false));
  public notificationSections = $state<NotificationSectionsState>(
    getPreference<NotificationSectionsState>('nt_matrix_sections', { ...DEFAULT_NOTIFICATION_SECTIONS })
  );

  public licenseData = $state<LicenseResponse | null>(null);
  public loadingLicense = $state(false);
  public systemStatus = $state<SystemStatus | null>(null);

  public history = $state<HistoryRecord[]>([]);
  public globalStats = $state<Record<string, unknown>>({});
  public epgSourcesStats = $state<EpgSourceStatItem[]>([]);
  public epgSlowNudgeDismissed = $state<boolean>(getEpgSlowNudgeDismissed());
  public terminalLogs = $state<string[]>([]);

  public get hasSlowSyncWarning(): boolean {
    if (this.epgSlowNudgeDismissed) return false;
    return this.epgSourcesStats.some((s) => Boolean(s.slow_sync_warning));
  }
  private logTimer: ReturnType<typeof setInterval> | null = null;

  public testingIndex = $state<number | null>(null);
  public testingSourceIndex = $state<number | null>(null);
  public iptvStatusMap = $state<Record<number, 'ok' | 'ko'>>({});
  public epgStatusMap = $state<Record<number, 'ok' | 'ko'>>({});
  public clearingCache = $state(false);
  public testingUrl = $state<string | null>(null);
  public availableGroups = $state<string[]>([]);

  /**
   * Loads group suggestions for scheduler filters.
   */
  public async loadGroupSuggestions(): Promise<void> {
    try {
      const res: any = await api.getChannels({ limit: 1000 });
      const items = Array.isArray(res) ? res : (res.items || []);
      const groups = new Set<string>();
      items.forEach((ch: any) => {
        if (ch.group) groups.add(ch.group.trim());
      });
      this.availableGroups = Array.from(groups).sort();
    } catch {
      this.availableGroups = [];
    }
  }

  /**
   * Dispatches a test notification to webhook targets.
   */
  public async testNotification(url?: string, isPro = true): Promise<void> {
    if (!isPro) {
      toastStore.warning('Multi-target webhook notifications require Pluvira Pro edition.');
      return;
    }
    if (!this.config.settings?.notifications?.enabled) {
      toastStore.warning('Please enable global notifications before sending a test notification.');
      return;
    }

    const currentUrls = this.config.settings.notifications.urls || [];
    if (currentUrls.length === 0 && !url) {
      toastStore.warning('Please add and save at least one notification destination URL before testing.');
      return;
    }

    this.testingUrl = url || 'all';
    try {
      await api.testNotification(
        '🔔 Pluvira: Test Notification',
        'Test notification message dispatched from Settings panel.',
        url
      );
      toastStore.success('Test notification sent successfully.');
    } catch (err: any) {
      toastStore.error(`Test notification failed: ${err.message}`);
    } finally {
      this.testingUrl = null;
    }
  }

  /**
   * Applies a quick event triggers preset profile.
   */
  public async applyNotificationPreset(presetName: string, isPro = true): Promise<void> {
    if (!isPro) {
      toastStore.warning('Notification presets and custom event matrices require Pluvira Pro edition.');
      return;
    }
    try {
      const res = await api.applyNotificationPreset(presetName);
      if (res && res.events) {
        this.config.settings.notifications!.events = res.events as any;
      }
      this.config = { ...this.config };
    } catch (err: any) {
      toastStore.error(`Failed to apply preset: ${err.message}`);
    }
  }

  /**
   * Loads cryptographic Pro license and IPC verification status details.
   */
  public async loadLicenseDetails(notify = false): Promise<void> {
    this.loadingLicense = true;
    try {
      const [licRes, sysRes] = await Promise.all([
        api.getLicense(),
        api.getSystemStatus().catch(() => null)
      ]);
      this.licenseData = licRes;
      if (sysRes) {
        this.systemStatus = sysRes;
      }
      if (this.licenseData) {
        licenseStore.updateFromLicenseResponse(this.licenseData);
      }
      if (notify) {
        if (licRes.license_valid) {
          const days = licRes.license?.days_remaining;
          toastStore.success(`Pro license verified: Active Valid (${days ?? 0} days remaining).`);
        } else {
          const reason = licRes.license?.message || licRes.license?.error_code || 'Unlicensed Core edition';
          toastStore.info(`License status: ${reason}.`);
        }
      }
    } catch (err: any) {
      this.licenseData = null;
      if (notify) {
        toastStore.error(`License verification failed: ${err.message}`);
      }
    } finally {
      this.loadingLicense = false;
    }
  }

  /**
   * Clears active system cache driver memory.
   */
  public async clearCache(): Promise<void> {
    this.clearingCache = true;
    toastStore.info('Clearing active system cache driver...');
    try {
      await api.clearCache();
      toastStore.success('System cache cleared successfully!');
    } catch (err: any) {
      toastStore.error(`Failed to clear cache: ${err.message}`);
    } finally {
      this.clearingCache = false;
    }
  }

  /**
   * Adds a new IPTV M3U source configuration.
   */
  public setExpandedIptvIdx(idx: number | null): void {
    this.expandedIptvIdx = idx;
    setPreference('st_iptv_open_idx', idx);
  }

  public setExpandedEpgIdx(idx: number | null): void {
    this.expandedEpgIdx = idx;
    setPreference('st_epg_open_idx', idx);
  }

  public setExpandedOverridesIdx(idx: number | null): void {
    this.expandedOverridesIdx = idx;
    setPreference('gt_overrides_open_idx', idx);
  }

  public setCachingOpen(val: boolean): void {
    this.cachingOpen = val;
    setPreference('gt_caching_open', val);
  }

  public setRewritesSectionOpen(val: boolean): void {
    this.rewritesSectionOpen = val;
    setPreference('gt_rewrites_section_open', val);
  }

  public setOverridesSectionOpen(val: boolean): void {
    this.overridesSectionOpen = val;
    setPreference('gt_overrides_section_open', val);
  }

  public toggleNotificationSection(section: string): void {
    const key = section as keyof NotificationSectionsState;
    if (key in this.notificationSections) {
      this.notificationSections[key] = !this.notificationSections[key];
      setPreference('nt_matrix_sections', this.notificationSections);
    }
  }

  public resetConfirmations(): void {
    resetDeleteConfirmations();
    toastStore.success('All delete confirmation prompts restored successfully.');
  }

  public dismissEpgSlowNudge(): void {
    this.epgSlowNudgeDismissed = true;
    setEpgSlowNudgeDismissed(true);
  }

  /**
   * Updates custom stopwords list by parsing multiline input text.
   *
   * @param text Multiline stopwords string.
   */
  public updateCustomStopwords(text: string): void {
    if (!this.config.settings) return;
    this.config.settings.custom_stopwords = parseNewlineList(text);
  }

  public addSource(): void {
    const newSource: Source = {
      name: 'New IPTV Source',
      enabled: true,
      m3u_url: '',
      settings: {
        allow_channels: [],
        deny_channels: [],
        rewrites: [],
        mapping_overrides: {}
      }
    };
    this.config.sources = [...(this.config.sources || []), newSource];
    this.setExpandedIptvIdx(this.config.sources.length - 1);
  }

  /**
   * Removes an IPTV source configuration by index.
   */
  public removeSource(index: number): void {
    this.config.sources = removeArrayItem(this.config.sources, index);
  }

  /**
   * Moves an IPTV source up or down in priority.
   */
  public moveSource(index: number, direction: number): void {
    this.config.sources = moveArrayItem(this.config.sources, index, direction);
  }

  /**
   * Toggles source-specific settings override block.
   */
  public toggleSourceOverride(src: Source): void {
    if (src.settings) {
      src.settings = null;
    } else {
      src.settings = {
        allow_channels: [],
        deny_channels: [],
        rewrites: [],
        mapping_overrides: {}
      };
    }
  }

  /**
   * Updates allowed channels list for a source by parsing multiline input text.
   *
   * @param sourceIndex Target source index.
   * @param text Multiline channels text.
   */
  public updateAllowChannels(sourceIndex: number, text: string): void {
    if (this.config.sources && this.config.sources[sourceIndex]?.settings) {
      this.config.sources[sourceIndex].settings!.allow_channels = parseNewlineList(text);
    }
  }

  /**
   * Updates denied channels list for a source by parsing multiline input text.
   *
   * @param sourceIndex Target source index.
   * @param text Multiline channels text.
   */
  public updateDenyChannels(sourceIndex: number, text: string): void {
    if (this.config.sources && this.config.sources[sourceIndex]?.settings) {
      this.config.sources[sourceIndex].settings!.deny_channels = parseNewlineList(text);
    }
  }

  /**
   * Adds a new manual EPG mapping override rule.
   *
   * @param key M3U Channel name.
   * @param value Namespaced EPG ID.
   */
  public submitNewMappingOverride(): void {
    if (this.newOverrideKey.trim() && this.newOverrideValue.trim()) {
      this.addMappingOverride(this.newOverrideKey, this.newOverrideValue);
      this.newOverrideKey = '';
      this.newOverrideValue = '';
      this.setOverridesSectionOpen(true);
      if (this.config.settings.mapping_overrides) {
        this.setExpandedOverridesIdx(Object.keys(this.config.settings.mapping_overrides).length - 1);
      }
    }
  }

  public addNotificationUrl(): void {
    const url = this.newNotificationUrl.trim();
    if (!url || !this.config.settings) return;
    if (!this.config.settings.notifications) {
      this.config.settings.notifications = {
        enabled: false,
        urls: [],
        events: {
          update_success: true,
          update_failure: true,
          link_test_report: true,
          link_ko_detected: true,
          disk_space_warning: true
        }
      };
    }
    const currentUrls = this.config.settings.notifications.urls || [];
    if (!currentUrls.includes(url)) {
      this.config.settings.notifications.urls = [...currentUrls, url];
      this.config.settings.notification_urls = [...this.config.settings.notifications.urls];
      this.config = { ...this.config };
      this.newNotificationUrl = '';
    }
  }

  public removeNotificationUrl(url: string): void {
    if (!this.config.settings?.notifications?.urls) return;
    this.config.settings.notifications.urls = this.config.settings.notifications.urls.filter((u) => u !== url);
    this.config.settings.notification_urls = [...this.config.settings.notifications.urls];
    this.config = { ...this.config };
  }

  public setNotificationsEnabled(enabled: boolean, isPro: boolean): void {
    if (!this.config.settings) return;
    if (!this.config.settings.notifications) {
      this.config.settings.notifications = {
        enabled: false,
        urls: [],
        events: {
          update_success: true,
          update_failure: true,
          link_test_report: true,
          link_ko_detected: true,
          disk_space_warning: true
        }
      };
    }
    if (!isPro && enabled) {
      this.config.settings.notifications.enabled = false;
      toastStore.warning('Notifications matrix requires Pluvira Pro edition.');
      return;
    }
    this.config.settings.notifications.enabled = enabled;
    this.config = { ...this.config };
  }

  public addMappingOverride(key: string, value: string): void {
    const k = key.trim();
    const v = value.trim();
    if (!k || !v) return;

    if (!this.config.settings.mapping_overrides) {
      this.config.settings.mapping_overrides = {};
    }
    this.config.settings.mapping_overrides = {
      ...this.config.settings.mapping_overrides,
      [k]: v
    };
  }

  /**
   * Removes a manual EPG mapping override by key name.
   *
   * @param key M3U Channel name key to remove.
   */
  public removeMappingOverride(key: string): void {
    if (this.config.settings.mapping_overrides) {
      const updated = { ...this.config.settings.mapping_overrides };
      delete updated[key];
      this.config.settings.mapping_overrides = updated;
    }
  }

  /**
   * Moves an EPG mapping override up or down in order.
   *
   * @param index Target entry index.
   * @param direction -1 for up, 1 for down.
   */
  public moveMappingOverride(index: number, direction: number): void {
    if (!this.config.settings.mapping_overrides) return;
    const entries = Object.entries(this.config.settings.mapping_overrides);
    const newIndex = index + direction;
    if (newIndex >= 0 && newIndex < entries.length) {
      const temp = entries[index];
      entries[index] = entries[newIndex];
      entries[newIndex] = temp;
      this.config.settings.mapping_overrides = Object.fromEntries(entries);
    }
  }

  /**
   * Updates an existing EPG mapping override key name.
   *
   * @param oldKey Existing key name.
   * @param newKey Updated key name.
   * @param val EPG ID value.
   */
  public updateMappingOverrideKey(oldKey: string, newKey: string, val: string): void {
    const k = newKey.trim();
    if (!k || k === oldKey || !this.config.settings.mapping_overrides) return;
    const updated = { ...this.config.settings.mapping_overrides };
    delete updated[oldKey];
    updated[k] = val;
    this.config.settings.mapping_overrides = updated;
  }

  /**
   * Updates an existing EPG mapping override value.
   *
   * @param key Key name.
   * @param newVal Updated EPG ID value.
   */
  public updateMappingOverrideValue(key: string, newVal: string): void {
    if (this.config.settings.mapping_overrides) {
      this.config.settings.mapping_overrides[key] = newVal.trim();
    }
  }

  /**
   * Triggers background acquisition refresh for specific IPTV sources.
   */
  public async refreshSources(sourceNames: string[]): Promise<void> {
    if (sourceNames.length === 0) return;
    try {
      await api.bulkRefreshSources({ names: sourceNames });
      toastStore.success(`Refresh triggered for ${sourceNames.length} IPTV source(s).`);
    } catch (err: any) {
      toastStore.error(`Failed to trigger source refresh: ${err.message}`);
    }
  }

  /**
   * Adds a new global EPG guide source configuration.
   */
  public addEpgSource(): void {
    const newEpg: EPGSource = {
      name: 'New EPG Source',
      enabled: true,
      url: '',
      user_agent: ''
    };
    this.config.epg_sources = [...(this.config.epg_sources || []), newEpg];
    this.setExpandedEpgIdx(this.config.epg_sources.length - 1);
  }

  /**
   * Removes an EPG source configuration by index.
   */
  public removeEpgSource(index: number): void {
    this.config.epg_sources = removeArrayItem(this.config.epg_sources, index);
  }

  /**
   * Moves an EPG source up or down in priority.
   */
  public moveEpgSource(index: number, direction: number): void {
    this.config.epg_sources = moveArrayItem(this.config.epg_sources, index, direction);
  }

  /**
   * Tests HTTP reachability for an EPG guide source URL.
   */
  /**
   * Tests HTTP reachability for an IPTV M3U source URL.
   */
  public async testSourceConnection(url: string, index: number): Promise<void> {
    if (!url) {
      toastStore.warning('IPTV source URL is empty.');
      return;
    }

    this.testingSourceIndex = index;
    toastStore.info(`Testing IPTV connection to ${url}...`);

    try {
      const res = await api.testStreamLink({ url, user_agent: 'Mozilla/5.0' });
      const ok = ((res.code as number) || 0) >= 200 && ((res.code as number) || 0) < 400;
      this.iptvStatusMap = { ...this.iptvStatusMap, [index]: ok ? 'ok' : 'ko' };
      const result = res;
      const code = (result.code as number) || 0;
      if (code >= 200 && code < 400) {
        toastStore.success(`Connection OK! (HTTP ${code})`);
      } else {
        toastStore.error(`Connection failed! (HTTP ${code})`);
      }
    } catch (err: any) {
      this.iptvStatusMap = { ...this.iptvStatusMap, [index]: 'ko' };
      toastStore.error(`Connection check failed: ${err.message}`);
    } finally {
      this.testingSourceIndex = null;
    }
  }

  public async testEpgConnection(url: string, index: number): Promise<void> {
    if (!url) {
      toastStore.warning('EPG source URL is empty.');
      return;
    }

    this.testingIndex = index;
    toastStore.info(`Testing EPG connection to ${url}...`);

    try {
      const res = await api.testStreamLink({ url, user_agent: 'Mozilla/5.0' });
      const ok = ((res.code as number) || 0) >= 200 && ((res.code as number) || 0) < 400;
      this.epgStatusMap = { ...this.epgStatusMap, [index]: ok ? 'ok' : 'ko' };
      const result = res;
      const code = (result.code as number) || 0;
      if (code >= 200 && code < 400) {
        toastStore.success(`Connection OK! (HTTP ${code})`);
      } else {
        toastStore.error(`Connection failed! (HTTP ${code})`);
      }
    } catch (err: any) {
      this.epgStatusMap = { ...this.epgStatusMap, [index]: 'ko' };
      toastStore.error(`Connection check failed: ${err.message}`);
    } finally {
      this.testingIndex = null;
    }
  }

  /**
   * Triggers background acquisition refresh for specific EPG sources.
   */
  public async refreshEpgSources(sourceNames: string[]): Promise<void> {
    if (sourceNames.length === 0) return;
    try {
      await api.bulkRefreshEpgSources({ names: sourceNames });
      toastStore.success(`Refresh triggered for ${sourceNames.length} EPG source(s).`);
    } catch (err: any) {
      toastStore.error(`Failed to trigger EPG source refresh: ${err.message}`);
    }
  }

  /**
   * Adds a new scheduled background job.
   */
  public addJob(): void {
    if (!this.schedule) {
      this.schedule = { enabled: true, jobs: [] };
    }
    if (!this.schedule.jobs) {
      this.schedule.jobs = [];
    }

    const newJob: ScheduledJob = {
      id: `update_job_${this.schedule.jobs.length + 1}`,
      enabled: true,
      trigger: 'cron',
      hour: 4,
      minute: 0,
      day_of_week: '*',
      hours: 0,
      minutes: 0,
      mode: 'full',
      description: 'Custom background update task',
      link_test_filters: {
        inclusion: 'included_only',
        status_filter: 'all',
        sources: [],
        groups: [],
        name_regex: '',
        max_channels: 50
      }
    };
    this.schedule.jobs = [...this.schedule.jobs, newJob];
  }

  /**
   * Removes a scheduled job by index.
   */
  public removeJob(index: number): void {
    if (this.schedule) {
      this.schedule.jobs = removeArrayItem(this.schedule.jobs, index);
    }
  }

  /**
   * Triggers immediate background execution for a scheduled job.
   */
  public async runJobNow(job: ScheduledJob): Promise<void> {
    const jobId = job.id || 'unnamed_job';
    toastStore.info(`Triggering background job execution for '${jobId}'...`);
    try {
      if (job.mode === 'link_test') {
        await api.testLinksBatch({
          items: []
        });
      } else {
        await api.triggerUpdate(job.mode);
      }
      toastStore.success(`Job '${jobId}' triggered successfully.`);
    } catch (err: any) {
      toastStore.error(`Failed to execute job: ${err.message}`);
    }
  }

  /**
   * Restores factory default system and recommended scheduler tasks.
   *
   * @param mode Restoration mode ('missing_only' or 'full_reset').
   */
  public async restoreDefaultSchedulerJobs(mode: 'missing_only' | 'full_reset' = 'missing_only'): Promise<void> {
    toastStore.info('Restoring default scheduler tasks...');
    try {
      const res = await api.restoreDefaultSchedulerJobs(mode);
      if (res && res.jobs) {
        this.schedule = normalizeSchedule(res);
        this.initialSchedule = JSON.parse(JSON.stringify(this.schedule));
      }
      toastStore.success('Default scheduler tasks restored successfully.');
    } catch (err: any) {
      toastStore.error(`Failed to restore default tasks: ${err.message}`);
    }
  }

  /**
   * Loads configuration and scheduler settings from API.
   */
  public async loadMetricsData(): Promise<void> {
    try {
      const [analyticsRes, historyRes] = await Promise.all([
        api.getDashboardAnalytics(),
        api.getHistory()
      ]);
      this.globalStats = analyticsRes.global_stats || {};
      this.epgSourcesStats = (analyticsRes.epg_sources_stats as unknown as EpgSourceStatItem[]) || [];
      this.history = historyRes || [];
    } catch (err: any) {
      toastStore.error(`Failed to load metrics: ${err.message}`);
    }
  }

  public async deleteHistoryRecord(recordId: string): Promise<void> {
    try {
      await api.deleteHistoryRecord(recordId);
      toastStore.info('History record deleted.');
      await this.loadMetricsData();
    } catch (err: any) {
      toastStore.error(`Failed to delete record: ${err.message}`);
    }
  }

  public async clearAllHistory(): Promise<void> {
    try {
      await api.clearHistory();
      toastStore.info('Execution history cleared.');
      await this.loadMetricsData();
    } catch (err: any) {
      toastStore.error(`Failed to clear history: ${err.message}`);
    }
  }

  public startLogPolling(): void {
    this.stopLogPolling();
    this.fetchLogs();
    this.logTimer = setInterval(() => this.fetchLogs(), 2000);
  }

  public stopLogPolling(): void {
    if (this.logTimer) {
      clearInterval(this.logTimer);
      this.logTimer = null;
    }
  }

  private async fetchLogs(): Promise<void> {
    try {
      const logs = await api.getSystemLogs(200);
      if (logs && Array.isArray(logs) && logs.length > 0) {
        this.terminalLogs = [...this.terminalLogs, ...logs];
        if (this.terminalLogs.length > 1000) {
          this.terminalLogs = this.terminalLogs.slice(this.terminalLogs.length - 1000);
        }
      }
    } catch {
      // Ignore poll error
    }
  }

  public async loadSettings(): Promise<void> {
    this.loading = true;
    try {
      const rawTab = getHashQueryParam('tab');
      const rawSub = getHashQueryParam('sub');
      const targetExpand = getHashQueryParam('expand');

      if (rawTab && ['general', 'sources', 'updates', 'backup'].includes(rawTab)) {
        this.activeMacroTab = rawTab as MacroSettingsTabKey;
        if (rawSub) {
          this.setSubSegment(this.activeMacroTab, rawSub);
        }
      }
      if (targetExpand) {
        this.expandSource = targetExpand;
      }

      const [cfgRes, schedRes, licRes, sysRes, analyticsRes, sourcesRes, epgSourcesRes] = await Promise.all([
        api.getConfig(),
        api.getSchedule(),
        api.getLicense().catch(() => null),
        api.getSystemStatus().catch(() => null),
        api.getDashboardAnalytics().catch(() => null),
        api.getSources().catch(() => []),
        api.getEpgSources().catch(() => [])
      ]);

      if (analyticsRes) {
        this.globalStats = analyticsRes.global_stats || {};
        this.epgSourcesStats = (analyticsRes.epg_sources_stats as unknown as EpgSourceStatItem[]) || [];
      }

      this.config = normalizeConfig(cfgRes);
      this.config.sources = sourcesRes || [];
      this.config.epg_sources = epgSourcesRes || [];
      if (!this.config.settings.rewrites) {
        this.config.settings.rewrites = [];
      }
      this.schedule = normalizeSchedule(schedRes);
      this.initialConfig = JSON.parse(JSON.stringify(this.config));
      this.initialSchedule = JSON.parse(JSON.stringify(this.schedule));

      if (licRes) {
        this.licenseData = licRes;
        licenseStore.updateFromLicenseResponse(licRes);
      }
      if (sysRes) {
        this.systemStatus = sysRes;
      }
    } catch (err: any) {
      toastStore.error(`Failed to load settings: ${err.message}`);
    } finally {
      this.loading = false;
    }
  }

  /**
   * Saves updated configuration and scheduler settings to API.
   */
  public async saveSettings(): Promise<boolean> {
    this.saving = true;
    try {
      if (this.config.sources) {
        const initialSources = this.initialConfig?.sources || [];
        const currentNames = new Set(this.config.sources.map((s) => s.name));
        for (const s of initialSources) {
          if (!currentNames.has(s.name)) {
            await api.deleteSource(s.name).catch(() => {});
          }
        }
        for (const s of this.config.sources) {
          if (s.name && s.m3u_url) {
            const initial = initialSources.find((init) => init.name === s.name);
            if (!initial) {
              await api.createSource(s).catch(() => {});
            } else if (JSON.stringify(initial) !== JSON.stringify(s)) {
              await api.deleteSource(initial.name).catch(() => {});
              await api.createSource(s).catch(() => {});
            }
          }
        }
      }

      if (this.config.epg_sources) {
        const initialEpg = this.initialConfig?.epg_sources || [];
        const currentEpgNames = new Set(this.config.epg_sources.map((e) => e.name));
        for (const e of initialEpg) {
          if (!currentEpgNames.has(e.name)) {
            await api.deleteEpgSource(e.name).catch(() => {});
          }
        }
        for (const e of this.config.epg_sources) {
          if (e.name && e.url) {
            const initial = initialEpg.find((init) => init.name === e.name);
            if (!initial) {
              await api.createEpgSource(e).catch(() => {});
            } else if (JSON.stringify(initial) !== JSON.stringify(e)) {
              await api.deleteEpgSource(initial.name).catch(() => {});
              await api.createEpgSource(e).catch(() => {});
            }
          }
        }
      }

      const [updatedConfig] = await Promise.all([
        api.updateConfig(this.config),
        api.updateSchedule(this.schedule)
      ]);
      if (updatedConfig && updatedConfig.settings?.rewrites) {
        this.config.settings.rewrites = updatedConfig.settings.rewrites;
      }
      this.initialConfig = JSON.parse(JSON.stringify(this.config));
      this.initialSchedule = JSON.parse(JSON.stringify(this.schedule));
      toastStore.success('Configuration saved successfully!');
      return true;
    } catch (err: any) {
      toastStore.error(`Failed to save settings: ${err.message}`);
      return false;
    } finally {
      this.saving = false;
    }
  }

  /**
   * Switches active macro tab and persists preference.
   *
   * @param tab Target macro tab key.
   */
  public setMacroTab(tab: MacroSettingsTabKey): void {
    this.activeMacroTab = tab;
    setPreference('st_active_macro_tab', tab);
  }

  /**
   * Sets sub-segment for a given macro tab and persists preference.
   *
   * @param macro Target macro tab key.
   * @param sub Target sub-segment key string.
   */
  public setSubSegment(macro: MacroSettingsTabKey, sub: string): void {
    if (macro === 'general') {
      const validSubs: GeneralSubTabKey[] = ['system', 'advanced', 'theme'];
      this.generalSubTab = validSubs.includes(sub as GeneralSubTabKey) ? (sub as GeneralSubTabKey) : 'system';
      setPreference('st_general_sub_tab', this.generalSubTab);
    } else if (macro === 'sources') {
      this.sourcesSubTab = sub as SourcesSubTabKey;
      setPreference('st_sources_sub_tab', this.sourcesSubTab);
    } else if (macro === 'updates') {
      this.updatesSubTab = sub as UpdatesSubTabKey;
      setPreference('st_updates_sub_tab', this.updatesSubTab);
    } else if (macro === 'backup') {
      this.backupSubTab = sub as BackupSubTabKey;
      setPreference('st_backup_sub_tab', this.backupSubTab);
    }
  }

  /**
   * Switches active macro tab and persists preference.
   *
   * @param tab Target macro tab key.
   */
  public setTab(tab: MacroSettingsTabKey): void {
    this.setMacroTab(tab);
  }
}
