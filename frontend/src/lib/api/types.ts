/**
 * TypeScript API v1 Interface definitions matching FastAPI OpenAPI 3.1 schema.
 */

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  git_hash?: string | null;
}

export interface EnvironmentInfo {
  version: string;
  git_hash: string | null;
  config_path: string;
  data_dir: string;
  temp_dir: string;
}

export type EditionType = 'core' | 'pro';
export type LicenseStatusType = 'valid' | 'expiring_soon' | 'grace_period' | 'expired' | 'missing' | 'unlicensed';

export interface LicenseDetails {
  valid: boolean;
  status: string;
  error_code: string | null;
  message: string;
  license_status: LicenseStatusType;
  tier?: string;
  display_name_full?: string | null;
  compact_name?: string | null;
  badge_icon?: string | null;
  badge_color?: string | null;
  badge_text_color?: string | null;
  max_ips?: number | null;
  max_slots?: number | null;
  backup_max_slots?: number | null;
  days_remaining: number | null;
  expires_at: number | null;
  modules: string[];
  subject: string | null;
  is_cached: boolean;
  trial?: boolean;
  is_trial?: boolean;
  trial_days_remaining?: number | null;
  update_recommended?: boolean;
  pro_version?: string;
  crockford_id?: string | null;
  managed_by_env?: boolean;
  cloud_account_linked?: boolean;
  has_claimed_trial?: boolean;
  grace_hours_remaining?: number | null;
}

export interface LicenseResponse {
  edition: EditionType;
  tier?: string;
  pro_binary_found: boolean;
  pro_active: boolean;
  license_valid: boolean;
  license: LicenseDetails;
  message: string;
}

export interface SystemStatus {
  is_running: boolean;
  status: string;
  mode?: string;
  edition?: EditionType;
  tier?: string;
  display_name_full?: string | null;
  compact_name?: string | null;
  badge_icon?: string | null;
  badge_color?: string | null;
  badge_text_color?: string | null;
  max_ips?: number | null;
  pro_active?: boolean;
  license_valid?: boolean;
  license?: LicenseDetails | null;
  edition_message?: string;
  webrtc_active?: boolean;
  webrtc_status?: 'connected' | 'standby' | 'disabled' | 'error';
  cloud_endpoints?: Record<string, string>;
  environment?: EnvironmentInfo;
  pro_version?: string;
  crockford_id?: string | null;
  device_hash?: string | null;
  supported_commands?: string[];
  supported_modules?: string[];
}

export interface FilePermissions {
  mode?: string;
  owner?: string;
  group?: string;
}

export interface FilterRule {
  field: string;
  regex: string;
}

export interface Filters {
  allow?: FilterRule[];
  deny?: FilterRule[];
}

export interface LinkTestSettings {
  min_delay?: number;
  max_delay?: number;
}

export interface MdnsConfig {
  enabled?: boolean;
  service_type?: string;
}

export interface SearchMethodsConfig {
  method_a?: boolean;
  method_b?: boolean;
  method_c?: boolean;
  method_d?: boolean;
}

export interface EpgProgramItem {
  s: string;
  e: string;
  t: string;
  d?: string;
}

export interface NotificationEventConfig {
  update_success?: boolean;
  update_failure?: boolean;
  link_test_report?: boolean;
  link_ko_detected?: boolean;
  disk_space_warning?: boolean;
  source_download_failure?: boolean;
  source_empty_malformed?: boolean;
  partial_acquisition?: boolean;
  massive_channel_drop?: boolean;
  massive_drop_threshold_pct?: number;
  link_recovered?: boolean;
  source_unhealth_warning?: boolean;
  source_health_threshold_pct?: number;
  suspicious_redirect_detected?: boolean;
  atomic_write_failure?: boolean;
  orphan_lock_recovered?: boolean;
  min_ram_disk_free_mb?: number;
  unmapped_included_warning?: boolean;
  unmapped_included_threshold_pct?: number;
  epg_expiration_warning?: boolean;
  min_epg_future_hours?: number;
  rewrite_conflict_warning?: boolean;
  config_save_failure?: boolean;
  service_lifecycle_event?: boolean;
  epg_source_unused?: boolean;
  slow_processing_warning?: boolean;
  slow_processing_threshold_s?: number;
  scheduled_job_skipped?: boolean;
  duplicate_channel_warning?: boolean;
  m3u_parsing_error?: boolean;
  xmltv_parsing_error?: boolean;
  system_high_load?: boolean;
  cpu_load_threshold_pct?: number;
  temp_threshold_c?: number;
  api_error_500?: boolean;
  link_failover_triggered?: boolean;
}

export interface NotificationSettings {
  enabled?: boolean;
  urls?: string[];
  events?: NotificationEventConfig;
}

export interface RewriteRule {
  field: string;
  pattern?: string;
  replacement: string;
  mode?: 'regex' | 'wildcard' | 'text' | 'replace';
  enabled?: boolean;
  description?: string | null;
}

export interface SourceSettings {
  output_m3u?: string | null;
  output_epg?: string | null;
  temp_dir?: string | null;
  device_name?: string | null;
  mdns?: MdnsConfig | null;
  user_agent?: string | null;
  epg_retention_days?: number | null;
  cache_driver?: string | null;
  cache_ttl_seconds?: number | null;
  file_permissions?: FilePermissions | null;
  rewrites?: RewriteRule[] | null;
  filters?: Filters | null;
  mapping_overrides?: Record<string, string> | null;
  notification_urls?: string[] | null;
  notifications?: NotificationSettings | null;
  allow_channels?: string[] | null;
  deny_channels?: string[] | null;
  link_test_settings?: LinkTestSettings | null;
  search_debounce_ms?: number | null;
  language?: string | null;
  custom_stopwords?: string[] | null;
  search_methods?: SearchMethodsConfig | null;
  force_proxy?: boolean | null;
  onboarding_completed?: boolean | null;
}

export interface StreamRef {
  url: string;
  source: string;
  user_agent?: string | null;
}

export interface ChannelMerge {
  name?: string | null;
  epg_id?: string | null;
  logo?: string | null;
  group?: string | null;
  user_agent?: string | null;
  primary_stream: StreamRef;
  backup_streams?: StreamRef[];
}

export interface Source {
  name: string;
  enabled?: boolean;
  m3u_url: string;
  settings?: SourceSettings | null;
}

export interface EPGSource {
  name: string;
  enabled?: boolean;
  url: string;
  user_agent?: string | null;
}

export interface AuthSettings {
  enabled?: boolean;
  username?: string;
  password?: string;
  secret_key?: string;
  algorithm?: string;
  token_expire_minutes?: number;
}

export interface GlobalConfig {
  settings: SourceSettings;
  auth?: AuthSettings;
  sources?: Source[];
  epg_sources?: EPGSource[];
  channel_merges?: Record<string, ChannelMerge>;
  individual_rewrites?: Record<string, RewriteRule[]>;
}

export interface ChannelItem {
  id: string;
  candidate_id?: string;
  name: string;
  url: string;
  original_url: string;
  group?: string;
  logo?: string;
  user_agent?: string;
  source: string;
  is_included: boolean;
  is_bookmarked?: boolean;
  is_locked?: boolean;
  is_modified?: boolean;
  bookmarked_playlist_ids?: string[];
  epg_id?: string;
  is_mapped: boolean;
  link_status: 'online' | 'offline' | 'unchecked';
  cors_supported?: boolean;
  needs_proxy?: boolean;
  rewrites?: string[];
  backup_streams?: StreamRef[];
  rewrite_details?: Record<string, string[]>;
  original_data?: {
    name: string;
    group: string;
    logo: string;
    url: string;
  };
}

export interface ChannelsResponse {
  total: number;
  limit: number;
  offset: number;
  items: ChannelItem[];
}

export interface ChannelRewritePayload {
  original_url?: string;
  field: 'name' | 'group' | 'logo' | 'url' | 'user_agent';
  original_val?: string;
  new_val: string;
}

export interface EpgChannelIndexItem {
  id: string;
  raw_id: string;
  name: string;
  source: string;
}

export interface EPGMappingPayload {
  channel_name?: string;
  source_name?: string;
  epg_id: string;
  is_global?: boolean;
}

export interface BulkInclusionPayload {
  channel_items: Array<Record<string, unknown>>;
  is_included: boolean;
}

export interface BulkGroupPayload {
  original_urls: string[];
  group: string;
}

export interface BulkUserAgentPayload {
  original_urls: string[];
  user_agent: string;
}

export interface BulkResetRewritesPayload {
  original_urls: string[];
}


export interface SourceStatItem {
  name: string;
  enabled: boolean;
  status: string;
  total_channels: number;
  included_channels: number;
  excluded_channels: number;
  epg_match_included_pct: number;
  epg_match_excluded_pct: number;
  online_links: number;
  offline_links: number;
  unchecked_links: number;
  link_health_pct: number;
}

export interface EpgSourceStatItem {
  name: string;
  enabled: boolean;
  status: string;
  total_epg_channels: number;
  mapped_m3u_channels: number;
  utilization_pct: number;
  total_programmes: number;
  coverage_days: string;
  last_sync_programmes?: number;
  last_sync_duration_s?: number;
  is_turbo?: boolean;
  slow_sync_warning?: boolean;
}

export interface CandidateCluster {
  cluster_id: string;
  canonical_name: string;
  is_merged?: boolean;
  status?: 'merged' | 'suggested';
  merged_details?: ChannelMerge | null;
  candidates: ChannelItem[];
  suggestions?: ChannelSuggestion[];
}

export interface ApplyMergePayload {
  master_name: string;
  primary_stream: StreamRef;
  backup_streams?: StreamRef[];
  logo?: string;
  group?: string;
  epg_id?: string;
}

export interface MergeStatsResponse {
  total_clusters_detected: number;
  total_merged_channels: number;
  total_unmerged_clusters: number;
  total_backup_streams: number;
}

export interface LinkStatusReportPayload {
  original_url: string;
  url?: string;
  source?: string;
  link_status: 'online' | 'offline' | 'unchecked' | 'redirect';
  code?: number;
  cors_supported?: boolean;
  needs_proxy?: boolean;
  error_message?: string;
  health_score?: number;
  latency_ms?: number;
  quarantined?: boolean;
}

export interface TestLinkPayload {
  url: string;
  original_url?: string | null;
  user_agent?: string;
}

export interface BatchTestLinkItem {
  url: string;
  original_url: string;
  source: string;
  user_agent?: string | null;
}

export interface BatchTestLinkPayload {
  items: BatchTestLinkItem[];
}

export interface EpgSourceSyncStats {
  source_name: string;
  channels: number;
  programmes: number;
  duration_s: number;
  engine: string;
}

export interface HistoryRecord {
  id: string;
  timestamp: string;
  mode: string;
  duration: number;
  status: string;
  total_channels: number;
  matched_channels: number;
  missing_channels: number;
  error_message?: string | null;
  is_turbo?: boolean;
  channels_modified?: number;
  turbo_rewrites_duration_s?: number;
  is_turbo_rewrites?: boolean;
  epg_stats?: EpgSourceSyncStats[];
  trigger?: 'manual' | 'scheduled' | string;
}

export interface DashboardAnalytics {
  sources_stats: Array<Record<string, unknown>>;
  global_stats: Record<string, unknown>;
  epg_sources_stats: EpgSourceStatItem[];
}

export interface LinkTestFilters {
  inclusion?: 'included_only' | 'all' | 'excluded_only';
  status_filter?: 'all' | 'ok_only' | 'ko_only' | 'unchecked_only';
  max_channels?: number;
  sources?: string[];
  groups?: string[];
  name_regex?: string;
}

export interface ScheduledJob {
  id?: string;
  enabled?: boolean;
  mode?: string;
  trigger?: string;
  hour?: number | string;
  minute?: number | string;
  day_of_week?: string;
  hours?: number;
  minutes?: number;
  description?: string;
  is_system?: boolean;
  is_recommended?: boolean;
  link_test_filters?: LinkTestFilters;
}

export interface RestoreDefaultsPayload {
  mode?: 'missing_only' | 'full_reset';
}

export interface SchedulePayload {
  enabled?: boolean;
  jobs?: ScheduledJob[];
}

export interface ChannelSearchPayload {
  search?: string;
  source?: string;
  group?: string;
  is_included?: boolean;
  is_mapped?: boolean;
  link_status?: string;
  limit?: number;
  offset?: number;
}

export interface EpgSearchPayload {
  ids: string[];
  date?: string;
  date_from?: string;
  date_to?: string;
}

export interface TestNotificationResponse {
  success: boolean;
  message: string;
  targets_count: number;
}

export interface DiffCategoryCount {
  added: number;
  updated: number;
  removed: number;
}

export interface BackupDiffSummary {
  sources: DiffCategoryCount;
  epg_sources: DiffCategoryCount;
  individual_rewrites: DiffCategoryCount;
  channel_merges: DiffCategoryCount;
  schedule_jobs: DiffCategoryCount;
  settings_modified: string[];
  auth_modified: boolean;
}

export interface BackupScheduleData {
  version: number;
  enabled: boolean;
  jobs: Record<string, any>[];
}

export interface BackupBundle {
  bundle_version: number;
  app_version: string;
  exported_at: string;
  sanitized: boolean;
  config: GlobalConfig;
  schedule: BackupScheduleData;
  sources?: Source[];
  epg_sources?: EPGSource[];
  channel_merges?: Record<string, ChannelMerge>;
  playlists?: PlaylistItem[];
  personal_channels?: PersonalChannel[];
  individual_rewrites?: Record<string, RewriteRule[]>;
  epg_mapping_overrides?: Record<string, any>[];
  source_channel_filters?: Record<string, any>[];
  metadata_rules?: Record<string, any>[];
  notification_settings?: NotificationSettings | null;
  notification_targets?: string[];
}

export interface BackupValidationResult {
  valid: boolean;
  bundle_version: number;
  target_version: number;
  migration_required: boolean;
  sanitized_detected: boolean;
  errors: string[];
  warnings: string[];
  diff: BackupDiffSummary | null;
}

export interface BackupImportPayload {
  bundle: BackupBundle;
  mode: 'destructive' | 'merge';
  trigger_sync?: boolean;
}

export interface BackupImportResult {
  success: boolean;
  mode: 'destructive' | 'merge';
  message: string;
  snapshot_created: boolean;
  diff: BackupDiffSummary | null;
}


export interface PlaylistItem {
  id: string;
  name: string;
  export_token?: string;
  is_default?: boolean;
  created_at?: string;
}

export interface CreatePlaylistPayload {
  id?: string;
  name: string;
}

export interface UpdatePlaylistPayload {
  name?: string;
  export_token?: string;
}

export interface RegenerateTokenResponse {
  token: string;
  message: string;
}

export interface ActivateLicensePayload {
  token: string;
}

export interface LicenseActivationResponse {
  success: boolean;
  message: string;
  license?: LicenseDetails;
  error_code?: string | null;
}

export interface TrialActivationResponse {
  success: boolean;
  message: string;
  license?: LicenseDetails;
}

export interface ChannelSlot {
  id: string;
  personal_channel_id: string;
  slot_index: number;
  url: string;
  source: string;
  user_agent?: string;
  health_score: number;
  is_locked: boolean;
  consecutive_errors?: number;
  quarantined_at?: string | null;
  latency_ms?: number;
  uptime_pct?: number;
}

export interface ChannelSuggestion {
  id: string;
  personal_channel_id: string;
  url: string;
  source: string;
  confidence_score: number;
}

export interface PersonalChannel {
  id: string;
  playlist_id: string;
  name: string;
  logo?: string;
  epg_id?: string;
  group?: string;
  custom_order?: number;
  is_pinned?: boolean;
  is_locked?: boolean;
  slots: ChannelSlot[];
  suggestions?: ChannelSuggestion[];
}

export interface BookmarkPayload {
  playlist_id?: string;
  channel: {
    name: string;
    url: string;
    source: string;
    group?: string;
    logo?: string;
    epg_id?: string;
  };
}

export interface BookmarkResponse {
  bookmarked: boolean;
  channel_id?: string;
}

export interface ReorderSlotsPayload {
  slot_ids: string[];
}

export interface PurgeQuarantinedPayload {
  playlist_id?: string;
}

export interface PurgeQuarantinedResponse {
  purged_count: number;
  message: string;
}

export type UpdateSourceStatus = 'pending' | 'running' | 'success' | 'failed' | 'skipped';

export interface UpdateSourceProgress {
  name: string;
  type: 'm3u' | 'epg';
  status: UpdateSourceStatus;
  channels?: number;
  programmes?: number;
  error?: string | null;
  reason?: string | null;
}

export interface UpdatePhaseProgress {
  title: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  detail?: string | null;
}

export interface UpdateProgressSummary {
  status: 'success' | 'failed';
  duration: number;
  total_channels: number;
  matched_channels: number;
  channels_modified?: number;
  is_turbo_rewrites?: boolean;
  error_message?: string | null;
}

export interface UpdateProgressDTO {
  is_running: boolean;
  mode: string;
  elapsed_seconds: number;
  sources: UpdateSourceProgress[];
  phases: Record<string, UpdatePhaseProgress>;
  summary?: UpdateProgressSummary | null;
}

export interface CloudPairingStartResponse {
  device_code: string;
  user_code: string;
  verification_uri: string;
  verification_uri_complete: string;
  expires_in: number;
  interval: number;
}

export type CloudPairingStatus = 'idle' | 'pending' | 'success' | 'expired' | 'denied' | 'failed';

export interface CloudPairingStatusResponse {
  status: CloudPairingStatus;
  user_code?: string | null;
  verification_uri_complete?: string | null;
  expires_at?: number | null;
  uid?: string | null;
  formatted_id?: string | null;
  error_message?: string | null;
}

export interface CloudAccountInfo {
  uid?: string | null;
  formatted_id?: string | null;
  access_token?: string | null;
  linked_at?: string | null;
  is_linked: boolean;
  device_hash?: string | null;
}

export interface FactoryResetResponse {
  success: boolean;
  message: string;
}

export interface CloudBackupSnapshot {
  id: string;
  size_bytes: number;
  sha256_checksum: string;
  snapshot_label?: string | null;
  created_at: string;
  is_pinned?: boolean;
}

export interface CloudBackupCreateUploadPayload {
  passphrase: string;
  snapshot_label?: string;
  pin_snapshot?: boolean;
}

export interface CloudBackupPinPayload {
  is_pinned: boolean;
}

export interface CloudBackupLatestDecryptPayload {
  passphrase: string;
}

export interface CloudBackupDecryptPayload {
  backup_id: string;
  passphrase: string;
}

export interface CloudBackupUploadPayload {
  encrypted_blob: string;
  sha256_checksum: string;
  snapshot_label?: string;
}

export interface CloudBackupUploadResponse {
  id: string;
  size_bytes: number;
  sha256_checksum: string;
  snapshot_label?: string | null;
  created_at: string;
  message: string;
}

export interface BulletinMediaDTO {
  type: 'image' | 'video' | string;
  url: string;
  sha256: string;
  alt?: string;
}

export type BulletinLevel = 'info' | 'warning' | 'critical' | 'security';

export interface BulletinDTO {
  id: string;
  level: BulletinLevel;
  icon?: string | null;
  title: Record<string, string>;
  message: Record<string, string>;
  action_url?: string | null;
  action_label?: Record<string, string> | null;
  media?: BulletinMediaDTO | null;
  dismissible: boolean;
  priority: number;
  expires_at: number;
  signature?: string | null;
  is_dismissed: boolean;
  dismissed_at?: string | null;
  is_read?: boolean;
  read_at?: string | null;
}

export interface BulletinListResponse {
  bulletins: BulletinDTO[];
  total: number;
  unread_count: number;
}

export interface BulletinDismissResponse {
  id: string;
  is_dismissed: boolean;
  message: string;
}

export interface BulletinReadResponse {
  id: string;
  is_read: boolean;
  message: string;
}

export interface BulletinAckPayload {
  received?: string[];
  read?: string[];
  dismissed?: string[];
}

export interface AutoMapEpgPayload {
  scope: 'curated' | 'all' | string;
  playlist_id?: string;
  similarity_threshold?: number;
  overwrite_existing?: boolean;
  source?: string | null;
  only_unmapped?: boolean;
}

export interface AutoMapEpgOverrideItem {
  channel_name: string;
  source_name: string;
  epg_id: string;
}

export interface AutoMapEpgResponse {
  success: boolean;
  scope: string;
  total_evaluated: number;
  mapped_count: number;
  matched_count?: number;
  skipped_count: number;
  is_pro: boolean;
  message: string;
  applied_overrides?: AutoMapEpgOverrideItem[];
}
