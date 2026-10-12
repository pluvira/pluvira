# Merge & Failover Tool Guide

The **Merge & Failover Tool** in `pluvira` enables channel deduplication, multi-stream consolidation, and automatic failover management across different IPTV sources.

---

## 1. Overview & Key Concepts

When multiple M3U playlists are configured (e.g., IPTV Source Alpha, IPTV Source Beta, private providers), identical or similar channels (e.g., `Channel One HD`, `CHANNEL 1`, `Channel One (1080p)`) frequently appear multiple times with different stream endpoints, logos, or User-Agents.

The Merge Tool consolidates these duplicate candidate streams into a single **Master Channel** with an ordered fallback chain of **Backup Streams**:

```text
+-----------------------------------------------------------------------+
|                         MASTER CHANNEL (Result)                       |
|  Name: Channel One HD | Logo: Custom/Source | EPG: channel1.net | Group: General  |
+-----------------------------------------------------------------------+
|  PRIMARY ACTIVE STREAM  : http://source1.com/channel1.m3u8 (Source A)  |
|  FAILOVER BACKUP #1     : http://source2.com/channel1.ts   (Source B)  |
|  FAILOVER BACKUP #2     : http://source3.com/live.m3u8 (Source C)      |
+-----------------------------------------------------------------------+
```

---

## 2. Fuzzy Matching & Deduplication Engine

The deduplication engine scans post-rewrite processed channels and detects duplicate clusters across configured sources. The Core Edition applies tag normalization (stripping resolution tags `HD`, `FHD`, `4K`, `1080p`) followed by `difflib.SequenceMatcher` fuzzy matching ($\ge 85\%$). The Pro Edition delegates clustering to a high-speed multithreaded Rust engine supporting extended sensitivity ranges ($50\%-100\%$).

1. **Name Normalization**: Strips resolution tags (`720p`, `1080p`, `1080p60`), quality labels (`HD`, `FHD`, `4K`, `SD`), and bracketed tags (`[TAG]`, `(A)`).
2. **Fast Token & Prefix Pre-Filtering**: Evaluates `_quick_prefix_match` to bypass $O(N^2)$ `SequenceMatcher` calculations for strings lacking initial character or token overlap.
3. **Fuzzy Similarity**: Calculates exact string similarity using `difflib.SequenceMatcher` for pre-filtered candidates.
4. **Sensitivity Threshold**: Configurable threshold (default **90%**) adjustable via the WebUI slider (50% to 100%) with real-time updates.
5. **Composite Deduplication & Disambiguation**: Candidate streams are uniquely identified by a composite `candidate_id` (`md5(url + source)`), and `DataProcessor` resolves merge primary and backup chains using `(original_url, source)` pairs, allowing identical stream URLs from different providers to be rendered, selected, and merged without collisions.

---

## 3. Dynamic User-Agent Inheritance

`pluvira` strictly adheres to the **DRY (Don't Repeat Yourself)** principle for HTTP headers and User-Agents:

* **Automatic Inheritance**: Each stream (Primary or Backup) automatically inherits the specific User-Agent computed by the cascading rewrite engine for its source provider.
* **No Cross-Cutting Maintenance**: Updating a source-level User-Agent or rewrite rule instantly updates all merged channels utilizing streams from that source.
* **Explicit Override**: An optional explicit User-Agent can be defined at the Master or Stream level if a specific channel requires custom headers.

---

## 4. Automatic Failover Engine (Pro Edition)

In the Pro Edition, during background link testing or real-time playback failure reports, the system executes native hardware-accelerated failover promotion with Zero-Copy SQLite WAL transaction commits:

1. If the active `primary_stream` returns an HTTP error (404, 500, or Timeout), the Polite Scanner (`backend/core/scanner.py`) inspects `config.channel_merges`.
2. It tests configured `backup_streams` sequentially in priority order (`#1`, `#2`, ...).
3. When a working backup stream (HTTP 200 OK) is found:
   * The working backup stream is **promoted** to `primary_stream`.
   * The failed primary stream is moved to the end of `backup_streams`.
   * `ChannelMergeRepository` updates `pluvira_main.db` atomically with zero YAML disk writes.

---

## 5. Bulk Merge Operations & Auto-Merge Engine

* **Atomic Bulk Merge Apply (`POST /api/v1/merge/bulk/apply`)**: Merges N duplicate clusters in a single atomic transaction with direct relational SQLite persistence.
* **Bulk Delete (`POST /api/v1/merge/bulk/delete`)**: Unmerges multiple master channels in a single operation.
* **High-Confidence Auto-Merge (`POST /api/v1/merge/auto-apply`)**: Automatically merges high-confidence clusters exceeding the target similarity threshold (default 95%) resolved via the native Pro engine.
* **On-Demand Cluster Computation**: Duplicate candidate clusters are calculated purely on-demand from post-rewrite processed channels, eliminating file mtime tracking and volatile cache invalidation bottlenecks.
* **Merge Statistics (`GET /api/v1/merge/stats`)**: Delivers real-time cluster metrics (`total_clusters_detected`, `total_merged_channels`, `total_unmerged_clusters`, `total_backup_streams`).
* **Merged Channel Edits & Save CTA**: When modifications are made to a merged master channel (such as display name edits or fallback stream reordering), a round icon-only `Save` button appears in the matrix toolbar to apply and persist updates.

## 6. Localized Channel Failover Sheet (`ChannelMergeSheet`)

In addition to the global Merge Tool, backup stream chains can be configured directly from the Channels view using `ChannelMergeSheet.svelte` (`channels/modals/ChannelMergeSheet.svelte`):

* **Primary Stream Inspection**: Displays active stream URL, source, and User-Agent.
* **Ordered Backup Chain**: Interactive list supporting priority movement (`Up` / `Down`) and stream removal.
* **Candidate Suggestions**: Automatically searches duplicate clusters for alternative stream candidates with one-click `Set Primary` and `+ Backup` actions.

## 7. WebUI Workflow (`/tools/merge`)

The dedicated Merge Tool is accessible via the sidebar menu and directly within the Channels & Playlist Hub (*#/channels?tab=merge*):

* **Top Control Bar**: Filter by status (*All Clusters*, *Unmerged Only*, *Merged Only*), debounced search input, and adaptive Fuzzy Sensitivity slider ($\ge 85\%$ in Core, $50\%-100\%$ in Pro with informative notice).
* **Top Bulk Operations & Stats Bar**: Displays aggregate metrics (`total_clusters_detected`, `total_merged_channels`, `total_unmerged_clusters`, `total_backup_streams`), an **"AUTO-MERGE ALL (≥ 95%)"** button (enabled in Pro, disabled with explanatory notice in Core), and an **"UNMERGE ALL"** button for bulk restoration.
* **Sidebar Cluster List**: Lists candidate clusters with explicit status badges (`SAVED` for active configurations, `SUGGESTED` for calculated recommendations).
* **Header & Action Buttons**: Native status badges (`MERGED / SAVED` vs `CALCULATED / SUGGESTED`) and dynamic action buttons (`MERGE` when unmerged, `UNMERGE` when merged) driven directly by backend cluster enrichment (`is_merged`, `status`, `merged_details`).
* **Master Panel (2 Columns)**:
  * *Left Column*: Master display name, logo preview, group, source, and primary stream details.
  * *Right Column*: Ordered *Failover Backup Priority* list with direct `SET PRIMARY`, `[ ↑ ] [ ↓ ]` reorder arrows, and `DELETE` actions.
* **Candidate Cards (CSS Grid)**: Multi-column responsive grid displaying candidate cards with Channel Details (Info icon), Play, Test Link, and `ADD AS BACKUP` buttons.

---

## 7. Configuration Example (`config.yaml`)

```yaml
channel_merges:
  "Channel One HD":
    name: "Channel One HD"
    logo: "https://example.com/logos/channel1.png"
    group: "General"
    epg_id: "EPG_Source_Alpha::channel1.net"
    primary_stream:
      url: "http://source1.com/channel1.m3u8"
      source: "IPTV_Source_Alpha"
    backup_streams:
      - url: "http://source2.com/live/channel1.m3u8"
        source: "IPTV_Source_Beta"
      - url: "http://source3.com/stream.ts"
        source: "IPTV_Source_Gamma"
```
