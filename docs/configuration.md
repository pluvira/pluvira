# Configuration Guide

This document explains how to configure `pluvira` using the YAML files located in the `config/` directory.

---

## 1. Application Configuration (`config.yaml`)

The main configuration file, `config.yaml`, is dedicated exclusively to static application settings (`settings`) and authentication credentials (`auth`). All dynamic operational entities—including IPTV M3U sources, XMLTV EPG sources, master channel merges, cascading rewrite rules, manual EPG mapping overrides, channel allow/deny filters, and notification settings—are persisted directly in the relational SQLite database `pluvira_main.db` in WAL mode.

### Configuration Structure Example

```yaml
version: 1
settings:
  output_m3u: "data/pluvira.m3u"
  output_epg: "data/pluvira_epg.xml"
  temp_dir: "/dev/shm/pluvira"
  device_name: "Pluvira"
  user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
  epg_retention_days: 7
  mdns:
    enabled: true
    service_type: "_pluvira._tcp.local."
  file_permissions:
    mode: "0644"
    owner: "ubuntu"
    group: "ubuntu"
  link_test_settings:
    min_delay: 1.5
    max_delay: 3.5
  notifications:
    enabled: true
    urls:
      - "tgram://BOT_TOKEN/CHAT_ID"
    events:
      update_success: true
      update_failure: true
      source_download_failure: true
      source_empty_malformed: true
      partial_acquisition: true
      massive_channel_drop: true
      massive_drop_threshold_pct: 30.0
      link_test_report: true
      link_ko_detected: true
      link_recovered: true
      source_unhealth_warning: true
      source_health_threshold_pct: 70.0
      suspicious_redirect_detected: true
      atomic_write_failure: true
      orphan_lock_recovered: true
      disk_space_warning: true
      min_ram_disk_free_mb: 30.0
      unmapped_included_warning: true
      unmapped_included_threshold_pct: 20.0
      epg_expiration_warning: true
      min_epg_future_hours: 24.0
      rewrite_conflict_warning: true
      config_save_failure: true
      service_lifecycle_event: true
auth:
  enabled: false
  username: "admin"
  password: "admin"
```

---

## 2. Global Settings (`settings`)

The `settings` block defines the default behavior of the application:

* **`output_m3u`**: Path where the processed M3U playlist is exported (managed via environment variables or defaults; abstracted by WebUI export endpoints).
* **`output_epg`**: Path where the processed XMLTV guide is exported (managed via environment variables or defaults; abstracted by WebUI export endpoints).
* **`temp_dir`**: Volatile RAM disk storage directory (`/dev/shm/pluvira`) managed internally to protect host storage media.
* **`device_name`**: Human-readable server instance and local mDNS broadcast hostname (default `"Pluvira"`).
* **`mdns`**: Local mDNS (Zeroconf / RFC 6762) discovery settings (`enabled`: default `true`, `service_type`: default `"_pluvira._tcp.local."`).
* **`user_agent`**: The default User-Agent header used for downloading playlists and EPGs.
* **`epg_retention_days`**: The number of days of EPG data to retain (older programmes are discarded during parsing).
* **`language`**: Primary system language code (`it`, `en`, `es`, `fr`, `de`, `pt`) used for EPG stop-words dictionaries and regional formatting.
* **`custom_stopwords`**: User-defined list of custom stop-words to ignore during intelligent EPG programme searches.
* **`search_methods`**: Dictionary of boolean toggles for active EPG search methodologies (`method_a`: Relevance scoring, `method_b`: Stop-words tokenization, `method_c`: Diacritics/Word-boundary match, `method_d`: Time-aware boost).
* **`sqlite_storage`**: The persistent storage engine uses a consolidated 2-database SQLite architecture in WAL mode (`pluvira_main.db` for core settings, curated playlists, and execution history; `pluvira_epg.db` for raw channel catalog, EPG guides, and stream link health) with zero JSON disk serialization for maximum I/O performance and SSD longevity.
* **`bsl_thresholds`**: Programmatic resource limits enforced in the Personal Free Tier (when no Pro license is active):
  * Ingest catalog cap: max 2,500 total channels in local SQLite database.
  * Curated list cap: max 25 channels active in "My List" (26th channel raises HTTP 403 `PersonalChannelLimitExceeded`).
  * Failover slot-pool: max 2 stream slots per channel (Slot 0 Primary + Slot 1 Backup) vs 7 slots in Pro Tier.
  * Playlist count: max 1 curated playlist ("My List", slug `default`) and max 2 active IPTV M3U sources.
  * Concurrent views: max 2 simultaneous stream views (local client IP leases).
  * Non-destructive trial expiration: channels from position 26 onwards remain stored in `pluvira_main.db` but are omitted from exported M3U playlists until Pro activation.
* **`search_debounce_ms`**: Debounce delay in milliseconds for UI search inputs (default 300ms, range 0-2000ms).
* **`force_proxy`**: Boolean toggle (default `false`) forcing all playback streams through the backend CORS proxy (`/api/v1/stream/proxy`).
* **`onboarding_completed`**: Boolean flag (default `false` on fresh install) tracking completion of the initial Post-Installation Onboarding Wizard.
* **`metadata_providers`**: Configuration for external Rich EPG Metadata enrichment providers:
  * **`tmdb_api_key`**: API key for The Movie Database (TMDb) for cinematic movies and scripted TV series.
  * **`tvdb_api_key`**: API key for TheTVDB.
  * **`trakt_client_id`**: Client ID for Trakt.tv community ratings.
  * **`enable_tvmaze`**: Boolean toggle (default `true`) enabling open TVMaze search fallback.
  * **`enable_wikipedia`**: Boolean toggle (default `true`) enabling Wikipedia REST summary fallback for news, talk shows, and sports.
  * **`metadata_retention_days`**: Cache retention TTL in days for enriched metadata in `pluvira_metadata.db` (default 30 days).
* **`stream_auto_purge`**: Boolean toggle (default `true`) enabling automated removal of expired quarantined streams.
* **`purge_days_threshold`**: Number of days a stream remains in quarantine before automatic deletion (default 7 days).
* **`file_permissions`**: Optional Unix file permissions applied to the exported files.
* **`link_test_settings`**: Configures the polite scanner delays (`min_delay` and `max_delay` in seconds) to prevent IP bans during link testing.
* **`notifications`**: Granular notification system configuration (full 27+ event matrix available in Pro Edition; Core Edition logs basic status events).
  * **`enabled`**: Global boolean toggle.
  * **`urls`**: List of supported webhook and notification service URLs (e.g., Telegram, Discord, Slack).
  * **`events`**: Dictionary of boolean toggles for specific system events (see [Notifications Guide](notifications.md) for details).
  * **Thresholds**:
    * `massive_drop_threshold_pct`: Min % of channel loss to trigger alert.
    * `source_health_threshold_pct`: Min % of healthy links per source.
    * `min_ram_disk_free_mb`: Min MB free on RAM disk before critical alert.
    * `min_epg_future_hours`: Min hours of future EPG coverage required.
* **`notification_urls`**: List of target webhook URLs for notification dispatches.

---

## 3. IPTV Sources (`sources`)

Each source represents an external IPTV provider. Sources are persisted directly in `pluvira_main.db` (`sources` table) via `SourceRepository` and managed through the REST API v1 or WebUI, eliminating YAML file serialization overhead.

* **`name`**: A unique identifier for the source.
* **`enabled`**: Boolean flag (`true`/`false`) to enable or disable this source.
* **`m3u_url`**: The URL or local path (`file://`) of the M3U playlist.

> **Note on Bulk Operations & WebUI**: The REST API provides bulk endpoints (`/api/v1/sources/bulk/*`) to enable, disable, delete, reorder, update User-Agents, and selectively refresh multiple M3U sources simultaneously. In the WebUI, IPTV and EPG sources are managed via sortable `AccordionCard` components with persistent expansion state, including source-specific metadata rewrites and allowed/denied channel accordions.

---

## 4. Global EPG Sources (`epg_sources`)

EPG guide sources are decoupled from M3U playlist sources and managed globally. EPG sources are persisted directly in `pluvira_main.db` (`epg_sources` table) via `SourceRepository` with priority order indexing.

* **`name`**: A unique identifier for the EPG source.
* **`enabled`**: Boolean flag (`true`/`false`) to enable or disable this guide source.
* **`url`**: The URL or local path (`file://`) of the XMLTV guide (supports `.xml` and compressed `.xml.gz` formats).
* **`user_agent`**: Optional custom User-Agent header for downloading this specific guide.
* **Priority Order**: The position of an EPG source in the list defines its automatic matching priority. When a channel matches multiple EPG guides, the source listed earliest takes precedence.

> **Note on Bulk Operations**: The REST API provides bulk endpoints (`/api/v1/epg/sources/bulk/*`) to enable, disable, delete, reorder, update User-Agents, and selectively refresh multiple EPG sources simultaneously.

* **`settings`**: Optional source-specific overrides. If defined, these settings take precedence over global settings for channels belonging to this source.
  * **`force_proxy`**: Optional boolean toggle forcing all streams from this source through the CORS proxy.
  * **`allow_channels` / `deny_channels`**: Channel inclusion and exclusion filters are persisted in `pluvira_main.db` (`source_channel_filters` table) and managed via the WebUI or bulk REST endpoints, eliminating YAML parsing overhead.
  * **`filters`**: Regex-based allow/deny rules applied to channel attributes (e.g., `group-title`).

---

## 5. Cascading Rewrites (`rewrites`)

Rewrite rules allow you to modify channel metadata (Name, Group, Logo, URL, User-Agent) on-the-fly. All rules are persisted directly in SQLite `pluvira_main.db` (`metadata_rules` table for Global and Source tiers, and `individual_rewrites` table for Individual channel rules). Modifying rules applies instant SQLite WAL updates without touching `config.yaml` or requiring a database reload.

### Rewrite Rule Fields

* **`field`**: The target attribute to modify (`name`, `group`, `logo`, `url`, `user_agent`, `force_proxy`).
* **`mode`**: The matching mode:
  * `replace`: Directly sets the field to the `replacement` value (ignores `pattern`).
  * `regex`: Performs a regular expression search and replace.
  * `wildcard`: Performs a glob-style wildcard match (supports `*` and `?`).
  * `text`: Performs a fixed-string search and replace.
* **`pattern`**: The search pattern (required for `regex`, `wildcard`, and `text` modes).
* **`replacement`**: The value to set or replace with.
* **`enabled`**: Boolean flag to enable or disable the rule.

### Examples

#### 1. Replace Mode (Direct Set)

Directly sets the User-Agent for a specific stream:

```yaml
field: "user_agent"
replacement: "HbbTV/1.6.1"
mode: "replace"
enabled: true
```

#### 2. Regex Mode

Removes bracketed text from channel names (e.g., `Channel One [HD]` ➔ `Channel One`):

```yaml
field: "name"
pattern: "\\s*\\[.*\\]"
replacement: ""
mode: "regex"
enabled: true
```

#### 3. Wildcard Mode

Categorizes any channel starting with "Sky Cinema" into the "Movies" group:

```yaml
field: "group"
pattern: "Sky Cinema*"
replacement: "Movies"
mode: "wildcard"
enabled: true
```

---

## 6. EPG Mapping Overrides

By default, `pluvira` attempts to match M3U channels to EPG channels using their `tvg-id` or normalized names. If automatic matching fails, you can configure manual overrides directly via the WebUI or REST API endpoints (`PUT /api/v1/channels/epg-mapping` and `PUT /api/v1/channels/{channel_id}/epg-mapping`).

Overrides are persisted in the relational SQLite database `pluvira_main.db` (`epg_mapping_overrides` table):

* **Global Overrides**: Applied across all sources when `is_global: true` (`source_name` is empty).
* **Source Overrides**: Applied only to channels belonging to a specific IPTV source provider (takes precedence over global overrides).

---

## 7. Scheduler Configuration (`schedule.yaml`)

The background scheduler is configured via `config/schedule.yaml`. It manages automatic background update tasks using APScheduler running in UTC. Tasks follow a modular domain-driven architecture (`backend/scheduler/jobs/`).

### Configuration Structure Example

```yaml
version: 1
enabled: true
jobs:
  - id: "pluvira_update_daily"
    enabled: true
    trigger: "cron"
    hour: 4
    minute: 0
    day_of_week: "*"
    mode: "tv_sync_full"
    description: "Run full TV and EPG sync daily at 4:00 AM UTC"
    is_system: false

  - id: "epg_update_frequent"
    enabled: true
    trigger: "cron"
    hour: "*/6"
    minute: 30
    mode: "epg_sync_guides"
    description: "Refresh XMLTV guide programmes every 6 hours"
    is_system: false

  - id: "scheduled_link_scan"
    enabled: true
    trigger: "cron"
    hour: 3
    minute: 0
    mode: "stream_health_scan"
    description: "Run automated polite link scanner for broken streams"
    is_system: false
    link_test_filters:
      inclusion: "included_only"
      status_filter: "ko_only"
      sources: []
      groups: []
      name_regex: "(?i)Channel \\d+"
      max_channels: 50

  - id: "license_auto_renewal"
    enabled: true
    trigger: "interval"
    hours: 0
    minutes: 2
    mode: "license_auto_renewal"
    description: "Periodic license synchronization and auto-renewal heartbeat"
    is_system: true
```

### Configuration Fields

* **`enabled`**: Global boolean flag to enable or disable the entire background scheduler.
* **`jobs`**: A list of scheduled background tasks:
  * **`id`**: Unique string identifier for the job (required).
  * **`enabled`**: Boolean flag to enable or disable an individual job (default: `true`).
  * **`mode`**: The domain task execution mode identifier:
    * `tv_sync_full`: Complete synchronization of M3U playlist channels, XMLTV guide programmes, and cache generation.
    * `tv_sync_channels`: Downloads and parses M3U playlist channels with allow/deny filters and metadata rewrites.
    * `epg_sync_guides`: Downloads and parses XMLTV guide schedules into database with channel mapping resolution.
    * `stream_health_scan`: Executes background polite link testing to verify stream reachability and compute health scores.
    * `cloud_backup`: Automated E2EE cloud backup snapshot synchronization for Pro and Ultra subscribers.
    * `license_auto_renewal`: System job managing online verification and silent auto-renewal of cryptographic license tokens.
    *(Legacy modes `full`, `m3u`, `epg`, `link_test`, `backup_cloud`, `license_revocation_heartbeat` are automatically mapped to canonical domain modes).*
  * **`is_system`**: Boolean flag indicating whether the job is a protected system task (e.g. `license_auto_renewal`). Protected jobs cannot be deleted and are automatically preserved across configuration updates. Disabling a system task triggers a safety confirmation prompt. Heartbeat intervals enforce safe execution bounds ($\ge 1\text{m}$ and $\le 24\text{h}$).
  * **`is_recommended`**: Boolean flag indicating whether the job is a recommended factory preset task (e.g. `tv_sync_full`, `epg_sync_guides`, `cloud_backup`).
  * **Restoring Default Tasks**: Users can invoke `POST /api/v1/scheduler/restore-defaults` (or click *"Restore Defaults"* in the WebUI) to re-instantiate missing factory tasks (`mode: "missing_only"`) or reset default tasks to standard values (`mode: "full_reset"`) while preserving custom user tasks.
  * **`trigger`**: Trigger type (`cron` or `interval`).
  * **Cron Trigger Fields (`trigger: "cron"`)**:
    * `hour`: Hour of execution in UTC (0-23 or cron expression like `"*/4"`).
    * `minute`: Minute of execution (0-59).
    * `day_of_week`: Day of week filter string (`*` for daily, `1-5` for weekdays, `6,0` for weekends, or specific days).
  * **Interval Trigger Fields (`trigger: "interval"`)**:
    * `hours`: Number of hours between executions.
    * `minutes`: Number of minutes between executions.
  * **`link_test_filters`**: Optional filter dictionary applied when mode is `stream_health_scan` (`inclusion`, `status_filter`, `sources`, `groups`, `name_regex`, `max_channels`).
  * **`description`**: Human-readable description of the job.


---

## 8. Authentication Settings (`auth`)

Configures optional JWT Bearer authentication requirements for API access. Can be enabled or disabled via `config.yaml` or the **Authentication** card in the Settings hub (`GeneralTab` -> `System`). The token expiration duration (`token_expire_minutes: 1440` / 24h) is managed directly via `config.yaml` or environment defaults and is kept hidden from the WebUI to minimize cognitive noise.

```yaml
auth:
  enabled: false
  secret_key: "pluvira_jwt_secret_key_change_me_in_prod"
  algorithm: "HS256"
  token_expire_minutes: 1440
  username: "admin"
  password: "admin"
```

* **`enabled`**: Toggle to enforce JWT Bearer authentication on protected endpoints.
* **`secret_key`**: Secret string used to sign JWT HS256 tokens.
* **`token_expire_minutes`**: Expiration duration for access tokens in minutes (default 1440m / 24h).

---

## 9. Unified Backup & Restore System (`/api/v1/backup/*`)

`pluvira` provides a unified configuration and schedule backup engine:

* **Export (`GET /api/v1/backup/export`)**: Produces a single unified JSON bundle (`pluvira_backup_*.json`) containing `GlobalConfig` and `SchedulePayload`. Supports `?sanitized=true` to mask passwords and sensitive webhook tokens for public sharing.
* **Pre-Flight Validation (`POST /api/v1/backup/validate`)**: Analyzes uploaded bundles, detects version migrations or sanitized credentials, and computes category-by-category diff counts (`added`, `updated`, `removed`).
* **Atomic Import (`POST /api/v1/backup/import`)**: Writes configuration and schedules to disk with `.bak` snapshot generation and auto-rollback. Supports `destructive` (total overwrite) and `merge` (incremental union) import modes.
* **Zero-Knowledge E2EE Cloud Vault (`/api/v1/cloud/backup/*`)**: Integrates local backend-orchestrated Dual-Engine encrypted backup persistence: primary hardware-accelerated AES-256-GCM via `cryptography` with pure-Python authenticated PBKDF2 (600,000 iterations) + SHA256-CTR + HMAC-SHA256 Encrypt-then-MAC fallback for low-power NAS portability. Encryption executes locally on the user's host/NAS daemon, ensuring full compatibility across all network topologies (including HTTP over LAN/Tailscale) while transmitting strictly opaque ciphertext to Pluvira Cloud. Passphrases never leave the local environment. Includes snapshot pinning to lock historical setups against scheduled FIFO auto-rotation (up to $N - 1$ pinned snapshots in Pro and Ultra tiers) and 1-click atomic disaster recovery (`GET /api/v1/cloud/backup/download/latest` and `POST /api/v1/cloud/backup/download-latest-and-decrypt`).
