import type { ChannelItem, StreamRef, ApplyMergePayload, CandidateCluster } from '$lib/api/types';

export type { CandidateCluster };
import type { StreamStatusUpdateEvent } from '$lib/components/player/VideoPlayerStore';
import { updateChannelStreamStatus } from '../utils/ChannelsUtils';

export interface StagedMergeState {
  masterName: string;
  primaryStream: StreamRef;
  backupStreams: StreamRef[];
  logo?: string;
  group?: string;
  epgId?: string;
}

/**
 * Factory constructing initial staged merge state from a CandidateCluster.
 *
 * @param cluster Target candidate cluster.
 * @returns Initialized StagedMergeState snapshot.
 */
export function createInitialStagedState(cluster?: CandidateCluster | null): StagedMergeState {
  if (!cluster || !cluster.candidates || cluster.candidates.length === 0) {
    return {
      masterName: '',
      primaryStream: { url: '', source: '' },
      backupStreams: []
    };
  }

  if ((cluster.is_merged || cluster.status === 'merged') && cluster.merged_details) {
    return {
      masterName: cluster.merged_details.name || cluster.canonical_name,
      primaryStream: { ...cluster.merged_details.primary_stream },
      backupStreams: cluster.merged_details.backup_streams ? [...cluster.merged_details.backup_streams] : [],
      logo: cluster.merged_details.logo || undefined,
      group: cluster.merged_details.group || undefined,
      epgId: cluster.merged_details.epg_id || undefined
    };
  }

  const firstCand = cluster.candidates[0];
  return {
    masterName: cluster.canonical_name,
    primaryStream: {
      url: firstCand.original_url,
      source: firstCand.source,
      user_agent: firstCand.user_agent
    },
    backupStreams: cluster.candidates.slice(1).map((c) => ({
      url: c.original_url,
      source: c.source,
      user_agent: c.user_agent
    })),
    logo: firstCand.logo,
    group: firstCand.group,
    epgId: firstCand.epg_id
  };
}

/**
 * Generates a unique key string for a candidate channel item using candidate_id or url + source.
 *
 * @param cand Candidate channel item.
 * @returns Composite unique string key.
 */
export function getCandidateKey(cand: ChannelItem): string {
  if (cand && cand.candidate_id) return cand.candidate_id;
  if (!cand) return '';
  return cand.id || `${cand.original_url}_${cand.source}`;
}

/**
 * Checks whether two stream references point to the exact same stream (URL + Source).
 *
 * @param a First StreamRef object.
 * @param b Second StreamRef object.
 * @returns True if both URL and Source match.
 */
export function isSameStream(a?: StreamRef | null, b?: StreamRef | null): boolean {
  if (!a || !b) return false;
  return a.url === b.url && a.source === b.source;
}

/**
 * Promotes a candidate stream to primary stream and moves old primary to backup.
 */
export function promoteStreamToPrimary(
  state: StagedMergeState,
  cand: ChannelItem
): StagedMergeState {
  const oldPrimaryStream = state.primaryStream;
  const newRef: StreamRef = {
    url: cand.original_url,
    source: cand.source,
    user_agent: cand.user_agent
  };

  const backupStreams = (state.backupStreams || []).filter((b) => !isSameStream(b, newRef));

  if (oldPrimaryStream && oldPrimaryStream.url && !backupStreams.some((b) => isSameStream(b, oldPrimaryStream))) {
    backupStreams.push(oldPrimaryStream);
  }

  return {
    ...state,
    primaryStream: newRef,
    backupStreams
  };
}

/**
 * Adds a candidate stream to the backup streams list.
 */
export function addStreamToBackup(
  state: StagedMergeState,
  cand: ChannelItem
): StagedMergeState {
  const ref: StreamRef = {
    url: cand.original_url,
    source: cand.source,
    user_agent: cand.user_agent
  };

  const backupStreams = [...(state.backupStreams || [])];
  if (!isSameStream(ref, state.primaryStream) && !backupStreams.some((b) => isSameStream(b, ref))) {
    backupStreams.push(ref);
  }

  return {
    ...state,
    backupStreams
  };
}

/**
 * Removes a stream from the backup streams list.
 */
export function removeStreamFromBackup(
  state: StagedMergeState,
  ref: StreamRef
): StagedMergeState {
  return {
    ...state,
    backupStreams: (state.backupStreams || []).filter((b) => !isSameStream(b, ref))
  };
}

/**
 * Moves a backup stream up or down in priority order.
 */
export function moveBackupStream(
  state: StagedMergeState,
  index: number,
  direction: number
): StagedMergeState {
  const newIndex = index + direction;
  const backupStreams = [...(state.backupStreams || [])];
  if (newIndex >= 0 && newIndex < backupStreams.length) {
    const temp = backupStreams[index];
    backupStreams[index] = backupStreams[newIndex];
    backupStreams[newIndex] = temp;
  }
  return {
    ...state,
    backupStreams
  };
}

/**
 * Filters duplicate clusters by search query and merge status.
 *
 * @param clusters Raw candidate clusters array.
 * @param query Search query string.
 * @param statusFilter Filter mode ('all' | 'unmerged_only' | 'merged_only').
 * @returns Filtered cluster items array.
 */
export function filterClusters(
  clusters: CandidateCluster[],
  query: string,
  statusFilter: string
): CandidateCluster[] {
  const q = (query || '').toLowerCase().trim();
  const status = (statusFilter || 'all').toLowerCase();

  return clusters.filter((c) => {
    const isMerged = Boolean(c.is_merged);
    if (status === 'merged_only' && !isMerged) return false;
    if (status === 'unmerged_only' && isMerged) return false;

    if (q) {
      const matchMaster = c.canonical_name.toLowerCase().includes(q);
      const matchCand = c.candidates.some((cand) => (cand.name || '').toLowerCase().includes(q));
      if (!matchMaster && !matchCand) return false;
    }

    return true;
  });
}

/**
 * Builds ApplyMergePayload from staged merge state and candidates list.
 *
 * @param state Active staged merge state.
 * @param candidates Array of candidate stream channels.
 * @returns Formatted ApplyMergePayload object.
 */
export function buildMergePayload(
  state: StagedMergeState,
  candidates: ChannelItem[]
): ApplyMergePayload | null {
  if (!state || !state.primaryStream || !state.primaryStream.url) {
    const primaryCand = candidates[0];
    if (!primaryCand) return null;
    return {
      master_name: state?.masterName?.trim() || primaryCand.name,
      primary_stream: {
        url: primaryCand.original_url,
        source: primaryCand.source,
        user_agent: primaryCand.user_agent
      },
      backup_streams: candidates.slice(1).map((c) => ({
        url: c.original_url,
        source: c.source,
        user_agent: c.user_agent
      })),
      logo: primaryCand.logo || '',
      group: primaryCand.group || '',
      epg_id: primaryCand.epg_id || ''
    };
  }

  return {
    master_name: state.masterName.trim() || state.primaryStream.url,
    primary_stream: state.primaryStream,
    backup_streams: state.backupStreams || [],
    logo: state.logo || '',
    group: state.group || '',
    epg_id: state.epgId || ''
  };
}

/**
 * Checks whether staged merge state has been modified compared to initial state.
 *
 * @param initial Initial StagedMergeState snapshot.
 * @param current Current active StagedMergeState.
 * @returns True if master name, primary stream, or backup stream chain differs.
 */
export function isStagedStateDirty(
  initial?: StagedMergeState | null,
  current?: StagedMergeState | null
): boolean {
  if (!initial || !current) return false;
  if (initial.masterName.trim() !== current.masterName.trim()) return true;
  if (!isSameStream(initial.primaryStream, current.primaryStream)) return true;

  const initBackups = initial.backupStreams || [];
  const currBackups = current.backupStreams || [];
  if (initBackups.length !== currBackups.length) return true;

  for (let i = 0; i < initBackups.length; i++) {
    if (!isSameStream(initBackups[i], currBackups[i])) return true;
  }
  return false;
}

export interface ClusterStreamUpdateResult {
  updatedClusters: CandidateCluster[];
  updated: boolean;
  targetName: string;
}

/**
 * Updates candidate stream statuses within clusters when a player status event is received.
 *
 * @param clusters Array of CandidateCluster objects.
 * @param event Stream status update event.
 * @returns ClusterStreamUpdateResult with updated clusters, flag, and target candidate name.
 */
export function updateClusterCandidateStreamStatus(
  clusters: CandidateCluster[],
  event: StreamStatusUpdateEvent
): ClusterStreamUpdateResult {
  let anyUpdated = false;
  let targetName = '';

  const updatedClusters = (clusters || []).map((cluster) => {
    const res = updateChannelStreamStatus(cluster.candidates || [], event);
    if (res.updated) {
      anyUpdated = true;
      targetName = res.targetName;
      return {
        ...cluster,
        candidates: res.updatedList
      };
    }
    return cluster;
  });

  return { updatedClusters, updated: anyUpdated, targetName };
}
