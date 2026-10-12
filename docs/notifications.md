# Notification System Guide

`pluvira` features an event-driven notification system. In the Core Edition, basic local log and in-app toast notifications are supported. In the Pro Edition, full event-driven webhooks and multi-target notification matrices are unlocked (Telegram, Discord, Slack, Email, and Pushbullet).

---

## 1. Core Architecture

The notification system is decoupled from the business logic. The `Notifier` service (`backend/core/notifier.py`) acts as a central dispatcher that reads notification configuration directly from `NotificationRepository` in `pluvira_main.db` (`notification_settings` and `notification_targets` tables), filters events based on user configuration and severity levels before parsing target URLs into provider DTOs (`telegram`, `discord`, `slack`, `generic`), and dispatches them via console or Pro IPC (`send-notification`).

### Global Toggle & Test Endpoint

You can enable or disable the entire notification system with a single master switch in the **Notifications** tab. In the open-source Core Edition, the master switch is disabled by default with basic status events logged to the console. In the Pro Edition, enabling the master switch unlocks all notification endpoint cards, presets, and the event matrix. When the master switch is disabled or inactive, all nested configuration cards are automatically deactivated using fieldset-level constraints. Event matrix accordion sections persist their open/closed state in `localStorage` and default to open.

---

## 2. Event Categories

Events are grouped into five logical categories to provide granular control over what triggers a notification.

### A. Acquisition & Runner

Monitors the raw data fetching process.

* **Update Success/Failure**: Global status of the update process.
* **Source Download Failure**: Triggered if a specific M3U or XMLTV URL is unreachable.
* **Source Empty/Malformed**: Triggered if a source is downloaded but contains zero valid items.
* **Partial Acquisition**: Sent if some sources succeeded while others failed.
* **Massive Channel Drop**: Triggered if a source loses more than `X%` of its channels compared to the previous run.
* **M3U / XMLTV Parsing Error**: Triggered on malformed lines, ignored tags, or XML structural errors.

### B. Link Scanner & Stream Health

Monitors the background "Polite Scanner" results.

* **Link Test Report**: A summary sent after a scheduled or batch link test completes.
* **Link KO Detected**: Instant alert when a previously online channel goes offline.
* **Link Recovered**: Instant alert when an offline channel comes back online.
* **Source Health Warning**: Triggered if the overall percentage of working links in a source falls below a threshold.
* **Suspicious Redirect**: Alert for streams redirecting multiple times or to different domains.
* **Link Failover Triggered**: Sent when an offline primary stream is automatically replaced by a working backup stream.

### C. Data Processor & EPG Quality

Monitors the quality of the generated output.

* **Unmapped Included Channels**: Alert if too many "Included" channels lack an EPG guide.
* **EPG Expiration Warning**: Triggered if the future EPG schedule coverage falls below a minimum number of hours.
* **Rewrite Conflict Warning**: Alert if metadata rules produce empty names, empty URLs, or duplicate stream endpoints.
* **Unused EPG Sources**: Alert if an enabled EPG source is not mapped to any included channel.
* **Duplicate Channel Warning**: Alert if channels with the same name are detected across different sources.
* **Slow Processing Warning**: Triggered if DataProcessor takes longer than the configured threshold (default 2s).

### D. Hardware, Storage & SMR

Protects the server and storage integrity.

* **RAM Disk Space Warning**: Critical alert if the `tmpfs` (/dev/shm) is nearly full.
* **Atomic Write Failure**: Alert if the system fails to persist data from RAM to physical storage.
* **Orphan Lock Cleared**: Notification when a stale system lock is automatically recovered.
* **System High Load**: Warning if CPU load average or system temperature exceeds safety thresholds.

### E. Security & Lifecycle

* **Config Save Failure**: Alert if `config.yaml` cannot be saved due to validation or permission errors.
* **Service Startup/Shutdown**: Notifications when the Pluvira daemon starts or stops.
* **Scheduled Job Skipped**: Alert if a cron or interval job is skipped due to a system execution lock.
* **API Internal Error 500**: Critical notification dispatched when an unhandled server exception occurs.

---

## 3. Quick Select Profiles (Presets)

To simplify configuration, the WebUI provides additive presets:

* **ALL**: Enables all 19 event triggers.
* **NONE**: Disables all event triggers.
* **SIMPLE**: Enables only critical failures (Acquisition, Hardware, Config).
* **BALANCED**: Recommended for daily use. Focuses on successes, failures, and link health.
* **ADVANCED**: Deep diagnostic mode for network and stream quality monitoring.
* **HARDWARE**: Focuses on system resources and storage protection.
* **CONTENT**: Focuses on EPG mapping and channel list integrity.

---

## 4. Monitoring Thresholds

Several events rely on configurable thresholds to avoid noise:

* **Massive Drop (%)**: Default 30%. Alert if a source loses this percentage of channels.
* **Health Threshold (%)**: Default 70%. Alert if source link health falls below this.
* **Min Future Hours**: Default 24h. Alert if EPG coverage is running out.
* **Min RAM Disk Free (MB)**: Default 30MB. Critical alert for low temporary storage.
