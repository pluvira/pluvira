import { api } from '$lib/api/client';
import type {
  ChannelItem,
  EPGSource,
  EPGMappingPayload,
  BatchTestLinkItem,
  EpgChannelIndexItem,
  ApplyMergePayload,
  PersonalChannel
} from '$lib/api/types';
import { toastStore } from '$lib/stores/toastStore';

export interface BatchChannelProgressItem extends ChannelItem {
  testState?: 'pending' | 'testing' | 'online' | 'offline';
}

/**
 * Normalizes channel title by removing common broadcast and resolution noise tags.
 */
export function cleanChannelTitle(name: string): string {
  return (name || '')
    .replace(/\s*\([^)]*\)/g, '')
    .replace(/\s*\[[^\]]*\]/g, '')
    .replace(/\b(HD|FHD|4K|UHD|1080p|720p|SD|HEVC|H264|H265|RAW|STREAM)\b/gi, '')
    .toLowerCase()
    .replace(/[^\w\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Calculates high-precision similarity score comparing candidate name against active query and channel name.
 */
export function calculateSimilarityScore(
  targetChannelName: string,
  searchQuery: string,
  candidateName: string
): number {
  const cleanTarget = cleanChannelTitle(targetChannelName);
  const cleanQuery = cleanChannelTitle(searchQuery);
  const cleanCand = cleanChannelTitle(candidateName);

  if (!cleanCand) return 0;

  function scoreSingle(ref: string, cand: string): number {
    if (!ref || !cand) return 0;
    if (ref === cand) return 100;

    if (cand.includes(ref) || ref.includes(cand)) {
      const minLen = Math.min(ref.length, cand.length);
      const maxLen = Math.max(ref.length, cand.length);
      const lengthRatio = minLen / maxLen;
      if (cand.startsWith(ref) || ref.startsWith(cand)) {
        return Math.max(90, Math.round(90 + (lengthRatio * 10)));
      }
      return Math.max(85, Math.round(85 + (lengthRatio * 10)));
    }

    const refTokens = ref.split(/\s+/).filter(Boolean);
    const candTokens = cand.split(/\s+/).filter(Boolean);
    if (refTokens.length === 0 || candTokens.length === 0) return 0;

    let matchedTokens = 0;
    for (const rt of refTokens) {
      if (candTokens.some((ct) => ct === rt || (ct.length > 3 && rt.length > 3 && (ct.includes(rt) || rt.includes(ct))))) {
        matchedTokens++;
      }
    }

    if (matchedTokens === 0) return 0;
    const tokenRatio = (2 * matchedTokens) / (refTokens.length + candTokens.length);
    return Math.round(tokenRatio * 95);
  }

  const queryScore = scoreSingle(cleanQuery, cleanCand);
  const targetScore = scoreSingle(cleanTarget, cleanCand);

  let finalScore = Math.max(queryScore, targetScore);
  if (queryScore >= 80 && targetScore >= 60) {
    finalScore = Math.min(100, finalScore + 5);
  }

  return Math.max(30, Math.min(100, finalScore));
}

export class ScannerMappingController {
  public testing = $state(false);
  public traceLogs = $state<string[]>([]);
  public testStatus = $state('Ready');
  public elapsedSeconds = $state(0);
  public batchItems = $state<BatchChannelProgressItem[]>([]);
  public batchProgress = $state({
    total: 0,
    tested: 0,
    online: 0,
    offline: 0,
    percent: 0
  });
  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private elapsedTimer: ReturnType<typeof setInterval> | null = null;
  public epgSources = $state<EPGSource[]>([]);
  public epgChannels = $state<EpgChannelIndexItem[]>([]);
  public loadingEpgChannels = $state(false);
  public savingMapping = $state(false);
  public loadingCandidates = $state(false);
  public savingMerge = $state(false);
  public candidateStreams = $state<ChannelItem[]>([]);
  public personalChannel = $state<PersonalChannel | null>(null);
  public loadingPersonalChannel = $state(false);

  /**
   * Loads personal channel entity including slots and suggestions queue.
   *
   * @param channel Target ChannelItem.
   * @param playlistId Target playlist ID.
   */
  public async loadPersonalChannel(channel: ChannelItem, playlistId = 'default'): Promise<PersonalChannel | null> {
    this.loadingPersonalChannel = true;
    try {
      const channels = await api.getPersonalChannels(playlistId);
      const match = channels.find(
        (pc) => pc.name.toLowerCase() === channel.name.toLowerCase() ||
                pc.slots.some((s) => s.url === channel.url || s.url === channel.original_url)
      );
      this.personalChannel = match || null;
      return this.personalChannel;
    } catch {
      this.personalChannel = null;
      return null;
    } finally {
      this.loadingPersonalChannel = false;
    }
  }

  /**
   * Approves a candidate stream suggestion into the personal channel slot pool.
   *
   * @param suggestionId Target suggestion identifier.
   */
  public async approveSuggestion(suggestionId: string): Promise<boolean> {
    try {
      const updated = await api.approveSuggestion(suggestionId);
      this.personalChannel = updated;
      toastStore.success('Suggestion approved into slot-pool.');
      return true;
    } catch (err: any) {
      toastStore.error(`Failed to approve suggestion: ${err.message}`);
      return false;
    }
  }

  /**
   * Rejects and dismisses a candidate stream suggestion.
   *
   * @param suggestionId Target suggestion identifier.
   */
  public async rejectSuggestion(suggestionId: string): Promise<boolean> {
    try {
      await api.rejectSuggestion(suggestionId);
      if (this.personalChannel) {
        this.personalChannel.suggestions = (this.personalChannel.suggestions || []).filter((s) => s.id !== suggestionId);
      }
      toastStore.info('Suggestion dismissed.');
      return true;
    } catch (err: any) {
      toastStore.error(`Failed to reject suggestion: ${err.message}`);
      return false;
    }
  }

  /**
   * Initializes batch tracking items and counters.
   */
  public initBatch(channels: ChannelItem[]): void {
    this.batchItems = channels.map((ch) => ({
      ...ch,
      testState: ch.link_status === 'online' ? 'online' : ch.link_status === 'offline' ? 'offline' : 'pending'
    }));
    this.batchProgress = {
      total: channels.length,
      tested: 0,
      online: 0,
      offline: 0,
      percent: 0
    };
    this.testStatus = 'Ready to start batch scan';
    this.elapsedSeconds = 0;
  }

  /**
   * Cleans up running polling timers.
   */
  public cleanupBatch(): void {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
    if (this.elapsedTimer) {
      clearInterval(this.elapsedTimer);
      this.elapsedTimer = null;
    }
  }

  /**
   * Triggers a batch stream link test and continuously monitors live progress.
   */
  public async startBatchTest(channels: ChannelItem[]): Promise<boolean> {
    if (channels.length === 0) return false;
    this.initBatch(channels);
    this.testing = true;
    this.testStatus = `Scanning ${channels.length} stream links...`;

    this.elapsedTimer = setInterval(() => {
      this.elapsedSeconds += 1;
    }, 1000);

    try {
      const items: BatchTestLinkItem[] = channels.map((ch) => ({
        url: ch.url,
        original_url: ch.original_url,
        source: ch.source,
        user_agent: ch.user_agent
      }));

      await api.testLinksBatch({ items });
      toastStore.success(`Batch link scan launched for ${channels.length} channels.`);

      this.pollTimer = setInterval(async () => {
        await this.pollBatchProgress();
      }, 1500);

      return true;
    } catch (err: any) {
      this.testStatus = 'Batch scan failed to start';
      toastStore.error(`Failed to start batch test: ${err.message}`);
      this.testing = false;
      this.cleanupBatch();
      return false;
    }
  }

  /**
   * Polls processed channels to update live status and progress counters.
   */
  private async pollBatchProgress(): Promise<void> {
    try {
      const response: any = await api.getChannels({ limit: 1000 });
      const currentList: ChannelItem[] = Array.isArray(response)
        ? response
        : (response.items || response.channels || []);

      const currentMap = new Map<string, ChannelItem>();
      for (const ch of currentList) {
        currentMap.set(ch.id, ch);
      }

      let onlineCount = 0;
      let offlineCount = 0;

      this.batchItems = this.batchItems.map((item) => {
        const live = currentMap.get(item.id);
        if (live) {
          const status = live.link_status;
          if (status === 'online') onlineCount++;
          if (status === 'offline') offlineCount++;
          return {
            ...item,
            link_status: status,
            testState: status === 'online' ? 'online' : status === 'offline' ? 'offline' : 'pending'
          };
        }
        return item;
      });

      const tested = onlineCount + offlineCount;
      const total = this.batchProgress.total || 1;
      const percent = Math.min(100, Math.round((tested / total) * 100));

      this.batchProgress = {
        total: this.batchProgress.total,
        tested,
        online: onlineCount,
        offline: offlineCount,
        percent
      };

      if (tested >= this.batchProgress.total) {
        this.testing = false;
        this.testStatus = `Scan completed: ${onlineCount} Online, ${offlineCount} Offline`;
        this.cleanupBatch();
      }
    } catch {
      // Non-fatal poll failure
    }
  }

  /**
   * Sends stop signal to background scanner daemon.
   */
  public async stopScanner(): Promise<void> {
    try {
      await api.stopScanner();
      this.testStatus = 'Stop signal sent to scanner';
      this.testing = false;
      this.cleanupBatch();
      toastStore.info('Batch test stopped.');
    } catch (err: any) {
      toastStore.error(`Failed to stop scanner: ${err.message}`);
    }
  }

  /**
   * Searches indexed EPG channels from backend cache by source and query.
   *
   * @param source Target EPG source name.
   * @param search Partial channel name search query.
   * @param limit Max items count limit.
   */
  public async searchEpgChannels(source?: string, search?: string, limit = 100): Promise<EpgChannelIndexItem[]> {
    this.loadingEpgChannels = true;
    try {
      const cleanSource = source && source.trim() ? source.trim() : undefined;
      this.epgChannels = await api.getEpgChannels({ source: cleanSource, search, limit });
      return this.epgChannels;
    } catch {
      this.epgChannels = [];
      return [];
    } finally {
      this.loadingEpgChannels = false;
    }
  }

  /**
   * Executes a deep real-time HTTP link verification for a channel stream.
   *
   * @param channel Target channel item.
   */
  public async runDeepLinkTest(channel: ChannelItem): Promise<void> {
    this.testing = true;
    this.traceLogs = [];
    this.testStatus = 'TEST IN PROGRESS...';

    try {
      const result = await api.testStreamLink({
        url: channel.url,
        original_url: channel.original_url,
        user_agent: channel.user_agent || 'Mozilla/5.0'
      });

      if (Array.isArray(result.trace)) {
        this.traceLogs = result.trace.map((item) => String(item));
      }

      const status = (result.status as string) || 'offline';
      const code = (result.code as number) || 0;
      channel.link_status = (status === 'online' ? 'online' : status === 'offline' ? 'offline' : 'unchecked') as any;
      if (result.cors_supported !== undefined) {
        channel.cors_supported = Boolean(result.cors_supported);
      }
      if (result.needs_proxy !== undefined) {
        channel.needs_proxy = Boolean(result.needs_proxy);
      }
      this.testStatus = `RESULT: ${status.toUpperCase()} (HTTP ${code})`;
      toastStore.info(`Link test completed: ${status.toUpperCase()}`);
    } catch (err: any) {
      this.traceLogs.push(`Error: ${err.message}`);
      this.testStatus = 'CONNECTION FAILED';
      toastStore.error(`Link test failed: ${err.message}`);
    } finally {
      this.testing = false;
    }
  }

  /**
   * Loads available global EPG guide sources.
   */
  public async loadEpgSources(): Promise<void> {
    try {
      this.epgSources = await api.getEpgSources();
    } catch {
      this.epgSources = [];
    }
  }

  /**
   * Saves manual EPG mapping override for a channel.
   *
   * @param payload Mapping parameters object.
   */
  public async saveEpgMapping(payload: EPGMappingPayload): Promise<boolean> {
    this.savingMapping = true;
    try {
      await api.updateChannelEpgMapping(payload);
      toastStore.success(`EPG mapping updated for '${payload.channel_name || 'channel'}'.`);
      return true;
    } catch (err: any) {
      toastStore.error(`Failed to update EPG mapping: ${err.message}`);
      return false;
    } finally {
      this.savingMapping = false;
    }
  }

  /**
   * Loads discovered alternative candidate streams for a channel from duplicate clusters.
   *
   * @param channel Target channel item.
   * @returns Array of matching candidate channels excluding the active channel itself.
   */
  public async loadCandidateMatches(channel: ChannelItem): Promise<ChannelItem[]> {
    this.loadingCandidates = true;
    try {
      const clusters = await api.getClusters(0.8);
      const found = clusters.find((c) =>
        c.candidates.some((cand) => cand.original_url === channel.original_url && cand.source === channel.source)
      );
      if (found) {
        this.candidateStreams = found.candidates.filter(
          (cand) => !(cand.original_url === channel.original_url && cand.source === channel.source)
        );
      } else {
        this.candidateStreams = [];
      }
      return this.candidateStreams;
    } catch {
      this.candidateStreams = [];
      return [];
    } finally {
      this.loadingCandidates = false;
    }
  }

  /**
   * Applies master channel failover merge configuration.
   *
   * @param payload ApplyMergePayload object.
   */
  public async applyMerge(payload: ApplyMergePayload): Promise<boolean> {
    this.savingMerge = true;
    try {
      await api.applyMerge(payload);
      toastStore.success(`Failover backup chain updated for '${payload.master_name}'.`);
      return true;
    } catch (err: any) {
      toastStore.error(`Failed to save merge: ${err.message}`);
      return false;
    } finally {
      this.savingMerge = false;
    }
  }

  /**
   * Deletes a master channel failover configuration.
   *
   * @param masterName Master channel display name.
   */
  public async deleteMerge(masterName: string): Promise<boolean> {
    this.savingMerge = true;
    try {
      await api.deleteMerge(masterName);
      toastStore.info(`Unmerged '${masterName}'.`);
      return true;
    } catch (err: any) {
      toastStore.error(`Failed to unmerge: ${err.message}`);
      return false;
    } finally {
      this.savingMerge = false;
    }
  }
}
