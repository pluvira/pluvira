import { api } from '$lib/api/client';
import type { ChannelItem } from '$lib/api/types';
import { toastStore } from '$lib/stores/toastStore';
import type { StreamStatusUpdateEvent } from '$lib/components/player/VideoPlayerStore';
import { getPreference, setPreference } from '$lib/utils/preferences';
import {
  filterClusters,
  buildMergePayload,
  getCandidateKey,
  updateClusterCandidateStreamStatus,
  type CandidateCluster,
  type StagedMergeState
} from './MergeUtils';
import type { MergeStatsResponse } from '$lib/api/types';

export class MergeController {
  public loading = $state(false);
  public similarityThreshold = $state(getPreference('mg_threshold', 0.85));
  public searchQuery = $state(getPreference('mg_search', ''));
  public clusterStatusFilter = $state(getPreference('mg_status_filter', 'all'));

  public allClusters = $state<CandidateCluster[]>([]);
  public filteredClusters = $state<CandidateCluster[]>([]);
  public selectedCluster = $state<CandidateCluster | null>(null);
  public stats = $state<MergeStatsResponse | null>(null);

  /**
   * Fetches candidate duplicate clusters from API.
   */
  public async loadClusters(): Promise<void> {
    this.loading = true;
    try {
      const rawClusters = await api.getClusters(this.similarityThreshold);
      const rawList = (rawClusters as CandidateCluster[]) || [];

      this.allClusters = rawList.map((cluster) => {
        const seen = new Set<string>();
        const uniqueCands: ChannelItem[] = [];

        (cluster.candidates || []).forEach((cand: ChannelItem) => {
          const key = getCandidateKey(cand);
          if (!seen.has(key)) {
            seen.add(key);
            uniqueCands.push(cand);
          }
        });

        return {
          ...cluster,
          is_merged: Boolean(cluster.is_merged || cluster.status === 'merged'),
          status: cluster.status || (cluster.is_merged ? 'merged' : 'suggested'),
          merged_details: cluster.merged_details || null,
          candidates: uniqueCands.map((c) => ({
            ...c,
            candidate_id: c.candidate_id || `${c.original_url}_${c.source}`
          }))
        };
      });

      this.applyFilters();

      if (this.selectedCluster) {
        const id = this.selectedCluster.cluster_id;
        this.selectedCluster = this.filteredClusters.find((c) => c.cluster_id === id) || this.filteredClusters[0] || null;
      } else if (this.filteredClusters.length > 0) {
        this.selectedCluster = this.filteredClusters[0];
      }

      await this.loadStats();
    } catch (err: any) {
      toastStore.error(`Failed to load merge clusters: ${err.message}`);
    } finally {
      this.loading = false;
    }
  }

  /**
   * Fetches aggregate cluster merge statistics from API.
   */
  public async loadStats(): Promise<void> {
    try {
      this.stats = await api.getMergeStats(this.similarityThreshold);
    } catch {
      this.stats = null;
    }
  }

  /**
   * Updates similarity threshold enforcing Pro/Core minimum boundaries.
   */
  public setThreshold(val: number, isPro = false): void {
    const minAllowed = isPro ? 0.5 : 0.85;
    this.similarityThreshold = Math.max(minAllowed, Math.min(1.0, val));
    setPreference('mg_threshold', this.similarityThreshold);
  }

  /**
   * Executes automatic server-side merge for clusters exceeding 95% similarity threshold.
   */
  public async autoMergeAll(isPro = true): Promise<void> {
    if (!isPro) {
      toastStore.warning('Auto-merge requires Pluvira Pro edition.');
      return;
    }
    this.loading = true;
    try {
      const res = await api.autoApplyMerge(0.95);
      toastStore.success(`Auto-merged ${res.merged_count || 0} cluster(s) automatically.`);
      await this.loadClusters();
    } catch (err: any) {
      toastStore.error(`Auto-merge failed: ${err.message}`);
    } finally {
      this.loading = false;
    }
  }

  /**
   * Unmerges all active master channels in a single bulk transaction.
   */
  public async bulkUnmergeAll(): Promise<void> {
    const mergedMasterNames = this.allClusters
      .filter((c) => c.is_merged)
      .map((c) => c.canonical_name);

    if (mergedMasterNames.length === 0) return;

    this.loading = true;
    try {
      const res = await api.bulkDeleteMerge(mergedMasterNames);
      toastStore.info(`Unmerged ${res.count || 0} master channel(s).`);
      await this.loadClusters();
    } catch (err: any) {
      toastStore.error(`Bulk unmerge failed: ${err.message}`);
    } finally {
      this.loading = false;
    }
  }

  /**
   * Applies active filter configuration to update filteredClusters and persists preferences.
   */
  public applyFilters(): void {
    this.filteredClusters = filterClusters(
      this.allClusters,
      this.searchQuery,
      this.clusterStatusFilter
    );

    if (this.selectedCluster) {
      const id = this.selectedCluster.cluster_id;
      const match = this.filteredClusters.find((c) => c.cluster_id === id);
      this.selectedCluster = match || this.filteredClusters[0] || null;
    } else if (this.filteredClusters.length > 0) {
      this.selectedCluster = this.filteredClusters[0];
    } else {
      this.selectedCluster = null;
    }

    setPreference('mg_search', this.searchQuery || '');
    setPreference('mg_status_filter', this.clusterStatusFilter || 'all');
    setPreference('mg_threshold', this.similarityThreshold);
  }

  /**
   * Applies a master channel merge configuration via API.
   *
   * @param state Staged merge state.
   * @param candidates Array of candidate channels in cluster.
   */
  public async applyMerge(state: StagedMergeState, candidates: ChannelItem[]): Promise<boolean> {
    const payload = buildMergePayload(state, candidates);
    if (!payload) return false;

    this.loading = true;
    try {
      await api.applyMerge(payload);
      toastStore.success(`Channel merge applied for '${payload.master_name}'.`);
      await this.loadClusters();
      return true;
    } catch (err: any) {
      toastStore.error(`Failed to apply merge: ${err.message}`);
      return false;
    } finally {
      this.loading = false;
    }
  }

  /**
   * Removes a master channel merge configuration via API.
   *
   * @param masterName Master channel display name key to unmerge.
   */
  public async unmerge(masterName: string): Promise<boolean> {
    this.loading = true;
    try {
      await api.deleteMerge(masterName);
      toastStore.info(`Unmerged '${masterName}'.`);
      await this.loadClusters();
      return true;
    } catch (err: any) {
      toastStore.error(`Failed to unmerge: ${err.message}`);
      return false;
    } finally {
      this.loading = false;
    }
  }

  /**
   * Updates candidate channel stream link and CORS status reactively in active clusters.
   *
   * @param event Stream status update event from video player.
   */
  public handleStreamStatusUpdate(event: StreamStatusUpdateEvent): void {
    const res = updateClusterCandidateStreamStatus(this.allClusters, event);
    if (res.updated) {
      this.allClusters = res.updatedClusters;
      this.applyFilters();
      if (event.link_status === 'offline' && event.errorCode) {
        toastStore.warning(`Candidate Stream KO (${res.targetName || 'Channel'}): ${event.errorCode}`);
      }
    }
  }
}
