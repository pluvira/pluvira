import type {
  HealthStatus,
  SystemStatus,
  GlobalConfig,
  ChannelsResponse,
  ChannelItem,
  ChannelRewritePayload,
  EPGMappingPayload,
  EpgChannelIndexItem,
  EpgProgramItem,
  BulkInclusionPayload,
  BulkGroupPayload,
  BulkUserAgentPayload,
  BulkResetRewritesPayload,
  Source,
  EPGSource,
  ApplyMergePayload,
  CandidateCluster,
  LinkStatusReportPayload,
  TestLinkPayload,
  BatchTestLinkPayload,
  HistoryRecord,
  DashboardAnalytics,
  SchedulePayload,
  ChannelSearchPayload,
  EpgSearchPayload,
  MergeStatsResponse,
  TestNotificationResponse,
  LicenseResponse,
  BackupValidationResult,
  BackupImportPayload,
  BackupImportResult,
  PlaylistItem,
  CreatePlaylistPayload,
  UpdatePlaylistPayload,
  RegenerateTokenResponse,
  TrialActivationResponse,
  LicenseActivationResponse,
  PersonalChannel,
  ChannelSlot,
  BookmarkPayload,
  BookmarkResponse,
  ReorderSlotsPayload,
  PurgeQuarantinedPayload,
  PurgeQuarantinedResponse,
  UpdateProgressDTO,
  FactoryResetResponse,
  CloudPairingStartResponse,
  CloudPairingStatusResponse,
  CloudAccountInfo,
  BulletinListResponse,
  BulletinDismissResponse,
  BulletinReadResponse,
  AutoMapEpgPayload,
  AutoMapEpgResponse,
  CloudBackupLatestDecryptPayload
} from './types';

import { setCachedCloudEndpoints } from '$lib/utils/cloudUrls';

import { getAuthToken, clearAuthToken } from '$lib/utils/preferences';
import { getStreamProxyUrl } from '$lib/utils/streamUtils';
import { connectionStore } from '$lib/stores/connectionStore';

const BASE_URL = '/api/v1';

export class ApiError extends Error {
  public errorCode?: string;

  constructor(public status: number, message: string, errorCode?: string) {
    super(message);
    this.name = 'ApiError';
    this.errorCode = errorCode;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const token = getAuthToken();

  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...(options.headers || {})
  };

  try {
    const response = await fetch(url, { ...options, headers });

    if (!response.ok) {
      let extractedError = `HTTP Error ${response.status}`;
      let extractedCode: string | undefined;
      try {
        const errData = await response.json();
        if (errData.code) {
          extractedCode = String(errData.code);
        }
        if (errData.detail) {
          extractedError = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
        }
      } catch {
        // Ignore non-JSON parsing errors
      }

      if (response.status >= 500) {
        connectionStore.setConnected(false, {
          errorMessage: extractedError,
          statusCode: response.status,
          failedUrl: url
        });
      }

      if (response.status === 401) {
        clearAuthToken();
        if (typeof window !== 'undefined') {
          window.location.hash = '#/login';
        }
        throw new ApiError(401, 'Unauthorized. Session expired, please login again.');
      }

      throw new ApiError(response.status, extractedError, extractedCode);
    }

    connectionStore.setConnected(true);

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    connectionStore.setConnected(false, {
      errorMessage: error instanceof Error ? error.message : 'Network error',
      statusCode: 0,
      failedUrl: url
    });
    throw error;
  }
}

function createSourceCrudApi<T>(basePath: string) {
  return {
    getAll: () => request<T[]>(basePath),
    create: (item: T) => request<T>(basePath, { method: 'POST', body: JSON.stringify(item) }),
    toggle: (name: string) => request<Record<string, unknown>>(`${basePath}/${encodeURIComponent(name)}/toggle`, { method: 'PATCH' }),
    delete: (name: string) => request<{ message: string }>(`${basePath}/${encodeURIComponent(name)}`, { method: 'DELETE' }),
    bulkStatus: (payload: { names: string[]; action: 'enable' | 'disable' | 'toggle' }) => request<{ message: string }>(`${basePath}/bulk/status`, { method: 'POST', body: JSON.stringify(payload) }),
    bulkDelete: (payload: { names: string[] }) => request<{ message: string }>(`${basePath}/bulk/delete`, { method: 'POST', body: JSON.stringify(payload) }),
    bulkUserAgent: (payload: { names: string[]; user_agent: string }) => request<{ message: string }>(`${basePath}/bulk/user-agent`, { method: 'POST', body: JSON.stringify(payload) }),
    bulkReorder: (payload: { names: string[] }) => request<{ message: string }>(`${basePath}/bulk/reorder`, { method: 'POST', body: JSON.stringify(payload) }),
    bulkRefresh: (payload: { names: string[] }) => request<{ message: string }>(`${basePath}/bulk/refresh`, { method: 'POST', body: JSON.stringify(payload) })
  };
}

const iptvSourcesApi = createSourceCrudApi<Source>('/sources');
const epgSourcesApi = createSourceCrudApi<EPGSource>('/epg/sources');

export const api = {
  // Auth & Session
  login: (username: string, password: string) => request<{ access_token: string; token_type: string; expires_in: number }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password })
  }),
  getAuthStatus: () => request<{ username: string; authenticated: boolean; auth_enabled: boolean }>('/auth/me'),

  // Health & System
  getHealth: () => request<HealthStatus>('/health'),
  getSystemStatus: async () => {
    const status = await request<SystemStatus>('/system/status');
    if (status?.cloud_endpoints) {
      setCachedCloudEndpoints(status.cloud_endpoints);
    }
    return status;
  },
  factoryReset: () => request<FactoryResetResponse>('/system/factory-reset', { method: 'POST' }),
  getUpdateProgress: () => request<UpdateProgressDTO>('/system/update/progress'),
  getLicense: () => request<LicenseResponse>('/system/license'),
  activateLicenseToken: (token: string) => request<LicenseActivationResponse>('/system/license/activate', {
    method: 'POST',
    body: JSON.stringify({ token })
  }),
  refreshLicenseStatus: () => request<LicenseResponse>('/system/license'),
  activateTrial: (token?: string) => request<TrialActivationResponse>('/system/license/trial', {
    method: 'POST',
    body: JSON.stringify({ token: token || '' })
  }),
  syncCloudLicense: () => request<LicenseActivationResponse>('/cloud/sync-license', { method: 'POST' }),
  triggerUpdate: (mode = 'full') => request<{ message: string }>('/system/update', { method: 'POST', body: JSON.stringify({ mode }) }),
  getSystemLogs: (maxItems = 100) => request<string[]>(`/system/logs?max_items=${maxItems}`),
  clearCache: () => request<{ message: string }>('/system/cache/clear', { method: 'POST' }),

  // Configuration
  getConfig: () => request<GlobalConfig>('/config'),
  updateConfig: (config: GlobalConfig) => request<GlobalConfig>('/config', { method: 'PUT', body: JSON.stringify(config) }),
  applyNotificationPreset: (name: string) => request<Record<string, unknown>>('/config/notifications/preset', { method: 'POST', body: JSON.stringify({ name }) }),
  testNotification: (title?: string, body?: string, targetUrl?: string) => request<TestNotificationResponse>('/config/notifications/test', {
    method: 'POST',
    body: JSON.stringify({
      title: title || '🔔 Pluvira: Test Notification',
      body: body || 'Test notification message dispatched from Settings panel.',
      ...(targetUrl ? { target_url: targetUrl } : {})
    })
  }),

  // Channels
  getChannels: (payload: ChannelSearchPayload | Record<string, unknown> = {}) => request<ChannelsResponse>('/channels/search', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  getChannelById: (id: string) => request<ChannelItem>(`/channels/${id}`),
  updateChannelRewrite: (payload: ChannelRewritePayload) => request<{ message: string }>('/channels/rewrite', { method: 'PUT', body: JSON.stringify(payload) }),
  updateChannelEpgMapping: (payload: EPGMappingPayload) => request<{ message: string }>('/channels/epg-mapping', { method: 'PUT', body: JSON.stringify(payload) }),
  bulkSetInclusion: (payload: BulkInclusionPayload) => request<{ message: string }>('/channels/bulk/inclusion', { method: 'POST', body: JSON.stringify(payload) }),
  bulkSetGroup: (payload: BulkGroupPayload) => request<{ message: string }>('/channels/bulk/group', { method: 'POST', body: JSON.stringify(payload) }),
  bulkSetUserAgent: (payload: BulkUserAgentPayload) => request<{ message: string }>('/channels/bulk/user-agent', { method: 'POST', body: JSON.stringify(payload) }),
  bulkResetRewrites: (payload: BulkResetRewritesPayload) => request<{ message: string }>('/channels/bulk/reset-rewrites', { method: 'POST', body: JSON.stringify(payload) }),
  autoMapEpg: (payload: AutoMapEpgPayload) => request<AutoMapEpgResponse>('/channels/auto-map-epg', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),

  // Sources
  getSources: iptvSourcesApi.getAll,
  createSource: iptvSourcesApi.create,
  toggleSource: iptvSourcesApi.toggle,
  deleteSource: iptvSourcesApi.delete,
  bulkSetSourceStatus: iptvSourcesApi.bulkStatus,
  bulkDeleteSources: iptvSourcesApi.bulkDelete,
  bulkSetSourceUa: iptvSourcesApi.bulkUserAgent,
  bulkReorderSources: iptvSourcesApi.bulkReorder,
  bulkRefreshSources: iptvSourcesApi.bulkRefresh,

  // EPG Sources & Programmes
  getEpgSources: epgSourcesApi.getAll,
  createEpgSource: epgSourcesApi.create,
  toggleEpgSource: epgSourcesApi.toggle,
  deleteEpgSource: epgSourcesApi.delete,
  bulkSetEpgSourceStatus: epgSourcesApi.bulkStatus,
  bulkDeleteEpgSources: epgSourcesApi.bulkDelete,
  bulkSetEpgSourceUa: epgSourcesApi.bulkUserAgent,
  bulkReorderEpgSources: epgSourcesApi.bulkReorder,
  bulkRefreshEpgSources: epgSourcesApi.bulkRefresh,
  getEpgChannels: (params: { source?: string; search?: string; limit?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.source) q.set('source', params.source);
    if (params.search) q.set('search', params.search);
    if (params.limit) q.set('limit', String(params.limit));
    const qs = q.toString() ? `?${q.toString()}` : '';
    return request<EpgChannelIndexItem[]>(`/epg/channels${qs}`);
  },
  getEpgProgrammes: (payload: EpgSearchPayload) => {
    const cleanIds = (payload.ids || []).filter((id) => Boolean(id && String(id).trim()));
    if (cleanIds.length === 0) return Promise.resolve({});
    return request<Record<string, EpgProgramItem[]>>('/epg/programmes/search', {
      method: 'POST',
      body: JSON.stringify({ ...payload, ids: cleanIds })
    });
  },

  // Merge & Failover
  getClusters: (similarityThreshold = 0.8) => request<CandidateCluster[]>('/merge/clusters/search', {
    method: 'POST',
    body: JSON.stringify({ similarity_threshold: similarityThreshold })
  }),
  applyMerge: (payload: ApplyMergePayload) => request<{ message: string }>('/merge/apply', { method: 'POST', body: JSON.stringify(payload) }),
  deleteMerge: (masterName: string) => request<{ message: string }>(`/merge/${encodeURIComponent(masterName)}`, { method: 'DELETE' }),
  bulkApplyMerge: (items: ApplyMergePayload[]) => request<{ message: string; count: number }>('/merge/bulk/apply', { method: 'POST', body: JSON.stringify(items) }),
  bulkDeleteMerge: (masterNames: string[]) => request<{ message: string; count: number }>('/merge/bulk/delete', { method: 'POST', body: JSON.stringify({ master_names: masterNames }) }),
  autoApplyMerge: (similarityThreshold = 0.95) => request<{ message: string; merged_count: number }>('/merge/auto-apply', {
    method: 'POST',
    body: JSON.stringify({ similarity_threshold: similarityThreshold })
  }),
  getMergeStats: (similarityThreshold = 0.8) => request<MergeStatsResponse>(`/merge/stats?similarity_threshold=${similarityThreshold}`),

  // Stream Proxy
  getStreamProxyUrl,

  // Scanner
  testStreamLink: (payload: TestLinkPayload) => request<Record<string, unknown>>('/scanner/test-link', { method: 'POST', body: JSON.stringify(payload) }),
  reportStreamStatus: (payload: LinkStatusReportPayload) => request<Record<string, unknown>>('/scanner/report-status', { method: 'POST', body: JSON.stringify(payload) }),
  testLinksBatch: (payload: BatchTestLinkPayload) => request<{ message: string }>('/scanner/test-links-batch', { method: 'POST', body: JSON.stringify(payload) }),
  stopScanner: () => request<{ message: string }>('/scanner/stop', { method: 'POST' }),
  resetScanner: () => request<{ message: string }>('/scanner/reset', { method: 'POST' }),

  // History
  getHistory: () => request<HistoryRecord[]>('/history'),
  deleteHistoryRecord: (recordId: string) => request<{ message: string }>(`/history/${recordId}`, { method: 'DELETE' }),
  clearHistory: () => request<{ message: string }>('/history', { method: 'DELETE' }),

  // Analytics
  getDashboardAnalytics: () => request<DashboardAnalytics>('/analytics/dashboard'),

  // Scheduler
  getSchedule: () => request<SchedulePayload>('/scheduler'),
  updateSchedule: (payload: SchedulePayload) => request<SchedulePayload>('/scheduler', { method: 'PUT', body: JSON.stringify(payload) }),
  restoreDefaultSchedulerJobs: (mode: 'missing_only' | 'full_reset' = 'missing_only') =>
    request<SchedulePayload>(`/scheduler/restore-defaults?mode=${encodeURIComponent(mode)}`, { method: 'POST' }),

  // Backup & Restore
  getCloudSnapshots: () => request<import('./types').CloudBackupSnapshot[]>('/cloud/backup/snapshots'),
  createAndUploadCloudSnapshot: (payload: import('./types').CloudBackupCreateUploadPayload) => request<import('./types').CloudBackupUploadResponse>('/cloud/backup/create-and-upload', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  downloadAndDecryptCloudSnapshot: (payload: import('./types').CloudBackupDecryptPayload) => request<import('./types').BackupBundle>('/cloud/backup/download-and-decrypt', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  uploadCloudSnapshot: (payload: import('./types').CloudBackupUploadPayload) => request<import('./types').CloudBackupUploadResponse>('/cloud/backup/upload', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  downloadCloudSnapshot: (id: string) => request<{ id: string; encrypted_blob: string }>(`/cloud/backup/download/${encodeURIComponent(id)}`),
  deleteCloudSnapshot: (id: string) => request<{ message: string }>(`/cloud/backup/${encodeURIComponent(id)}`, {
    method: 'DELETE'
  }),
  pinCloudBackupSnapshot: (id: string, isPinned: boolean) => request<import('./types').CloudBackupSnapshot>(`/cloud/backup/${encodeURIComponent(id)}/pin`, {
    method: 'PATCH',
    body: JSON.stringify({ is_pinned: isPinned })
  }),
  downloadLatestCloudBackupSnapshot: () => request<import('./types').CloudBackupSnapshot>('/cloud/backup/download/latest'),
  downloadLatestAndDecryptCloudBackup: (payload: CloudBackupLatestDecryptPayload) => request<import('./types').BackupBundle>('/cloud/backup/download-latest-and-decrypt', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  exportBackup: async (sanitized = false) => {
    const token = getAuthToken();
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${BASE_URL}/backup/export?sanitized=${sanitized}`, { headers });
    if (!res.ok) throw new ApiError(res.status, 'Failed to export backup bundle');

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pluvira_backup_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  },
  validateBackup: (payload: BackupImportPayload) => request<BackupValidationResult>('/backup/validate', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  importBackup: (payload: BackupImportPayload) => request<BackupImportResult>('/backup/import', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),

  // Curated Playlists & Personal Channels
  getPlaylists: () => request<PlaylistItem[]>('/playlists'),
  createPlaylist: (payload: CreatePlaylistPayload) => request<PlaylistItem>('/playlists', { method: 'POST', body: JSON.stringify(payload) }),
  updatePlaylist: (id: string, payload: UpdatePlaylistPayload) => request<PlaylistItem>(`/playlists/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deletePlaylist: (id: string) => request<{ message: string }>(`/playlists/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  regeneratePlaylistToken: (id: string) => request<RegenerateTokenResponse>(`/playlists/${encodeURIComponent(id)}/regenerate-token`, { method: 'POST' }),

  getPersonalChannels: (playlistId = 'default') => request<PersonalChannel[]>(`/personal-channels?playlist_id=${encodeURIComponent(playlistId)}`),
  bookmarkChannel: (payload: BookmarkPayload) => request<BookmarkResponse>('/personal-channels/bookmark', { method: 'POST', body: JSON.stringify(payload) }),
  addChannelSlot: (channelId: string, slot: Partial<ChannelSlot>) => request<PersonalChannel>(`/personal-channels/${encodeURIComponent(channelId)}/slots`, { method: 'POST', body: JSON.stringify(slot) }),
  deleteChannelSlot: (channelId: string, slotId: string) => request<PersonalChannel>(`/personal-channels/${encodeURIComponent(channelId)}/slots/${encodeURIComponent(slotId)}`, { method: 'DELETE' }),
  reorderChannelSlots: (channelId: string, payload: ReorderSlotsPayload) => request<PersonalChannel>(`/personal-channels/${encodeURIComponent(channelId)}/slots/reorder`, { method: 'POST', body: JSON.stringify(payload) }),
  approveSuggestion: (suggestionId: string) => request<PersonalChannel>(`/personal-channels/suggestions/${encodeURIComponent(suggestionId)}/approve`, { method: 'POST' }),
  rejectSuggestion: (suggestionId: string) => request<{ message: string }>(`/personal-channels/suggestions/${encodeURIComponent(suggestionId)}/reject`, { method: 'POST' }),
  purgeQuarantined: (payload: PurgeQuarantinedPayload = {}) => request<PurgeQuarantinedResponse>('/personal-channels/purge-quarantined', { method: 'POST', body: JSON.stringify(payload) }),

  // Cloud Pairing & Identity (RFC 8628)
  startCloudPairing: () => request<CloudPairingStartResponse>('/cloud/pairing/start', { method: 'POST' }),
  getCloudPairingStatus: () => request<CloudPairingStatusResponse>('/cloud/pairing/status'),
  cancelCloudPairing: () => request<{ message: string }>('/cloud/pairing/cancel', { method: 'POST' }),
  getCloudAccount: () => request<CloudAccountInfo>('/cloud/account'),
  unlinkCloudAccount: () => request<{ message: string }>('/cloud/account', { method: 'DELETE' }),

  // System Bulletins
  getBulletins: (includeDismissed = false) => request<BulletinListResponse>(`/system/bulletins?include_dismissed=${includeDismissed}`),
  dismissBulletin: (id: string) => request<BulletinDismissResponse>(`/system/bulletins/${encodeURIComponent(id)}/dismiss`, { method: 'POST' }),
  markBulletinRead: (id: string) => request<BulletinReadResponse>(`/system/bulletins/${encodeURIComponent(id)}/read`, { method: 'POST' }),
  deleteBulletin: (id: string) => request<{ id: string; deleted: boolean; message: string }>(`/system/bulletins/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  clearArchivedBulletins: () => request<{ success: boolean; deleted_count: number; message: string }>('/system/bulletins', { method: 'DELETE' })
};
